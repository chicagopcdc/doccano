from typing import List

import filetype
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_drf_filepond.api import store_upload
from django_drf_filepond.models import TemporaryUpload
from django.db import transaction, DataError, IntegrityError, ProgrammingError
from django.db.utils import OperationalError
from django.contrib.auth import get_user_model
from django.apps import apps

from .datasets import load_dataset
from .pipeline.catalog import Format, create_file_format
from .pipeline.exceptions import (
    FileImportException,
    FileTypeException,
    MaximumFileSizeException,
)
from .pipeline.readers import FileName
from projects.models import Project

from typing import List, Iterable, Optional
from pathlib import Path
import json


def get_label_text_max_length_for_project(project) -> Optional[int]:
    """
    Best-effort: read the CharField('text').max_length from the label model
    used by this project. Returns None if not found.
    """

    # 1) Project-provided label class (common in doccano forks)
    for attr in ("get_label_type_class", "label_type_class", "label_types"):
        cls = getattr(project, attr, None)
        if cls:
            try:
                # handle both callables and classes
                Model = cls() if callable(cls) else cls
                field = Model._meta.get_field("text")
                if getattr(field, "max_length", None):
                    return field.max_length
            except Exception:
                pass

    # 2) Map by project.project_type -> model
    # Adjust names if your app/model names differ.
    mapping = {
        "DocumentClassification": ("labels", "CategoryType"),
        "SequenceLabeling": ("labels", "SpanType"),
        "RelationExtraction": ("labels", "RelationType"),
        "IntentDetectionAndSlotFilling": ("labels", "CategoryType"),
        "Text2Text": ("labels", "CategoryType"),
        # add other project types here if you have them
    }
    ptype = getattr(project, "project_type", None)
    if ptype in mapping:
        app_label, model_name = mapping[ptype]
        try:
            Model = apps.get_model(app_label, model_name)
            field = Model._meta.get_field("text")
            if getattr(field, "max_length", None):
                return field.max_length
        except Exception:
            pass

    # 3) Fallback scan of common label models
    for model_name in ("CategoryType", "SpanType", "RelationType"):
        try:
            Model = apps.get_model("labels", model_name)
            field = Model._meta.get_field("text")
            if getattr(field, "max_length", None):
                return field.max_length
        except Exception:
            continue

    return None


def _err(filename: str, line: int, message: str) -> dict:
    # Matches what the frontend already allows
    return {"filename": filename or "Import", "line": line if line is not None else "-", "message": str(message)}


def _extract_label_strings(obj: dict) -> Iterable[str]:
    # entities: [{"label": "X", ...}]
    ents = obj.get("entities")
    if isinstance(ents, list):
        for e in ents:
            if isinstance(e, dict) and isinstance(e.get("label"), str):
                yield e["label"]
    # labels: [[s,e,"X"]] or [{"label":"X"}]
    labs = obj.get("labels")
    if isinstance(labs, list):
        for item in labs:
            if isinstance(item, list) and len(item) >= 3 and isinstance(item[2], str):
                yield item[2]
            elif isinstance(item, dict) and isinstance(item.get("label"), str):
                yield item["label"]


def _preflight_jsonl(path: Path, label_max_len: Optional[int]) -> List[dict]:
    errors: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
                if not isinstance(obj, dict):
                    errors.append(_err(path.name, i, "Each line must be a JSON object (mapping)."))
                    continue
            except json.JSONDecodeError as e:
                errors.append(_err(path.name, i, f"Invalid JSON: {e.msg}"))
                continue
            for lbl in _extract_label_strings(obj):
                if label_max_len and len(lbl) > label_max_len:
                    errors.append(_err(path.name, i, f"Label too long ({len(lbl)}>{label_max_len})"))
    return errors


