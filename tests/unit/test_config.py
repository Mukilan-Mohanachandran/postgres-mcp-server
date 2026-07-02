import pytest

from psql_mcp.config import AccessMode, Settings, init_settings


def test_settings_parses_allowed_schemas():
    settings = Settings(
        DATABASE_URI="postgresql://user:pass@localhost:5432/db",
        ALLOWED_SCHEMAS="public, analytics",
    )
    assert settings.allowed_schema_set == frozenset({"public", "analytics"})


def test_require_schema_allowed():
    settings = Settings(
        DATABASE_URI="postgresql://user:pass@localhost:5432/db",
        ALLOWED_SCHEMAS="public",
    )
    settings.require_schema_allowed("public")
    with pytest.raises(ValueError, match="ALLOWED_SCHEMAS"):
        settings.require_schema_allowed("auth")


def test_init_settings_overrides():
    init_settings(
        database_uri="postgresql://u:p@host:5432/test",
        access_mode=AccessMode.RESTRICTED,
    )
    from psql_mcp.config import get_settings

    assert get_settings().access_mode == AccessMode.RESTRICTED
