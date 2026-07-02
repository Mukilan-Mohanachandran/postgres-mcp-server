"""Response formatting helpers for MCP tools."""

from __future__ import annotations

import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

import mcp.types as types

ResponseType = list[types.TextContent | types.ImageContent | types.EmbeddedResource]


def _serialize_cell(value: Any, max_cell_chars: int) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, (bytes, memoryview)):
        text = bytes(value).decode("utf-8", errors="replace")
        if len(text) > max_cell_chars:
            return text[: max_cell_chars - 3] + "..."
        return text
    if isinstance(value, str) and len(value) > max_cell_chars:
        return value[: max_cell_chars - 3] + "..."
    if isinstance(value, (list, dict)):
        encoded = json.dumps(value, default=str)
        if len(encoded) > max_cell_chars:
            return encoded[: max_cell_chars - 3] + "..."
        return value
    return value


def format_query_result(
    rows: list[dict[str, Any]],
    *,
    max_rows: int,
    max_cell_chars: int,
    execution_ms: int,
) -> dict[str, Any]:
    truncated = len(rows) > max_rows
    limited = rows[:max_rows]
    columns: list[str] = list(limited[0].keys()) if limited else []
    serialized_rows: list[list[Any]] = []
    for row in limited:
        serialized_rows.append([_serialize_cell(row.get(col), max_cell_chars) for col in columns])
    return {
        "columns": columns,
        "rows": serialized_rows,
        "row_count": len(limited),
        "truncated": truncated,
        "execution_ms": execution_ms,
    }


def format_text_response(data: Any) -> ResponseType:
    if isinstance(data, str):
        text = data
    else:
        text = json.dumps(data, indent=2, default=str)
    return [types.TextContent(type="text", text=text)]


def format_error_response(error: str) -> ResponseType:
    return format_text_response({"error": error})
