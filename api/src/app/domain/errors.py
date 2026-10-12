"""Expected business failures raised by use cases; each delivery layer maps them to its protocol."""


class DomainError(Exception):
    pass


class EmailAlreadyRegisteredError(DomainError):
    def __init__(self) -> None:
        super().__init__("email is already registered")


class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        # Deliberately the same for unknown email and wrong password.
        super().__init__("invalid email or password")


class InvalidTokenError(DomainError):
    """The token is malformed, expired, revoked or of the wrong type."""


class EntityModelNotFoundError(DomainError):
    def __init__(self, entity_model_slug: str) -> None:
        super().__init__(f"data model {entity_model_slug!r} not found")


class RecordNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("record not found")
