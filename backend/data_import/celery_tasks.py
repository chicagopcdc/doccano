# -*- coding: utf-8 -*-

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
    Tries to discover the max length constraint for label text ("text" CharField)
    for the given project's label model.

    Why?
    - Different project types can use different label models.
    - We want to reject too-long labels early (preflight), before DB insert fails.

    Returns:
        int | None: max_length if found, else None (means "no known limit").
    """

    # label model through attribute
    for attr in ("get_label_type_class", "label_type_class", "label_types"):
        cls = getattr(project, attr, None)
        if cls:
            try:
                # Handle callables (factories) and classes directly.
                Model = cls() if callable(cls) else cls
                field = Model._meta.get_field("text")
                if getattr(field, "max_length", None):
                    return field.max_length
            except Exception:
                # If any step fails, just try the next strategy.
                pass

    # Map a project.project_type string to a known labels app model.
    # Adjust names if the app/model names differ.
    mapping = {
        "DocumentClassification": ("labels", "CategoryType"),
        "SequenceLabeling": ("labels", "SpanType"),
        "RelationExtraction": ("labels", "RelationType"),
        "IntentDetectionAndSlotFilling": ("labels", "CategoryType"),
        "Text2Text": ("labels", "CategoryType"),
        # Add more mappings as needed.
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

    # If needed look through common label models in the "labels" app.
    for model_name in ("CategoryType", "SpanType", "RelationType"):
        try:
            Model = apps.get_model("labels", model_name)
            field = Model._meta.get_field("text")
            if getattr(field, "max_length", None):
                return field.max_length
        except Exception:
            continue

    # No constraint found => return None.
    return None


def _err(filename: str, line: int, message: str) -> dict:
    """
    Build a single error row in the shape the frontend expects.
    """
    return {
        "Source": filename or "Import",
        "line": line if line is not None else "-",
        "message": str(message),
    }


def _extract_label_strings(obj: dict) -> Iterable[str]:
    """
    Extract label strings from a single dataset JSON object.

    Supports common shapes:
      - {"entities": [{"label": "X", ...}, ...]}
      - {"labels": [[start, end, "X"], ...]}
      - {"labels": [{"label": "X"}, ...]}
    """
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


# TODO: Implement preflight(...) for non-JSONL formats.
# Until then, imports try to save and report any errors; transactions prevent partial writes.


def _preflight_jsonl(path: Path, label_max_len: Optional[int]) -> List[dict]:
    """
    Validate json a file line-by-line without writing to the DB.

    Checks:
      - Each non-empty line must parse as JSON.
      - Each line must be a JSON object (mapping).
      - Any label text must respect max length if provided.
    """
    errors: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                # Allow blank lines.
                continue
            try:
                obj = json.loads(s)
                if not isinstance(obj, dict):
                    errors.append(_err(path.name, i, "Each line must be a JSON object (mapping)."))
                    continue
            except json.JSONDecodeError as e:
                errors.append(_err(path.name, i, f"Invalid JSON: {e.msg}"))
                continue

            # Validate label lengths if we know a limit.
            for lbl in _extract_label_strings(obj):
                if label_max_len and len(lbl) > label_max_len:
                    errors.append(_err(path.name, i, f"Label too long ({len(lbl)}>{label_max_len})"))
    return errors


def _preflight_files(fmt, filenames, project, options, label_max_len: Optional[int]):
    """
    Run a format-specific preflight if the format shows one.

    Returns:
        list[dict]: list of error rows (empty = OK to import)
    """
    # Prefer a native preflight implemented by the format adapter.
    if hasattr(fmt, "preflight") and callable(getattr(fmt, "preflight")):
        try:
            result = fmt.preflight(filenames=filenames, project=project, options=options or {})
            errs = result.get("errors") if isinstance(result, dict) else result
            return errs or []
        except Exception as e:
            # If the format's preflight itself fails, surface a single clear error.
            return [_err("Preflight", "-", f"Preflight failed: {e}")]

    # Heuristic JSONL fallback (by name/extension only).
    name = (getattr(fmt, "name", "") or "").lower()
    ext = (getattr(fmt, "ext", "") or "").lower()
    is_jsonl = "jsonl" in name or ext == ".jsonl"

    errors: List[dict] = []
    if is_jsonl:
        for fn in filenames:
            errors.extend(_preflight_jsonl(Path(fn.full_path), label_max_len))
    return errors


def check_file_type(filename, file_format: Format, filepath: str):
    """
    If file type checking is enabled, ensure the detected MIME is acceptable
    to the chosen format. Raises FileTypeException on mismatch.
    """
    if not settings.ENABLE_FILE_TYPE_CHECK:
        return
    kind = filetype.guess(filepath)
    if not file_format.validate_mime(kind.mime):
        raise FileTypeException(filename, kind.mime, file_format.accept_types)


def check_uploaded_files(upload_ids: List[str], file_format: Format):
    """
    Validate uploads before we attempt to parse them:

    - Reject files bigger than MAX_UPLOAD_SIZE (delete the temp upload).
    - Reject files whose MIME type doesn't match the chosen format
      (delete the temp upload).
    - Keep only validated upload IDs for the pipeline.

    Returns:
        (cleaned_ids, errors)
    """
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
    # Retries only for likely-transient infra issues.
    # We intentionally DO NOT retry for data/validation/constraint errors.
    autoretry_for=(OperationalError, ConnectionError, TimeoutError, SoftTimeLimitExceeded),
    retry_backoff=2,
    retry_jitter=True,
    retry_backoff_max=30,
    max_retries=3,
)
def import_dataset(user_id, project_id, file_format: str, upload_ids: List[str], task: str, **kwargs):
    """
    Main import task.

    Flow:
      1) Resolve project/user.
      2) Build file format adapter.
      3) Validate uploads (size/MIME), collect cleaned upload IDs.
      4) PRE-FLIGHT (no DB writes): format-native or our JSONL fallback.
      5) If preflight is clean: parse and SAVE inside a transaction.
      6) After successful save, move temp uploads to permanent store.
      7) Return {"error": [...]} where [] means success.

    Returns:
        dict: {"error": [..]} list of error rows (empty = success)
    """
    project = get_object_or_404(Project, pk=project_id)
    user = get_object_or_404(get_user_model(), pk=user_id)

    # Discover max label length constraint for this project's label model (if any).
    label_max_len = get_label_text_max_length_for_project(project)

    try:
        # Build format adapter (e.g., JSONL, CSV, etc.).
        fmt = create_file_format(file_format)

        # Validate file size/MIME and clean the upload IDs.
        upload_ids, errors = check_uploaded_files(upload_ids, fmt)

        # Convert remaining uploads into pipeline FileName objects.
        temporary_uploads = TemporaryUpload.objects.filter(upload_id__in=upload_ids)
        filenames = [
            FileName(
                full_path=tu.get_file_path(),
                generated_name=tu.file.name,
                upload_name=tu.upload_name,
            )
            for tu in temporary_uploads
        ]

        # Pre-flight
        preflight_errors = _preflight_files(fmt, filenames, project, kwargs, label_max_len)
        if preflight_errors:
            # Stop early; nothing written to DB yet.
            return {"error": preflight_errors}

        # Build dataset object using the pipeline.
        dataset = load_dataset(task, fmt, filenames, project, **kwargs)

        # Writing to db
        with transaction.atomic():
            dataset.save(user, batch_size=settings.IMPORT_BATCH_SIZE)

        # Move upload after succes
        upload_to_store(temporary_uploads)

        # Normalize and return any non-fatal dataset errors (usually empty).
        errors.extend(getattr(dataset, "errors", []))
        return {"error": [e.dict() if hasattr(e, "dict") else e for e in errors]}

    except FileImportException as e:
        # Known import error type from the pipeline: return in the same shape.
        return {"error": [e.dict()]}

    except (DataError, IntegrityError, ProgrammingError) as e:
        # Hard DB/constraint error: return a single, clear error row; no retry.
        return {"error": [_err("Server", "-", str(e))]}

    except Exception as e:
        # Catch-all safeguard: return a readable error row; the task will not retry.
        return {"error": [_err("Server", "-", str(e))]}


def upload_to_store(temporary_uploads):
    """
    Move temporary uploads (django-drf-filepond) to their permanent location.
    Only called after a successful DB write.
    """
    for tu in temporary_uploads:
        store_upload(tu.upload_id, destination_file_path=tu.file.name)
