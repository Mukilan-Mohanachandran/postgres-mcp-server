"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio
import os
import sys

import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Default test database URI — override via TEST_DATABASE_URI for integration tests.
os.environ.setdefault("DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/psql_mcp_test")
os.environ.setdefault("ACCESS_MODE", "restricted")
os.environ.setdefault("ALLOWED_SCHEMAS", "public")


@pytest.fixture(autouse=True)
def reset_settings():
    import psql_mcp.config as config_module

    config_module._settings = None
    yield
    config_module._settings = None
