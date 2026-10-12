from app.shared.converter import camel_to_snake


def convert_name_to_crud_slug(name: str) -> str:
    """``user_tokens`` -> ``user-tokens``, ``UserModel`` -> ``user-model``."""
    return camel_to_snake(name).replace("_", "-")
