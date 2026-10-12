"""Describe a model as an Avro-style record schema (same shape as the Go ``GenerateAvroSchema``)."""

from datetime import datetime
from types import NoneType, UnionType
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from app.shared.crud.converter import convert_name_to_crud_slug

# bool must come before int: bool is a subclass of int.
_AVRO_TYPES: tuple[tuple[type, str], ...] = (
    (bool, "boolean"),
    (int, "long"),
    (float, "double"),
    (str, "string"),
    (datetime, "datetime"),
)


def avro_type(annotation: Any) -> str:
    if get_origin(annotation) is UnionType:
        # ``X | None`` is described as ``X``, like a Go pointer field.
        args = [arg for arg in get_args(annotation) if arg is not NoneType]
        return avro_type(args[0]) if len(args) == 1 else "unknown"
    if isinstance(annotation, type):
        for python_type, name in _AVRO_TYPES:
            if issubclass(annotation, python_type):
                return name
    return "unknown"


def generate_avro_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Public fields only: fields declared with ``exclude=True`` are never described."""
    return {
        "type": "record",
        "name": convert_name_to_crud_slug(model.__name__),
        "fields": [
            {"name": name, "type": avro_type(field.annotation)}
            for name, field in model.model_fields.items()
            if not field.exclude
        ],
    }
