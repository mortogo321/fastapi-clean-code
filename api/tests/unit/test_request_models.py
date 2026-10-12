from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.entities.user import UserLoginRequest, UserRefreshTokenRequest, UserRegisterRequest


def register_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "email": "user@example.com",
        "password": "password123",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }
    payload.update(overrides)
    return payload


def test_register_lowercases_email() -> None:
    request = UserRegisterRequest.model_validate(register_payload(email="Ada.L@Example.COM"))
    assert request.email == "ada.l@example.com"


def test_login_normalizes_email() -> None:
    request = UserLoginRequest.model_validate({"email": "  Ada@Example.COM ", "password": "x"})
    assert request.email == "ada@example.com"


@pytest.mark.parametrize("password", ["a" * 8, "a" * 72, "ก" * 24])
def test_password_boundaries_accepted(password: str) -> None:
    assert UserRegisterRequest.model_validate(register_payload(password=password)).password


@pytest.mark.parametrize("password", ["a" * 7, "a" * 73, "ก" * 25, ""])
def test_password_boundaries_rejected(password: str) -> None:
    with pytest.raises(ValidationError):
        UserRegisterRequest.model_validate(register_payload(password=password))


def test_login_password_byte_limit() -> None:
    with pytest.raises(ValidationError):
        UserLoginRequest.model_validate({"email": "a@b.co", "password": "ก" * 25})
    with pytest.raises(ValidationError):
        UserLoginRequest.model_validate({"email": "a@b.co", "password": ""})


def test_names_are_stripped() -> None:
    request = UserRegisterRequest.model_validate(
        register_payload(first_name="  Ada ", last_name="\tLovelace\n")
    )
    assert (request.first_name, request.last_name) == ("Ada", "Lovelace")


@pytest.mark.parametrize("field", ["first_name", "last_name"])
@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_empty_names_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        UserRegisterRequest.model_validate(register_payload(**{field: value}))


def test_name_too_long_rejected() -> None:
    with pytest.raises(ValidationError):
        UserRegisterRequest.model_validate(register_payload(first_name="a" * 101))


def test_invalid_email_rejected() -> None:
    with pytest.raises(ValidationError):
        UserRegisterRequest.model_validate(register_payload(email="not-an-email"))


def test_extra_keys_forbidden() -> None:
    with pytest.raises(ValidationError):
        UserRegisterRequest.model_validate(register_payload(is_admin=True))
    with pytest.raises(ValidationError):
        UserLoginRequest.model_validate({"email": "a@b.co", "password": "x", "extra": 1})
    with pytest.raises(ValidationError):
        UserRefreshTokenRequest.model_validate({"refresh_token": "t", "extra": 1})
