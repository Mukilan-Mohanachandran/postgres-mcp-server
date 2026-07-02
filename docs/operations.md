# Operations Guide

This guide covers running, deploying, monitoring, and maintaining **psql-mcp v0.1.0** in development and production environments.

---

## Local development

```bash
uv sync --dev
uv run psql-mcp --access-mode=restricted
```

Run tests:

```bash
uv run ruff check src tests
uv run pytest tests/unit -v
```

Integration tests require a running Postgres instance:

```bash
docker compose up postgres -d
TEST_DATABASE_URI=postgresql://postgres:postgres@localhost:5433/psql_mcp_test \
  uv run pytest tests/integration -m integration -v
```

---

## Docker deployment

### Postgres only (for testing)

```bash
docker compose up postgres -d
```

Postgres is available at `localhost:5433` with seed data from `sql/init_test_db.sql`.

### Full stack (MCP + Postgres)

```bash
docker compose --profile full up --build
```

| Service | Port | Description |
|---------|------|-------------|
| `postgres` | 5433 | PostgreSQL 16 with test seed |
| `mcp` | 8000 | psql-mcp on streamable-http transport |

The MCP container runs as a non-root user with `ACCESS_MODE=restricted`.

### Build image manually

```bash
docker build -t psql-mcp:0.1.0 .
docker run --env-file .env psql-mcp:0.1.0 --access-mode=restricted
```

---

## Transport modes

| Transport | Command | Client |
|-----------|---------|--------|
| stdio | `uv run psql-mcp` | Cursor, Claude Desktop |
| sse | `TRANSPORT=sse uv run psql-mcp` | HTTP MCP clients |
| streamable-http | `TRANSPORT=streamable-http uv run psql-mcp` | Remote RAG orchestrators |

For remote RAG agents, use `streamable-http` and set:

```env
TRANSPORT=streamable-http
STREAMABLE_HTTP_HOST=0.0.0.0
STREAMABLE_HTTP_PORT=8000
```

---

## Audit logging

Every tool invocation emits a structured JSON log line to stdout:

```json
{
  "event": "mcp_tool_call",
  "tool": "execute_sql",
  "success": true,
  "duration_ms": 45,
  "row_count": 10,
  "target": "db.example.com/myapp",
  "schema": "public"
}
```

| Field | Description |
|-------|-------------|
| `event` | Always `mcp_tool_call` |
| `tool` | Tool name |
| `success` | `true` or `false` |
| `duration_ms` | Execution time |
| `row_count` | Rows returned (query tools only) |
| `target` | `host/database` (no credentials) |
| `error` | Error message on failure (passwords obfuscated) |
| `sql_preview` | First 500 chars of SQL (only if `AUDIT_LOG_SQL=true`) |

Enable SQL preview for debugging only:

```env
AUDIT_LOG_SQL=true
LOG_LEVEL=DEBUG
```

---

## Client wiring

### Cursor IDE

See [`.cursor/mcp.json`](../.cursor/mcp.json) and [configuration.md](configuration.md#cursor-mcp-configuration).

### Custom RAG orchestrator (Python)

Connect via stdio or streamable-http using the MCP Python client:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(
    command="uv",
    args=["run", "psql-mcp", "--access-mode=restricted"],
    env={"DATABASE_URI": "...", "ALLOWED_SCHEMAS": "public"},
)
async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("list_schemas", arguments={})
```

### MCP Inspector (development)

```bash
npx @modelcontextprotocol/inspector uv run psql-mcp --access-mode=restricted
```

---

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on push and pull requests:

1. Start Postgres 16 service container
2. Seed test database with `sql/init_test_db.sql`
3. `ruff check src tests`
4. `pytest tests/unit`
5. `pytest tests/integration -m integration`

---

## Health checks

psql-mcp does not expose a dedicated `/health` HTTP endpoint in v0.1.0. Verify health by:

1. **Connection test:** `uv run python scripts/test_connection.py`
2. **Startup log:** `Connected to database` in server output
3. **Tool call:** invoke `list_schemas` via MCP Inspector or Cursor

---

## Graceful shutdown

The server handles `SIGTERM` and `SIGINT` by closing the connection pool before exit. On Windows, signal handling is limited; stop the process with `Ctrl+C`.

---

## Helper scripts

| Script | Purpose |
|--------|---------|
| `scripts/test_connection.py` | 3-step TCP / auth / query connectivity test |
| `scripts/adversarial_test.py` | Pre-production security acceptance tests |

---

## Version and upgrades

Current version: **0.1.0** (see `pyproject.toml`).

For future upgrades:

1. Read [CHANGELOG.md](../CHANGELOG.md) for breaking changes
2. Update `uv sync`
3. Re-run adversarial tests
4. Verify MCP client configuration
