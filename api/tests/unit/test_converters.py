import pytest

from app.shared.converter import camel_to_snake
from app.shared.crud.converter import convert_name_to_crud_slug


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("UserModel", "user_model"),
        ("user", "user"),
        ("User", "user"),
        ("", ""),
        ("userToken", "user_token"),
        ("HTTPServer", "h_t_t_p_server"),
    ],
)
def test_camel_to_snake(name: str, expected: str) -> None:
    assert camel_to_snake(name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("user_tokens", "user-tokens"),
        ("UserModel", "user-model"),
        ("users", "users"),
    ],
)
def test_convert_name_to_crud_slug(name: str, expected: str) -> None:
    assert convert_name_to_crud_slug(name) == expected
