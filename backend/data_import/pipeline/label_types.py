from typing import Dict, List, Type

from label_types.models import LabelType
from projects.models import Project

from .exceptions import FieldTooLongException


class LabelTypes:
    def __init__(self, label_type_class: Type[LabelType]):
        self.types: Dict[str, LabelType] = {}
        self.label_type_class = label_type_class

    def __contains__(self, text: str) -> bool:
        return text in self.types

    def __getitem__(self, text: str) -> LabelType:
        return self.types[text]

    def save(self, label_types: List[LabelType]):
        max_length = self.label_type_class._meta.get_field("text").max_length
        if max_length is not None:
            too_long = list(dict.fromkeys(lt.text for lt in label_types if lt.text and len(lt.text) > max_length))
            if too_long:
                raise FieldTooLongException(
                    filename=self.label_type_class.__name__,
                    field_name="text",
                    values=too_long,
                    max_length=max_length,
                )
        self.label_type_class.objects.bulk_create(label_types, ignore_conflicts=True)

    def update(self, project: Project):
        types = self.label_type_class.objects.filter(project=project)
        self.types = {label_type.text: label_type for label_type in types}
