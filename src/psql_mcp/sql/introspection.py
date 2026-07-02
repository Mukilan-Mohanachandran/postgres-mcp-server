"""Parameterized schema introspection queries."""

from __future__ import annotations

from typing import Any

from .safe_sql import SafeSqlDriver
from .sql_driver import SqlDriver


async def list_schemas_query(sql_driver: SqlDriver) -> list[dict[str, Any]]:
    rows = await sql_driver.execute_query(
        """
        SELECT
            schema_name,
            schema_owner,
            CASE
                WHEN schema_name LIKE 'pg_%' THEN 'System Schema'
                WHEN schema_name = 'information_schema' THEN 'System Information Schema'
                ELSE 'User Schema'
            END AS schema_type
        FROM information_schema.schemata
        ORDER BY schema_type, schema_name
        """
    )
    return [row.cells for row in rows] if rows else []


async def list_objects_query(
    sql_driver: SqlDriver,
    schema_name: str,
    object_type: str,
) -> list[dict[str, Any]]:
    if object_type in ("table", "view"):
        table_type = "BASE TABLE" if object_type == "table" else "VIEW"
        rows = await SafeSqlDriver.execute_param_query(
            sql_driver,
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = {} AND table_type = {}
            ORDER BY table_name
            """,
            [schema_name, table_type],
        )
        return (
            [
                {
                    "schema": row.cells["table_schema"],
                    "name": row.cells["table_name"],
                    "type": row.cells["table_type"],
                }
                for row in rows
            ]
            if rows
            else []
        )

    if object_type == "sequence":
        rows = await SafeSqlDriver.execute_param_query(
            sql_driver,
            """
            SELECT sequence_schema, sequence_name, data_type
            FROM information_schema.sequences
            WHERE sequence_schema = {}
            ORDER BY sequence_name
            """,
            [schema_name],
        )
        return (
            [
                {
                    "schema": row.cells["sequence_schema"],
                    "name": row.cells["sequence_name"],
                    "data_type": row.cells["data_type"],
                }
                for row in rows
            ]
            if rows
            else []
        )

    if object_type == "extension":
        rows = await sql_driver.execute_query(
            """
            SELECT extname, extversion, extrelocatable
            FROM pg_extension
            ORDER BY extname
            """
        )
        return (
            [
                {
                    "name": row.cells["extname"],
                    "version": row.cells["extversion"],
                    "relocatable": row.cells["extrelocatable"],
                }
                for row in rows
            ]
            if rows
            else []
        )

    raise ValueError(f"Unsupported object type: {object_type}")


async def get_object_details_query(
    sql_driver: SqlDriver,
    schema_name: str,
    object_name: str,
    object_type: str,
) -> dict[str, Any]:
    if object_type in ("table", "view"):
        col_rows = await SafeSqlDriver.execute_param_query(
            sql_driver,
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = {} AND table_name = {}
            ORDER BY ordinal_position
            """,
            [schema_name, object_name],
        )
        columns = (
            [
                {
                    "column": r.cells["column_name"],
                    "data_type": r.cells["data_type"],
                    "is_nullable": r.cells["is_nullable"],
                    "default": r.cells["column_default"],
                }
                for r in col_rows
            ]
            if col_rows
            else []
        )

        con_rows = await SafeSqlDriver.execute_param_query(
            sql_driver,
            """
            SELECT tc.constraint_name, tc.constraint_type, kcu.column_name
            FROM information_schema.table_constraints AS tc
            LEFT JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = {} AND tc.table_name = {}
            """,
            [schema_name, object_name],
        )
        constraints: dict[str, dict[str, Any]] = {}
        if con_rows:
            for row in con_rows:
                cname = row.cells["constraint_name"]
                if cname not in constraints:
                    constraints[cname] = {"type": row.cells["constraint_type"], "columns": []}
                col = row.cells["column_name"]
                if col:
                    constraints[cname]["columns"].append(col)

        idx_rows = await SafeSqlDriver.execute_param_query(
            sql_driver,
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = {} AND tablename = {}
            """,
            [schema_name, object_name],
        )
        indexes = (
            [{"name": r.cells["indexname"], "definition": r.cells["indexdef"]} for r in idx_rows]
            if idx_rows
            else []
        )
        return {
            "basic": {"schema": schema_name, "name": object_name, "type": object_type},
            "columns": columns,
            "constraints": [{"name": name, **data} for name, data in constraints.items()],
            "indexes": indexes,
        }

    if object_type == "sequence":
        rows = await SafeSqlDriver.execute_param_query(
            sql_driver,
            """
            SELECT sequence_schema, sequence_name, data_type, start_value, increment
            FROM information_schema.sequences
            WHERE sequence_schema = {} AND sequence_name = {}
            """,
            [schema_name, object_name],
        )
        if rows and rows[0]:
            row = rows[0]
            return {
                "schema": row.cells["sequence_schema"],
                "name": row.cells["sequence_name"],
                "data_type": row.cells["data_type"],
                "start_value": row.cells["start_value"],
                "increment": row.cells["increment"],
            }
        return {}

    if object_type == "extension":
        rows = await SafeSqlDriver.execute_param_query(
            sql_driver,
            """
            SELECT extname, extversion, extrelocatable
            FROM pg_extension
            WHERE extname = {}
            """,
            [object_name],
        )
        if rows and rows[0]:
            row = rows[0]
            return {
                "name": row.cells["extname"],
                "version": row.cells["extversion"],
                "relocatable": row.cells["extrelocatable"],
            }
        return {}

    raise ValueError(f"Unsupported object type: {object_type}")


async def get_table_relationships_query(
    sql_driver: SqlDriver,
    schema_name: str,
) -> list[dict[str, Any]]:
    rows = await SafeSqlDriver.execute_param_query(
        sql_driver,
        """
        SELECT
            tc.table_schema AS source_schema,
            tc.table_name AS source_table,
            kcu.column_name AS source_column,
            ccu.table_schema AS target_schema,
            ccu.table_name AS target_table,
            ccu.column_name AS target_column,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = {}
        ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position
        """,
        [schema_name],
    )
    return [row.cells for row in rows] if rows else []


async def search_objects_query(
    sql_driver: SqlDriver,
    pattern: str,
    object_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    types = object_types or ["table", "view"]
    type_literals: list[str] = []
    if "table" in types:
        type_literals.append("BASE TABLE")
    if "view" in types:
        type_literals.append("VIEW")
    if not type_literals:
        raise ValueError("object_types must include 'table' and/or 'view'")

    if len(type_literals) == 1:
        rows = await SafeSqlDriver.execute_param_query(
            sql_driver,
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_type = {}
              AND table_name ILIKE {}
            ORDER BY table_schema, table_name
            LIMIT 100
            """,
            [type_literals[0], f"%{pattern}%"],
        )
    else:
        rows = await SafeSqlDriver.execute_param_query(
            sql_driver,
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_type IN ('BASE TABLE', 'VIEW')
              AND table_name ILIKE {}
            ORDER BY table_schema, table_name
            LIMIT 100
            """,
            [f"%{pattern}%"],
        )
    return (
        [
            {
                "schema": row.cells["table_schema"],
                "name": row.cells["table_name"],
                "type": row.cells["table_type"],
            }
            for row in rows
        ]
        if rows
        else []
    )
