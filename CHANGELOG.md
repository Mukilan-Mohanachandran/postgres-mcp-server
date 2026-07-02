# Changelog

All notable changes to **psql-mcp** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-02

### Added

- Initial release of **psql-mcp**, a PostgreSQL MCP server for agentic RAG workflows.
- Eight MCP tools: `list_schemas`, `list_objects`, `get_object_details`, `get_table_relationships`, `search_objects`, `sample_rows`, `execute_sql`, `explain_query`.
- Dual access modes: `restricted` (read-only, default) and `unrestricted` (development only).
- `SafeSqlDriver` with pglast AST validation blocking DDL, DML, transactions, locking clauses, and `EXPLAIN ANALYZE`.
- Schema allowlist via `ALLOWED_SCHEMAS` environment variable.
- Async connection pooling with psycopg3 (`POOL_MIN_SIZE`, `POOL_MAX_SIZE`).
- Structured JSON query responses with `columns`, `rows`, `row_count`, `truncated`, and `execution_ms`.
- Response caps: `MAX_ROWS` and `MAX_CELL_CHARS`.
- Query timeout via `QUERY_TIMEOUT_SEC`.
- Structured audit logging to stdout (`AUDIT_LOG_SQL` optional).
- MCP transports: `stdio` (default), `sse`, and `streamable-http`.
- Pydantic-based configuration from environment and CLI.
- Helper scripts: `scripts/test_connection.py`, `scripts/adversarial_test.py`.
- Database hardening script: `sql/setup_mcp_role.sql`.
- Docker support: `Dockerfile`, `docker-compose.yml` with test Postgres seed.
- GitHub Actions CI: ruff, unit tests, integration tests.
- Cursor MCP configuration example: `.cursor/mcp.json`.
- Windows compatibility: `WindowsSelectorEventLoopPolicy` for psycopg3 async.

### Security

- `BEGIN TRANSACTION READ ONLY` enforced on every query in restricted mode.
- Function and extension allowlists in `safe_sql.py`.
- Parameterized introspection queries using psycopg `SQL`/`Identifier` composables.
- Password obfuscation in logs and error messages.
- MCP tool annotations: `readOnlyHint` on all tools in restricted mode; `destructiveHint` on `execute_sql` in unrestricted mode.
- Adversarial acceptance test script for pre-production validation.

### Known limitations

- Unqualified table names in user SQL follow the database `search_path`; schema allowlist only validates explicitly qualified references.
- `EXPLAIN ANALYZE` is blocked by design to prevent query execution side effects.
- Unsafe stored procedures (e.g. PL/Python with `COMMIT`) may bypass read-only protections; restrict `EXECUTE` on functions at the database level.
- Vector search and RAG orchestration are intentionally out of scope; use a separate retrieval pipeline.

[0.1.0]: https://github.com/your-org/psql-mcp/releases/tag/v0.1.0