def _preflight_files(fmt, filenames, project, options, label_max_len: Optional[int]):
    """Call a format-specific preflight if available; otherwise fallback for JSONL."""
    # Prefer a native preflight implemented by the format adapter
    if hasattr(fmt, "preflight") and callable(getattr(fmt, "preflight")):
        try:
            result = fmt.preflight(filenames=filenames, project=project, options=options or {})
            errs = result.get("errors") if isinstance(result, dict) else result
            return errs or []
        except Exception as e:
            # If the format's preflight itself fails, surface a single clear error
            return [_err("Preflight", "-", f"Preflight failed: {e}")]

    # Heuristic JSONL fallback (by extension/name)
    name = (getattr(fmt, "name", "") or "").lower()
    ext = (getattr(fmt, "ext", "") or "").lower()
    is_jsonl = "jsonl" in name or ext == ".jsonl"

    errors: List[dict] = []
    if is_jsonl:
        for fn in filenames:
            errors.extend(_preflight_jsonl(Path(fn.full_path), label_max_len))
    return errors


def check_file_type(filename, file_format: Format, filepath: str):
    if not settings.ENABLE_FILE_TYPE_CHECK:
        return
    kind = filetype.guess(filepath)
    if not file_format.validate_mime(kind.mime):
        raise FileTypeException(filename, kind.mime, file_format.accept_types)


def check_uploaded_files(upload_ids: List[str], file_format: Format):
    errors: List[FileImportException] = []
    cleaned_ids = []
    temporary_uploads = TemporaryUpload.objects.filter(upload_id__in=upload_ids)
    for tu in temporary_uploads:
        if tu.file.size > settings.MAX_UPLOAD_SIZE:
            errors.append(MaximumFileSizeException(tu.upload_name, settings.MAX_UPLOAD_SIZE))
            tu.delete()
            continue
        try:
            check_file_type(tu.upload_name, file_format, tu.get_file_path())
        except FileTypeException as e:
            errors.append(e)
            tu.delete()
            continue
        cleaned_ids.append(tu.upload_id)
    return cleaned_ids, errors


@shared_task(
    # Retry only on transient infra issues; not on data/constraint errors
    autoretry_for=(OperationalError, ConnectionError, TimeoutError, SoftTimeLimitExceeded),
    retry_backoff=2,
    retry_jitter=True,
    retry_backoff_max=30,
    max_retries=3,
)
def import_dataset(user_id, project_id, file_format: str, upload_ids: List[str], task: str, **kwargs):
    project = get_object_or_404(Project, pk=project_id)
    user = get_object_or_404(get_user_model(), pk=user_id)
    label_max_len = get_label_text_max_length_for_project(project)
    try:
        fmt = create_file_format(file_format)
        upload_ids, errors = check_uploaded_files(upload_ids, fmt)

        temporary_uploads = TemporaryUpload.objects.filter(upload_id__in=upload_ids)
        filenames = [
            FileName(full_path=tu.get_file_path(), generated_name=tu.file.name, upload_name=tu.upload_name)
            for tu in temporary_uploads
        ]

        # 1) PRE-VALIDATE (no DB writes)
        preflight_errors = _preflight_files(fmt, filenames, project, kwargs, label_max_len)
        if preflight_errors:
            return {"error": preflight_errors}

        dataset = load_dataset(task, fmt, filenames, project, **kwargs)

        # 2) ATOMIC WRITE (all or nothing)
        with transaction.atomic():
            dataset.save(user, batch_size=settings.IMPORT_BATCH_SIZE)

        # 3) Move uploads only after a successful save
        upload_to_store(temporary_uploads)

        # unify error shape
        errors.extend(getattr(dataset, "errors", []))
        return {"error": [e.dict() if hasattr(e, "dict") else e for e in errors]}

    except FileImportException as e:
        return {"error": [e.dict()]}

    except (DataError, IntegrityError, ProgrammingError) as e:
        # hard data/constraint error -> one clear error, no retry
        return {"error": [_err("Server", "-", str(e))]}

    except Exception as e:
        # treat everything else as a one-shot failure for this task
        return {"error": [_err("Server", "-", str(e))]}


def upload_to_store(temporary_uploads):
    for tu in temporary_uploads:
        store_upload(tu.upload_id, destination_file_path=tu.file.name)
