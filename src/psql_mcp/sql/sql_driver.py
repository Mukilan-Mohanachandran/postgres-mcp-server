"""SQL driver adapter for PostgreSQL connections."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, LiteralString
from urllib.parse import urlparse, urlunparse

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


def obfuscate_password(text: str | None) -> str | None:
    """Obfuscate password in connection URLs, DSN strings, and error messages."""
    if text is None:
        return None
    if not text:
        return text

    try:
        parsed = urlparse(text)
        if parsed.scheme and parsed.netloc and parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "****")
            return urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        pass

    url_pattern = re.compile(r"(postgres(?:ql)?:\/\/[^:]+:)([^@]+)(@[^\/\s]+)")
    text = re.sub(url_pattern, r"\1****\3", text)
    param_pattern = re.compile(r'(password=)([^\s&;"\']+)', re.IGNORECASE)
    text = re.sub(param_pattern, r"\1****", text)
    dsn_single_quote = re.compile(r"(password\s*=\s*')([^']+)(')", re.IGNORECASE)
    text = re.sub(dsn_single_quote, r"\1****\3", text)
    dsn_double_quote = re.compile(r'(password\s*=\s*")([^"]+)(")', re.IGNORECASE)
    text = re.sub(dsn_double_quote, r"\1****\3", text)
    return text


class DbConnPool:
    """Database connection manager using psycopg's async connection pool."""

    def __init__(
        self,
        connection_url: str | None = None,
        *,
        min_size: int = 2,
        max_size: int = 10,
    ):
        self.connection_url = connection_url
        self.min_size = min_size
        self.max_size = max_size
        self.pool: AsyncConnectionPool | None = None
        self._is_valid = False
        self._last_error: str | None = None

    async def pool_connect(self, connection_url: str | None = None) -> AsyncConnectionPool:
        if self.pool and self._is_valid:
            return self.pool

        url = connection_url or self.connection_url
        self.connection_url = url
        if not url:
            self._is_valid = False
            self._last_error = "Database connection URL not provided"
            raise ValueError(self._last_error)

        await self.close()

        try:
            self.pool = AsyncConnectionPool(
                conninfo=url,
                min_size=self.min_size,
                max_size=self.max_size,
                open=False,
            )
            await self.pool.open()
            async with self.pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
            self._is_valid = True
            self._last_error = None
            return self.pool
        except Exception as e:
            self._is_valid = False
            self._last_error = str(e)
            await self.close()
            raise ValueError(f"Connection attempt failed: {obfuscate_password(str(e))}") from e

    async def close(self) -> None:
        if self.pool:
            try:
                await self.pool.close()
            except Exception as e:
                logger.warning("Error closing connection pool: %s", e)
            finally:
                self.pool = None
                self._is_valid = False

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    @property
    def last_error(self) -> str | None:
        return self._last_error


class SqlDriver:
    """PostgreSQL query executor with optional read-only transactions."""

    @dataclass
    class RowResult:
        cells: dict[str, Any]

    def __init__(self, conn: Any = None, engine_url: str | None = None):
        if conn:
            self.conn = conn
            self.is_pool = isinstance(conn, DbConnPool)
        elif engine_url:
            self.engine_url = engine_url
            self.conn = None
            self.is_pool = False
        else:
            raise ValueError("Either conn or engine_url must be provided")

    def connect(self):
        if self.conn is not None:
            return self.conn
        if self.engine_url:
            self.conn = DbConnPool(self.engine_url)
            self.is_pool = True
            return self.conn
        raise ValueError("Connection not established")

    async def execute_query(
        self,
        query: LiteralString,
        params: list[Any] | None = None,
        force_readonly: bool = False,
    ) -> list[RowResult] | None:
        try:
            if self.conn is None:
                self.connect()
                if self.conn is None:
                    raise ValueError("Connection not established")

            if self.is_pool:
                pool = await self.conn.pool_connect()
                async with pool.connection() as connection:
                    return await self._execute_with_connection(connection, query, params, force_readonly=force_readonly)
            return await self._execute_with_connection(self.conn, query, params, force_readonly=force_readonly)
        except Exception as e:
            if self.conn and self.is_pool:
                self.conn._is_valid = False
                self.conn._last_error = str(e)
            elif self.conn and not self.is_pool:
                self.conn = None
            raise e

    async def _execute_with_connection(
        self,
        connection,
        query,
        params,
        force_readonly: bool,
    ) -> list[RowResult] | None:
        transaction_started = False
        try:
            async with connection.cursor(row_factory=dict_row) as cursor:
                if force_readonly:
                    await cursor.execute("BEGIN TRANSACTION READ ONLY")
                    transaction_started = True

                if params:
                    await cursor.execute(query, params)
                else:
                    await cursor.execute(query)

                while cursor.nextset():
                    pass

                if cursor.description is None:
                    if not force_readonly:
                        await cursor.execute("COMMIT")
                    elif transaction_started:
                        await cursor.execute("ROLLBACK")
                        transaction_started = False
                    return None

                rows = await cursor.fetchall()

                if not force_readonly:
                    await cursor.execute("COMMIT")
                elif transaction_started:
                    await cursor.execute("ROLLBACK")
                    transaction_started = False

                return [SqlDriver.RowResult(cells=dict(row)) for row in rows]
        except Exception as e:
            if transaction_started:
                try:
                    await connection.rollback()
                except Exception as rollback_error:
                    logger.error("Error rolling back transaction: %s", rollback_error)
            logger.error("Error executing query (%s): %s", query[:200], e)
            raise e
