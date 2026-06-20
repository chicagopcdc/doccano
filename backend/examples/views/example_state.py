import json
import logging
import os
import tempfile

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from api.gearbox_client import submit_to_gearbox
from data_export.models import ExportedExample
from data_export.pipeline.dataset import Dataset
from data_export.pipeline.factories import (
    create_comment,
    create_formatter,
    create_labels,
    create_writer,
)
from data_export.pipeline.services import ExportApplicationService
from examples.models import Example, ExampleState
from examples.serializers import ExampleStateSerializer
from projects.models import Project
from projects.permissions import IsProjectMember

logger = logging.getLogger(__name__)


def _transform_to_gearbox_format(jsonl_bytes: bytes) -> bytes:
    """Convert doccano JSONL export format to gearbox RawCriteriaIn format.

    Doccano exports label as [[start, end, name, meta], ...].
    Gearbox expects entities as [{"start_offset":..., "end_offset":..., "label":..., "meta":...}]
    and pre_annotated as [{"span":[start,end,name], "matched_models":[...], "is_standard_gb_var":...}].
    """
    lines = jsonl_bytes.decode("utf-8").strip().split("\n")
    out = []
    for line in lines:
        if not line.strip():
            continue
        obj = json.loads(line)
        raw_labels = obj.pop("label", [])
        entities = []
        pre_annotated = []
        for entry in raw_labels:
            start_offset, end_offset, label_name = entry[0], entry[1], entry[2]
            meta = entry[3] if len(entry) > 3 else {}
            entities.append(
                {
                    "start_offset": start_offset,
                    "end_offset": end_offset,
                    "label": label_name,
                    "meta": meta,
                }
            )
            pre_annotated.append(
                {
                    "span": [start_offset, end_offset, label_name],
                    "matched_models": meta.get("matched_models"),
                    "is_standard_gb_var": meta.get("is_standard_gb_var"),
                }
            )
        obj["entities"] = entities
        obj["pre_annotated"] = pre_annotated
        out.append(json.dumps(obj))
    return "\n".join(out).encode("utf-8")


class ExampleStateList(generics.ListCreateAPIView):
    serializer_class = ExampleStateSerializer
    permission_classes = [IsAuthenticated & IsProjectMember]

    @property
    def can_confirm_per_user(self):
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])
        return not project.collaborative_annotation

    def get_queryset(self):
        queryset = ExampleState.objects.filter(example=self.kwargs["example_id"])
        if self.can_confirm_per_user:
            queryset = queryset.filter(confirmed_by=self.request.user)
        return queryset

    def perform_create(self, serializer):
        queryset = self.get_queryset()
        if queryset.exists():
            queryset.delete()
        else:
            example = get_object_or_404(Example, pk=self.kwargs["example_id"])
            serializer.save(example=example, confirmed_by=self.request.user)
            self._submit_to_gearbox(example)

    def _submit_to_gearbox(self, example):
        try:
            project = get_object_or_404(Project, pk=self.kwargs["project_id"])
            examples = ExportedExample.objects.filter(pk=example.pk)
            labels = create_labels(project, examples)
            comments = create_comment(examples)
            dataset = Dataset(examples, labels, comments, project.is_text_project)
            formatters = create_formatter(project, "JSONL")
            writer = create_writer("JSONL")

            service = ExportApplicationService(dataset, formatters, writer)
            with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
                tmp_path = tmp.name
            service.export(tmp_path)
            with open(tmp_path, "rb") as f:
                jsonl_bytes = f.read()
            os.unlink(tmp_path)

            jsonl_bytes = _transform_to_gearbox_format(jsonl_bytes)
            submit_to_gearbox(jsonl_bytes, filename=f"example_{example.pk}.jsonl")
            logger.info("Successfully submitted example %s to gearbox", example.pk)
        except Exception:
            logger.exception("Failed to submit example %s to gearbox", example.pk)
