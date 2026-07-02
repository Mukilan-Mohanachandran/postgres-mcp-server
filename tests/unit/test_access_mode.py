from unittest.mock import MagicMock, patch

import pytest

from psql_mcp.config import init_settings
from psql_mcp.server import AccessMode as ServerAccessMode
from psql_mcp.server import get_sql_driver
from psql_mcp.sql import SafeSqlDriver, SqlDriver


@pytest.mark.asyncio
async def test_get_sql_driver_modes():
    mock_pool = MagicMock()
    mock_pool._is_valid = True

    init_settings(
        database_uri="postgresql://u:p@localhost:5432/db",
        access_mode="restricted",
    )

    with patch("psql_mcp.server.db_connection", mock_pool):
        with patch("psql_mcp.server.current_access_mode", ServerAccessMode.RESTRICTED):
            driver = await get_sql_driver()
            assert isinstance(driver, SafeSqlDriver)

        with patch("psql_mcp.server.current_access_mode", ServerAccessMode.UNRESTRICTED):
            driver = await get_sql_driver()
            assert isinstance(driver, SqlDriver)
            assert not isinstance(driver, SafeSqlDriver)
