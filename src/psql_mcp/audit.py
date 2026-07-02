"""Structured audit logging for MCP tool invocations."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from .config import get_settings, obfuscated_connection_target
from .sql import obfuscate_password

logger = logging.getLogger("psql_mcp.audit")


@dataclass
class AuditRecord:
    tool: str
    success: bool
    duration_ms: int
    row_count: int | None = None
    error: str | None = None
    sql_preview: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def emit(self, database_uri: str) -> None:
        settings = get_settings()
        payload: dict[str, Any] = {
            "event": "mcp_tool_call",
            "tool": self.tool,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "target": obfuscated_connection_target(database_uri),
        }
        if self.row_count is not None:
            payload["row_count"] = self.row_count
        if self.error:
            payload["error"] = obfuscate_password(self.error)
        if settings.audit_log_sql and self.sql_preview:
            payload["sql_preview"] = self.sql_preview[:500]
        if self.extra:
            payload.update(self.extra)
        logger.info(json.dumps(payload, default=str))


@asynccontextmanager
async def audit_tool(
    tool_name: str,
    database_uri: str,
    *,
    sql_preview: str | None = None,
    **extra: Any,
) -> AsyncIterator[dict[str, Any]]:
    start = time.perf_counter()
    context: dict[str, Any] = {"row_count": None}
    error: str | None = None
    try:
        yield context
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        AuditRecord(
            tool=tool_name,
            success=error is None,
            duration_ms=duration_ms,
            row_count=context.get("row_count"),
            error=error,
            sql_preview=sql_preview,
            extra=extra,
        ).emit(database_uri)
