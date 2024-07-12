from django.urls import path

from .views import DatasetCatalog, DatasetExportAPI, DatasetToGearbox

urlpatterns = [
    path(route="projects/<int:project_id>/download-format", view=DatasetCatalog.as_view(), name="download-format"),
    path(route="projects/<int:project_id>/download", view=DatasetExportAPI.as_view(), name="download-dataset"),
    path(route="projects/<int:project_id>/send-dataset", view=DatasetToGearbox.as_view(), name="send-dataset"),
]
