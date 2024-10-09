import datetime
import os

import requests
from celery.result import AsyncResult
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Project
from projects.permissions import IsProjectAdmin

from .celery_tasks import export_dataset, export_example
from .pipeline.catalog import Options


class DatasetCatalog(APIView):
    permission_classes = [IsAuthenticated & IsProjectAdmin]

    def get(self, request, *args, **kwargs):
        project_id = kwargs["project_id"]
        project = get_object_or_404(Project, pk=project_id)
        use_relation = getattr(project, "use_relation", False)
        options = Options.filter_by_task(project.project_type, use_relation)
        return Response(data=options, status=status.HTTP_200_OK)


class DatasetExportAPI(APIView):
    permission_classes = [IsAuthenticated & IsProjectAdmin]

    def get(self, request, *args, **kwargs):
        task_id = request.GET["taskId"]
        task = AsyncResult(task_id)
        ready = task.ready()
        if ready:
            filename = task.result
            return FileResponse(open(filename, mode="rb"), as_attachment=True)
        return Response({"status": "Not ready"})

    def post(self, request, *args, **kwargs):
        project_id = self.kwargs["project_id"]
        file_format = request.data.pop("format")
        export_approved = request.data.pop("exportApproved", False)
        task = export_dataset.delay(
            project_id=project_id,
            file_format=file_format,
            confirmed_only=export_approved,
            **request.data,
        )
        return Response({"task_id": task.task_id})


class DatasetToGearbox(APIView):
    permission_classes = [IsAuthenticated & IsProjectAdmin]

    def post(self, request, *args, **kwargs):
        """
        Handles the POST request to create a task and export the specified document to GEARBOX_URL.

        Args:
            request (Request): The HTTP request object.
            args (tuple): Positional arguments.
            kwargs (dict): Keyword arguments.

        Returns:
            Response: The HTTP response object.

        Raises:
            Exception: If an error occurs during the export process.

        """
        # Create task
        project_id = self.kwargs["project_id"]
        document_id = request.data.pop("docId")
        file_format = request.data.pop("format")
        export_approved = request.data.pop("exportApproved", False)
        task = export_example.delay(
            project_id=project_id,
            document_id=document_id,
            file_format=file_format,
            confirmed_only=export_approved,
            **request.data,
        )

        try:
            export_filename = AsyncResult(task.task_id).get(timeout=None, propagate=True)
        except Exception as e:
            return Response({"status_code": False, "exception": e.args[0]})
        # Get GEARBOX_URL from the environment
        GEARBOX_URL = os.getenv("GEARBOX_URL")
        status_code = None
        response = None

        filename = (
        	f"doccano_export_{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
        )
       	files = {"file": (filename, open(export_filename, "rb"), "application/zip")} 
        response = requests.post(GEARBOX_URL, files=files, timeout=15)

        status_code = response.ok
        return Response({"status_code": status_code})
