"""Integration tests — require Postgres (docker compose up postgres)."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio

from psql_mcp.config import init_settings
from psql_mcp.sql import DbConnPool, SafeSqlDriver, SqlDriver
from psql_mcp.sql.introspection import list_schemas_query

pytestmark = pytest.mark.integration

DATABASE_URI = os.environ.get(
    "TEST_DATABASE_URI",
    "postgresql://postgres:postgres@localhost:5433/psql_mcp_test",
)


@pytest_asyncio.fixture
async def sql_driver():
    init_settings(database_uri=DATABASE_URI, access_mode="restricted", allowed_schemas="public")
    pool = DbConnPool(DATABASE_URI, min_size=1, max_size=2)
    await pool.pool_connect()
    base = SqlDriver(conn=pool)
    driver = SafeSqlDriver(sql_driver=base, timeout=10.0, allowed_schemas=frozenset({"public"}))
    yield driver
    await pool.close()


@pytest.mark.asyncio
async def test_list_schemas(sql_driver):
    schemas = await list_schemas_query(sql_driver)
    names = {s["schema_name"] for s in schemas}
    assert "public" in names


@pytest.mark.asyncio
async def test_select_query(sql_driver):
    rows = await sql_driver.execute_query("SELECT 1 AS one")  # type: ignore[arg-type]
    assert rows is not None
    assert rows[0].cells["one"] == 1
