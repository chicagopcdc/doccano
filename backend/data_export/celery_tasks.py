import os
import shutil
import uuid

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import DataError, IntegrityError, ProgrammingError
from django.db.utils import OperationalError
from django.shortcuts import get_object_or_404

from .pipeline.dataset import Dataset
from .pipeline.factories import (
    create_comment,
    create_formatter,
    create_labels,
    create_writer,
)
from .pipeline.services import ExportApplicationService
from data_export.models import ExportedExample
from projects.models import Member, Project

logger = get_task_logger(__name__)


def create_collaborative_dataset(
    project: Project, dirpath: str, confirmed_only: bool, formatters, writer, example_ids=None
):
    is_text_project = project.is_text_project
    if confirmed_only:
        examples = ExportedExample.objects.confirmed(project)
    else:
        examples = ExportedExample.objects.filter(project=project)
    if example_ids:
        examples = examples.filter(id__in=example_ids)
    labels = create_labels(project, examples)
    comments = create_comment(examples)
    dataset = Dataset(examples, labels, comments, is_text_project)

    service = ExportApplicationService(dataset, formatters, writer)

    filepath = os.path.join(dirpath, f"all.{writer.extension}")
    service.export(filepath)


def create_individual_dataset(
    project: Project, dirpath: str, confirmed_only: bool, formatters, writer, example_ids=None
):
    is_text_project = project.is_text_project
    members = Member.objects.filter(project=project)
    for member in members:
        if confirmed_only:
            examples = ExportedExample.objects.confirmed(project, user=member.user)
        else:
            examples = ExportedExample.objects.filter(project=project)
        if example_ids:
            examples = examples.filter(id__in=example_ids)
        labels = create_labels(project, examples, member.user)
        comments = create_comment(examples, member.user)
        dataset = Dataset(examples, labels, comments, is_text_project)

        service = ExportApplicationService(dataset, formatters, writer)

        filepath = os.path.join(dirpath, f"{member.username}.{writer.extension}")
        service.export(filepath)


@shared_task(
    # Retries only for likely-transient infra issues, same policy as
    # data_import.celery_tasks.import_dataset. Permanent errors (bad
    # file_format, missing project, DB constraint issues) should fail
    # fast instead of burning 3 retries.
    autoretry_for=(OperationalError, ConnectionError, TimeoutError, SoftTimeLimitExceeded),
    retry_backoff=2,
    retry_jitter=True,
    retry_backoff_max=30,
    max_retries=3,
)
def export_dataset(project_id, file_format: str, confirmed_only=False, example_ids=None):
    try:
        project = get_object_or_404(Project, pk=project_id)
        dirpath = os.path.join(settings.MEDIA_ROOT, str(uuid.uuid4()))
        os.makedirs(dirpath, exist_ok=True)
        formatters = create_formatter(project, file_format)
        writer = create_writer(file_format)
        if project.collaborative_annotation:
            create_collaborative_dataset(project, dirpath, confirmed_only, formatters, writer, example_ids)
        else:
            create_individual_dataset(project, dirpath, confirmed_only, formatters, writer, example_ids)
        zip_file = shutil.make_archive(dirpath, "zip", dirpath)
        shutil.rmtree(dirpath)
        return zip_file

    except (OperationalError, ConnectionError, TimeoutError, SoftTimeLimitExceeded):
        # Must be re-raised (not caught-and-returned) so autoretry_for above
        # actually sees it and can schedule a retry.
        raise

    except (DataError, IntegrityError, ProgrammingError):
        logger.warning("export_dataset: DB error for project %s", project_id, exc_info=True)
        raise

    except Exception:
        # Catch-all safeguard: log so real bugs stay visible, then
        # re-raise. We don't want to retry these (they won't succeed
        # on retry), but export_dataset has no established "error" dict
        # return shape like import_dataset does, so we let it fail as
        # a normal task failure rather than inventing a new contract.
        logger.exception("export_dataset: unexpected error for project %s", project_id)
        raise
