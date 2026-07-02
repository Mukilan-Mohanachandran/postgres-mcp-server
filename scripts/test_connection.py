#!/usr/bin/env python3
"""Test DATABASE_URI connectivity. Loads credentials from .env — nothing hardcoded."""

from __future__ import annotations

import asyncio
import sys
import time

from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from psql_mcp.config import get_settings, init_settings
from psql_mcp.sql import DbConnPool, obfuscate_password


async def main() -> int:
    init_settings()
    settings = get_settings()
    uri = settings.database_uri
    safe_uri = obfuscate_password(uri) or uri

    print("Testing connection...")
    print(f"  Target: {safe_uri}")
    print(f"  Timeout: pool default (30s max wait)")

    # 1. TCP reachability
    from urllib.parse import urlparse

    parsed = urlparse(uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    print(f"\n[1/3] TCP check {host}:{port} ...")
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=5.0)
        writer.close()
        await writer.wait_closed()
        print("  OK — port is open")
    except TimeoutError:
        print("  FAIL — TCP timeout (host unreachable or firewall blocking)")
        return 1
    except OSError as e:
        print(f"  FAIL — {e}")
        return 1

    # 2. Postgres handshake + auth
    print("\n[2/3] Postgres auth (SELECT 1) ...")
    pool = DbConnPool(uri, min_size=1, max_size=1)
    start = time.perf_counter()
    try:
        await asyncio.wait_for(pool.pool_connect(), timeout=15.0)
        elapsed = int((time.perf_counter() - start) * 1000)
        print(f"  OK — connected in {elapsed} ms")
    except TimeoutError:
        print("  FAIL — Postgres handshake timed out after 15s")
        print("  Common causes: wrong password, pg_hba.conf rejects your IP, SSL mismatch")
        return 1
    except ValueError as e:
        print(f"  FAIL — {obfuscate_password(str(e))}")
        return 1
    except Exception as e:
        print(f"  FAIL — {obfuscate_password(str(e))}")
        return 1

    # 3. Simple query
    print("\n[3/3] Query check ...")
    try:
        from psql_mcp.sql import SqlDriver

        driver = SqlDriver(conn=pool)
        rows = await driver.execute_query("SELECT current_database() AS db, current_user AS user, version() AS version")
        if rows:
            cells = rows[0].cells
            print(f"  database: {cells.get('db')}")
            print(f"  user:     {cells.get('user')}")
            ver = str(cells.get("version", ""))[:80]
            print(f"  version:  {ver}...")
        print("\nConnection string is valid.")
        return 0
    except Exception as e:
        print(f"  FAIL — {obfuscate_password(str(e))}")
        return 1
    finally:
        await pool.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
