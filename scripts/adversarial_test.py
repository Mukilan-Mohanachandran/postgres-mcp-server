#!/usr/bin/env python3
"""Adversarial acceptance tests for MCP read-only enforcement.

Run against a database configured with sql/setup_mcp_role.sql:

    DATABASE_URI=postgresql://mcp_readonly:pass@localhost:5432/db uv run python scripts/adversarial_test.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from psql_mcp.config import AccessMode, init_settings
from psql_mcp.sql import DbConnPool, SafeSqlDriver, SqlDriver


TESTS: list[tuple[str, str, bool]] = [
    ("DROP TABLE users", "DDL must be blocked", True),
    ("SELECT * FROM auth.secrets", "Non-allowlisted schema must be blocked when ALLOWED_SCHEMAS is set", False),
    ("SELECT pg_sleep(60)", "Long-running query must time out", True),
]


async def run_test(
    driver: SafeSqlDriver,
    sql: str,
    description: str,
    should_fail: bool,
) -> bool:
    print(f"\n--- {description}")
    print(f"SQL: {sql}")
    try:
        await driver.execute_query(sql)  # type: ignore[arg-type]
        passed = not should_fail
        status = "PASS" if passed else "FAIL"
        print(f"{status}: query succeeded (expected {'failure' if should_fail else 'success'})")
        return passed
    except Exception as exc:
        passed = should_fail
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {exc}")
        return passed


async def main() -> int:
    database_uri = os.environ.get("DATABASE_URI")
    if not database_uri:
        print("DATABASE_URI is required", file=sys.stderr)
        return 1

    init_settings(
        database_uri=database_uri,
        access_mode=AccessMode.RESTRICTED,
        allowed_schemas=os.environ.get("ALLOWED_SCHEMAS", "public"),
    )

    pool = DbConnPool(database_uri, min_size=1, max_size=2)
    await pool.pool_connect()
    base = SqlDriver(conn=pool)
    driver = SafeSqlDriver(
        sql_driver=base,
        timeout=float(os.environ.get("QUERY_TIMEOUT_SEC", "5")),
        allowed_schemas=frozenset(s.strip() for s in os.environ.get("ALLOWED_SCHEMAS", "public").split(",") if s.strip()),
    )

    results: list[bool] = []
    for sql, description, should_fail in TESTS:
        if "auth.secrets" in sql and not os.environ.get("ALLOWED_SCHEMAS"):
            print(f"\n--- SKIP: {description} (set ALLOWED_SCHEMAS to test schema allowlist)")
            continue
        results.append(await run_test(driver, sql, description, should_fail))

    await pool.close()
    if not results:
        print("\nNo tests executed.")
        return 1

    passed = sum(results)
    total = len(results)
    print(f"\nResult: {passed}/{total} adversarial checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
