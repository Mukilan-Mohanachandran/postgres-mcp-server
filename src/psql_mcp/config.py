"""Application configuration from environment and CLI."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SYSTEM_SCHEMAS = frozenset({"information_schema", "pg_catalog"})


class AccessMode(StrEnum):
    RESTRICTED = "restricted"
    UNRESTRICTED = "unrestricted"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_uri: str = Field(..., validation_alias="DATABASE_URI")
    access_mode: AccessMode = Field(default=AccessMode.RESTRICTED, validation_alias="ACCESS_MODE")
    allowed_schemas: str = Field(default="", validation_alias="ALLOWED_SCHEMAS")
    max_rows: int = Field(default=1000, ge=1, le=100_000, validation_alias="MAX_ROWS")
    max_cell_chars: int = Field(default=500, ge=1, le=10_000, validation_alias="MAX_CELL_CHARS")
    query_timeout_sec: float = Field(default=30.0, ge=1.0, le=600.0, validation_alias="QUERY_TIMEOUT_SEC")
    transport: Literal["stdio", "sse", "streamable-http"] = Field(default="stdio", validation_alias="TRANSPORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    audit_log_sql: bool = Field(default=False, validation_alias="AUDIT_LOG_SQL")
    pool_min_size: int = Field(default=2, ge=1, validation_alias="POOL_MIN_SIZE")
    pool_max_size: int = Field(default=10, ge=1, validation_alias="POOL_MAX_SIZE")
    sse_host: str = Field(default="localhost", validation_alias="SSE_HOST")
    sse_port: int = Field(default=8000, validation_alias="SSE_PORT")
    streamable_http_host: str = Field(default="localhost", validation_alias="STREAMABLE_HTTP_HOST")
    streamable_http_port: int = Field(default=8000, validation_alias="STREAMABLE_HTTP_PORT")

    @field_validator("database_uri")
    @classmethod
    def validate_database_uri(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URI must not be empty")
        parsed = urlparse(value)
        if parsed.scheme not in ("postgresql", "postgres"):
            raise ValueError("DATABASE_URI must use postgresql:// or postgres:// scheme")
        return value

    @property
    def allowed_schema_set(self) -> frozenset[str] | None:
        if not self.allowed_schemas.strip():
            return None
        return frozenset(s.strip() for s in self.allowed_schemas.split(",") if s.strip())

    def is_schema_allowed(self, schema_name: str, *, for_introspection: bool = False) -> bool:
        if for_introspection and schema_name in SYSTEM_SCHEMAS:
            return True
        allowed = self.allowed_schema_set
        if allowed is None:
            return True
        return schema_name in allowed

    def require_schema_allowed(self, schema_name: str, *, for_introspection: bool = False) -> None:
        if not self.is_schema_allowed(schema_name, for_introspection=for_introspection):
            allowed = self.allowed_schema_set or frozenset()
            raise ValueError(
                f"Schema '{schema_name}' is not in ALLOWED_SCHEMAS. "
                f"Allowed: {', '.join(sorted(allowed)) or '(none configured)'}"
            )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def init_settings(**overrides: object) -> Settings:
    """Initialize settings from environment with optional overrides (for CLI)."""
    global _settings
    env_overrides = {k: v for k, v in overrides.items() if v is not None}
    _settings = Settings(**env_overrides)
    return _settings


def apply_cli_overrides(
    database_uri: str | None = None,
    access_mode: str | None = None,
    transport: str | None = None,
) -> Settings:
    overrides: dict[str, object] = {}
    if database_uri:
        overrides["database_uri"] = database_uri
    if access_mode:
        overrides["access_mode"] = access_mode
    if transport:
        overrides["transport"] = transport
    if overrides:
        return init_settings(**overrides)
    return get_settings()


@lru_cache(maxsize=1)
def obfuscated_connection_target(database_uri: str) -> str:
    parsed = urlparse(database_uri)
    host = parsed.hostname or "unknown"
    db = (parsed.path or "/").lstrip("/") or "unknown"
    return f"{host}/{db}"
