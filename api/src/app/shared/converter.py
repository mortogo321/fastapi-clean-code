def camel_to_snake(camel: str) -> str:
    """``UserModel`` -> ``user_model`` (same rules as the Go ``CamelToSnake``)."""
    return "".join(
        f"_{char.lower()}" if char.isupper() and index > 0 else char.lower()
        for index, char in enumerate(camel)
    )
