"""Configuration from environment variables and ``.env`` (port of config/config.go).

``.env`` values may use ``${VAR:-default}``; real environment variables always win.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    name: str = "FastAPI Clean Code"
    version: str = "0.1.0"
    secret_key: SecretStr = Field(min_length=32)
    jwt_access_expires: int = Field(default=900, gt=0, description="seconds")
    jwt_refresh_expires: int = Field(default=604_800, gt=0, description="seconds")
    bcrypt_rounds: int = Field(default=12, ge=4, le=31)
    cors_origins: list[str] = Field(default_factory=list)
    docs_enabled: bool = True

    @property
    def jwt_issuer(self) -> str:
        """``FastAPI Clean Code`` -> ``fastapi-clean-code``; used as JWT ``iss`` and ``aud``."""
        return "-".join(self.name.lower().split())


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_", env_file=".env", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: SecretStr
    db: str = "postgres"


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_postgres_settings() -> PostgresSettings:
    return PostgresSettings()
