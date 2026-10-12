from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models.user import UserModel, UserPermissionModel, UserTokenModel
from app.shared.crud.avro_schema import generate_avro_schema


class SampleRecord(BaseModel):
    id: int
    flag: bool
    ratio: float
    name: str
    nickname: str | None = None
    count: int | None = None
    born: datetime
    tags: list[str] = []
    secret: str = Field(default="", exclude=True)


def fields_of(schema: dict[str, object]) -> dict[str, str]:
    fields = schema["fields"]
    assert isinstance(fields, list)
    return {field["name"]: field["type"] for field in fields}


def test_go_record_format() -> None:
    schema = generate_avro_schema(SampleRecord)
    assert set(schema) == {"type", "name", "fields"}
    assert schema["type"] == "record"
    assert schema["name"] == "sample-record"
    assert all(set(field) == {"name", "type"} for field in schema["fields"])
    assert [field["name"] for field in schema["fields"]][:3] == ["id", "flag", "ratio"]


def test_type_mapping() -> None:
    assert fields_of(generate_avro_schema(SampleRecord)) == {
        "id": "long",
        "flag": "boolean",
        "ratio": "double",
        "name": "string",
        "nickname": "string",
        "count": "long",
        "born": "datetime",
        "tags": "unknown",
    }


def test_excluded_fields_are_absent() -> None:
    assert "secret" not in fields_of(generate_avro_schema(SampleRecord))


def test_user_model_hides_password_hash() -> None:
    schema = generate_avro_schema(UserModel)
    assert schema["name"] == "user-model"
    assert fields_of(schema) == {
        "id": "long",
        "email": "string",
        "first_name": "string",
        "last_name": "string",
        "created_at": "datetime",
        "updated_at": "datetime",
    }


def test_other_published_models() -> None:
    assert "expires_at" in fields_of(generate_avro_schema(UserTokenModel))
    assert fields_of(generate_avro_schema(UserPermissionModel))["permission"] == "string"
