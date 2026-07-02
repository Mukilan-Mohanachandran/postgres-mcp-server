from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from psql_mcp.sql import SafeSqlDriver, SqlDriver


@pytest.fixture
def restricted_driver():
    mock_pool = MagicMock()
    mock_pool._is_valid = True
    base = SqlDriver(conn=mock_pool)
    return SafeSqlDriver(sql_driver=base, timeout=30.0, allowed_schemas=frozenset({"public"}))


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "SELECT id, name FROM users WHERE id = 1",
        "EXPLAIN SELECT * FROM users",
        "SHOW timezone",
    ],
)
def test_allows_safe_queries(restricted_driver, sql):
    restricted_driver._validate(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE users",
        "INSERT INTO users (name) VALUES ('x')",
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "CREATE TABLE evil (id int)",
        "SELECT * FROM users FOR UPDATE",
        "EXPLAIN ANALYZE SELECT * FROM users",
    ],
)
def test_blocks_unsafe_queries(restricted_driver, sql):
    with pytest.raises(ValueError):
        restricted_driver._validate(sql)


def test_blocks_disallowed_schema(restricted_driver):
    with pytest.raises(ValueError, match="ALLOWED_SCHEMAS"):
        restricted_driver._validate("SELECT * FROM auth.secrets")


def test_allows_allowlisted_schema(restricted_driver):
    restricted_driver._validate('SELECT * FROM public.users')


@pytest.mark.asyncio
async def test_force_readonly_enforcement():
    mock_pool = MagicMock()
    mock_pool._is_valid = True
    mock_execute = AsyncMock(return_value=[SqlDriver.RowResult(cells={"test": "value"})])

    base = SqlDriver(conn=mock_pool)
    driver = SafeSqlDriver(sql_driver=base, timeout=30.0)

    with patch.object(SqlDriver, "_execute_with_connection", mock_execute):
        await driver.execute_query("SELECT 1")
        assert mock_execute.call_args[1]["force_readonly"] is True

        mock_execute.reset_mock()
        await driver.execute_query("SELECT 1", force_readonly=False)
        assert mock_execute.call_args[1]["force_readonly"] is True
