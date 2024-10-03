import os
import shutil
import uuid

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.shortcuts import get_object_or_404

from data_export.models import ExportedExample
from projects.models import Member, Project

from .pipeline.dataset import Dataset
from .pipeline.factories import (
    create_comment,
    create_formatter,
    create_labels,
    create_writer,
)
from .pipeline.services import ExportApplicationService

logger = get_task_logger(__name__)


def create_collaborative_dataset(
    project: Project, dirpath: str, confirmed_only: bool, formatters, writer
):
    is_text_project = project.is_text_project
    if confirmed_only:
        examples = ExportedExample.objects.confirmed(project)
    else:
        examples = ExportedExample.objects.filter(project=project)
    labels = create_labels(project, examples)
    comments = create_comment(examples)
    dataset = Dataset(examples, labels, comments, is_text_project)

    service = ExportApplicationService(dataset, formatters, writer)

    filepath = os.path.join(dirpath, f"all.{writer.extension}")
    service.export(filepath)


def create_individual_dataset(
    project: Project, dirpath: str, confirmed_only: bool, formatters, writer
):
    is_text_project = project.is_text_project
    members = Member.objects.filter(project=project)
    for member in members:
        if confirmed_only:
            examples = ExportedExample.objects.confirmed(project, user=member.user)
        else:
            examples = ExportedExample.objects.filter(project=project)
        labels = create_labels(project, examples, member.user)
        comments = create_comment(examples, member.user)
        dataset = Dataset(examples, labels, comments, is_text_project)

        service = ExportApplicationService(dataset, formatters, writer)

        filepath = os.path.join(dirpath, f"{member.username}.{writer.extension}")
        service.export(filepath)


def create_single_example_dataset(
    project: Project,
    document_id: int,
    dirpath: str,
    confirmed_only: bool,
    formatters,
    writer,
):
    """
    Create a single example dataset.

    Args:
        project (Project): The project.
        document_id (int): The ID of the document.
        dirpath (str): The directory path.
        confirmed_only (bool): Whether to include only confirmed examples.
        formatters: The formatters.
        writer: The writer.

    Returns:
        None
    """
    member = Member.objects.filter(project=project)
    is_text_project = project.is_text_project
    example = [ExportedExample.objects.get(id=document_id)]
    labels = create_labels(project, example, member.user)
    comments = create_comment(example, member.user)
    dataset = Dataset(example, labels, comments, is_text_project)

    service = ExportApplicationService(dataset, formatters, writer)

    filepath = os.path.join(dirpath, f"{member.username}.{writer.extension}")
    service.export(filepath)


def create_single_example_collaborative_dataset(
    project: Project,
    document_id: int,
    dirpath: str,
    confirmed_only: bool,
    formatters,
    writer,
):
    """
    Creates a single example dataset for a collaborative project.

    Args:
        project (Project): The project.
        document_id (int): The ID of the document.
        dirpath (str): The directory path.
        confirmed_only (bool): Whether to include only confirmed examples.
        formatters: The formatters.
        writer: The writer.

    Returns:
        None
    """
    is_text_project = project.is_text_project
    example = [ExportedExample.objects.get(id=document_id)]
    labels = create_labels(project, example)
    comments = create_comment(example)
    dataset = Dataset(example, labels, comments, is_text_project)

    service = ExportApplicationService(dataset, formatters, writer)

    filepath = os.path.join(dirpath, f"all.{writer.extension}")
    service.export(filepath)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True)
def export_dataset(project_id, file_format: str, confirmed_only=False):
    project = get_object_or_404(Project, pk=project_id)
    dirpath = os.path.join(settings.MEDIA_ROOT, str(uuid.uuid4()))
    os.makedirs(dirpath, exist_ok=True)
    formatters = create_formatter(project, file_format)
    writer = create_writer(file_format)
    if project.collaborative_annotation:
        create_collaborative_dataset(project, dirpath, confirmed_only, formatters, writer)
    else:
        create_individual_dataset(project, dirpath, confirmed_only, formatters, writer)
    zip_file = shutil.make_archive(dirpath, "zip", dirpath)
    shutil.rmtree(dirpath)
    return zip_file


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True)
def export_example(project_id, document_id, file_format: str, confirmed_only=False):
    """
    Export a single example dataset for a project.

    Args:
        project_id (int): The ID of the project.
        document_id (int): The ID of the document.
        file_format (str): The format of the exported file.
        confirmed_only (bool, optional): Whether to include only confirmed examples. Defaults to False.

    Returns:
        str: The path to the exported file.

    Raises:
        Exception: If an error occurs during the export process.
    """
    project = get_object_or_404(Project, pk=project_id)
    dirpath = os.path.join(settings.MEDIA_ROOT, str(uuid.uuid4()))
    os.makedirs(dirpath, exist_ok=True)
    formatters = create_formatter(project, file_format)
    writer = create_writer(file_format)
    if project.collaborative_annotation:
        create_single_example_collaborative_dataset(
            project, document_id, dirpath, confirmed_only, formatters, writer
        )
    else:
        create_single_example_dataset(
            project, document_id, dirpath, confirmed_only, formatters, writer
        )
    zip_file = shutil.make_archive(dirpath, "zip", dirpath)
    shutil.rmtree(dirpath)
    return zip_file
