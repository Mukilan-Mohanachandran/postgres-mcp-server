# ruff: noqa: B008
"""FastMCP server exposing PostgreSQL tools for agentic RAG workflows."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
import time
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from psycopg import sql
from pydantic import Field

from .artifacts import (
    ResponseType,
    format_error_response,
    format_query_result,
    format_text_response,
)
from .audit import audit_tool
from .config import AccessMode, apply_cli_overrides, get_settings
from .sql import DbConnPool, SafeSqlDriver, SqlDriver, obfuscate_password
from .sql.introspection import (
    get_object_details_query,
    get_table_relationships_query,
    list_objects_query,
    list_schemas_query,
    search_objects_query,
)

mcp = FastMCP("psql-mcp")

db_connection = DbConnPool()
current_access_mode = AccessMode.RESTRICTED
shutdown_in_progress = False

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def get_sql_driver() -> SqlDriver | SafeSqlDriver:
    settings = get_settings()
    base_driver = SqlDriver(conn=db_connection)
    if current_access_mode == AccessMode.RESTRICTED:
        return SafeSqlDriver(
            sql_driver=base_driver,
            timeout=settings.query_timeout_sec,
            allowed_schemas=settings.allowed_schema_set,
        )
    return base_driver


def _filter_schemas(schemas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    settings = get_settings()
    allowed = settings.allowed_schema_set
    if allowed is None:
        return schemas
    return [s for s in schemas if s.get("schema_name") in allowed]


@mcp.tool(
    description="List all schemas in the database",
    annotations=ToolAnnotations(title="List Schemas", readOnlyHint=True),
)
async def list_schemas() -> ResponseType:
    settings = get_settings()
    try:
        async with audit_tool("list_schemas", settings.database_uri):
            sql_driver = await get_sql_driver()
            schemas = _filter_schemas(await list_schemas_query(sql_driver))
            return format_text_response(schemas)
    except Exception as e:
        logger.error("Error listing schemas: %s", e)
        return format_error_response(str(e))


@mcp.tool(
    description="List objects in a schema",
    annotations=ToolAnnotations(title="List Objects", readOnlyHint=True),
)
async def list_objects(
    schema_name: str = Field(description="Schema name"),
    object_type: str = Field(
        description="Object type: 'table', 'view', 'sequence', or 'extension'",
        default="table",
    ),
) -> ResponseType:
    settings = get_settings()
    try:
        settings.require_schema_allowed(schema_name)
        async with audit_tool("list_objects", settings.database_uri, extra={"schema": schema_name}):
            sql_driver = await get_sql_driver()
            objects = await list_objects_query(sql_driver, schema_name, object_type)
            return format_text_response(objects)
    except Exception as e:
        logger.error("Error listing objects: %s", e)
        return format_error_response(str(e))


@mcp.tool(
    description="Show detailed information about a database object",
    annotations=ToolAnnotations(title="Get Object Details", readOnlyHint=True),
)
async def get_object_details(
    schema_name: str = Field(description="Schema name"),
    object_name: str = Field(description="Object name"),
    object_type: str = Field(
        description="Object type: 'table', 'view', 'sequence', or 'extension'",
        default="table",
    ),
) -> ResponseType:
    settings = get_settings()
    try:
        if object_type != "extension":
            settings.require_schema_allowed(schema_name)
        async with audit_tool(
            "get_object_details",
            settings.database_uri,
            extra={"schema": schema_name, "object": object_name},
        ):
            sql_driver = await get_sql_driver()
            result = await get_object_details_query(sql_driver, schema_name, object_name, object_type)
            return format_text_response(result)
    except Exception as e:
        logger.error("Error getting object details: %s", e)
        return format_error_response(str(e))


@mcp.tool(
    description="List foreign-key relationships for tables in a schema",
    annotations=ToolAnnotations(title="Get Table Relationships", readOnlyHint=True),
)
async def get_table_relationships(
    schema_name: str = Field(description="Schema name"),
) -> ResponseType:
    settings = get_settings()
    try:
        settings.require_schema_allowed(schema_name)
        async with audit_tool("get_table_relationships", settings.database_uri, extra={"schema": schema_name}):
            sql_driver = await get_sql_driver()
            relationships = await get_table_relationships_query(sql_driver, schema_name)
            return format_text_response(relationships)
    except Exception as e:
        logger.error("Error getting table relationships: %s", e)
        return format_error_response(str(e))


@mcp.tool(
    description="Search for tables and views by name pattern across schemas",
    annotations=ToolAnnotations(title="Search Objects", readOnlyHint=True),
)
async def search_objects(
    pattern: str = Field(description="Case-insensitive substring to match against object names"),
    object_types: list[str] = Field(
        description="Object types to include: 'table' and/or 'view'",
        default=["table", "view"],
    ),
) -> ResponseType:
    settings = get_settings()
    try:
        async with audit_tool("search_objects", settings.database_uri, extra={"pattern": pattern}):
            sql_driver = await get_sql_driver()
            objects = await search_objects_query(sql_driver, pattern, object_types)
            allowed = settings.allowed_schema_set
            if allowed is not None:
                objects = [o for o in objects if o["schema"] in allowed]
            return format_text_response(objects)
    except Exception as e:
        logger.error("Error searching objects: %s", e)
        return format_error_response(str(e))


@mcp.tool(
    description="Return a small sample of rows from an allowlisted table",
    annotations=ToolAnnotations(title="Sample Rows", readOnlyHint=True),
)
async def sample_rows(
    schema_name: str = Field(description="Schema name"),
    table_name: str = Field(description="Table name"),
    limit: int = Field(description="Maximum rows to return (capped by server config)", default=10, ge=1, le=100),
) -> ResponseType:
    settings = get_settings()
    try:
        settings.require_schema_allowed(schema_name)
        sample_limit = min(limit, settings.max_rows)
        query = sql.SQL("SELECT * FROM {}.{} LIMIT {}").format(
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
            sql.Literal(sample_limit),
        )
        sql_text = query.as_string(None)
        async with audit_tool(
            "sample_rows",
            settings.database_uri,
            sql_preview=sql_text,
            extra={"schema": schema_name, "table": table_name},
        ) as audit_ctx:
            sql_driver = await get_sql_driver()
            start = time.perf_counter()
            rows = await sql_driver.execute_query(sql_text)  # type: ignore[arg-type]
            execution_ms = int((time.perf_counter() - start) * 1000)
            row_dicts = [r.cells for r in rows] if rows else []
            audit_ctx["row_count"] = len(row_dicts)
            payload = format_query_result(
                row_dicts,
                max_rows=settings.max_rows,
                max_cell_chars=settings.max_cell_chars,
                execution_ms=execution_ms,
            )
            return format_text_response(payload)
    except Exception as e:
        logger.error("Error sampling rows: %s", e)
        return format_error_response(str(e))


@mcp.tool(
    description="Explain the execution plan for a SQL query (EXPLAIN only, no ANALYZE)",
    annotations=ToolAnnotations(title="Explain Query", readOnlyHint=True),
)
async def explain_query(
    sql: str = Field(description="SQL query to explain"),
) -> ResponseType:
    settings = get_settings()
    explain_sql = f"EXPLAIN (FORMAT JSON) {sql}"
    try:
        async with audit_tool("explain_query", settings.database_uri, sql_preview=explain_sql):
            sql_driver = await get_sql_driver()
            rows = await sql_driver.execute_query(explain_sql)  # type: ignore[arg-type]
            if not rows:
                return format_error_response("No explain plan returned")
            plan = rows[0].cells.get("QUERY PLAN") or rows[0].cells
            return format_text_response(plan)
    except Exception as e:
        logger.error("Error explaining query: %s", e)
        return format_error_response(str(e))


async def execute_sql(
    sql: str = Field(description="SQL query to execute"),
) -> ResponseType:
    settings = get_settings()
    try:
        async with audit_tool("execute_sql", settings.database_uri, sql_preview=sql) as audit_ctx:
            sql_driver = await get_sql_driver()
            start = time.perf_counter()
            rows = await sql_driver.execute_query(sql)  # type: ignore[arg-type]
            execution_ms = int((time.perf_counter() - start) * 1000)
            row_dicts = [r.cells for r in rows] if rows else []
            audit_ctx["row_count"] = len(row_dicts)
            payload = format_query_result(
                row_dicts,
                max_rows=settings.max_rows,
                max_cell_chars=settings.max_cell_chars,
                execution_ms=execution_ms,
            )
            return format_text_response(payload)
    except Exception as e:
        logger.error("Error executing query: %s", e)
        return format_error_response(str(e))


async def main() -> None:
    global current_access_mode

    parser = argparse.ArgumentParser(description="PostgreSQL MCP Server for Agentic RAG")
    parser.add_argument("database_url", nargs="?", help="Database connection URL")
    parser.add_argument(
        "--access-mode",
        choices=[mode.value for mode in AccessMode],
        default=None,
        help="SQL access mode (default: restricted)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=None,
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--sse-host", default=None)
    parser.add_argument("--sse-port", type=int, default=None)
    parser.add_argument("--streamable-http-host", default=None)
    parser.add_argument("--streamable-http-port", type=int, default=None)
    args = parser.parse_args()

    database_url = args.database_url or os.environ.get("DATABASE_URI")
    settings = apply_cli_overrides(
        database_uri=database_url,
        access_mode=args.access_mode,
        transport=args.transport,
    )
    current_access_mode = settings.access_mode

    if current_access_mode == AccessMode.UNRESTRICTED:
        logger.warning(
            "UNRESTRICTED access mode enabled — use only for local development, never in production"
        )
        mcp.add_tool(
            execute_sql,
            description="Execute any SQL query",
            annotations=ToolAnnotations(title="Execute SQL", destructiveHint=True),
        )
    else:
        mcp.add_tool(
            execute_sql,
            description="Execute a read-only SQL query",
            annotations=ToolAnnotations(title="Execute SQL (Read-Only)", readOnlyHint=True),
        )

    _configure_logging()
    logger.info("Starting psql-mcp in %s mode", current_access_mode.value.upper())

    db_connection.min_size = settings.pool_min_size
    db_connection.max_size = settings.pool_max_size

    try:
        await db_connection.pool_connect(settings.database_uri)
        logger.info("Connected to database: %s", obfuscate_password(settings.database_uri))
    except Exception as e:
        logger.warning("Could not connect to database: %s", obfuscate_password(str(e)))
        logger.warning("Server will start but database operations will fail until connected.")

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s)))
    except NotImplementedError:
        logger.warning("Signal handling not supported on this platform")

    if settings.transport == "stdio":
        await mcp.run_stdio_async()
    elif settings.transport == "sse":
        mcp.settings.host = args.sse_host or settings.sse_host
        mcp.settings.port = args.sse_port or settings.sse_port
        await mcp.run_sse_async()
    else:
        mcp.settings.host = args.streamable_http_host or settings.streamable_http_host
        mcp.settings.port = args.streamable_http_port or settings.streamable_http_port
        await mcp.run_streamable_http_async()


async def shutdown(sig=None) -> None:
    global shutdown_in_progress
    if shutdown_in_progress:
        sys.exit(1)
    shutdown_in_progress = True
    logger.info("Shutting down (signal: %s)", sig)
    await db_connection.close()
    sys.exit(0)
