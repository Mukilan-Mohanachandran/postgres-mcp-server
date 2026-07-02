# Configuration Reference

**psql-mcp v0.1.0** is configured via environment variables, a `.env` file, and optional CLI flags. CLI arguments take precedence over environment variables, which take precedence over `.env`.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URI` | *(required)* | PostgreSQL connection string |
| `ACCESS_MODE` | `restricted` | `restricted` or `unrestricted` |
| `ALLOWED_SCHEMAS` | *(empty = all)* | Comma-separated schema allowlist |
| `MAX_ROWS` | `1000` | Maximum rows returned per query (1–100,000) |
| `MAX_CELL_CHARS` | `500` | Per-cell truncation limit (1–10,000) |
| `QUERY_TIMEOUT_SEC` | `30` | Query timeout in seconds (1–600) |
| `TRANSPORT` | `stdio` | MCP transport: `stdio`, `sse`, `streamable-http` |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `AUDIT_LOG_SQL` | `false` | Include SQL preview in audit logs (debug only) |
| `POOL_MIN_SIZE` | `2` | Minimum connection pool size |
| `POOL_MAX_SIZE` | `10` | Maximum connection pool size |
| `SSE_HOST` | `localhost` | Host for SSE transport |
| `SSE_PORT` | `8000` | Port for SSE transport |
| `STREAMABLE_HTTP_HOST` | `localhost` | Host for streamable-http transport |
| `STREAMABLE_HTTP_PORT` | `8000` | Port for streamable-http transport |

### `DATABASE_URI` format

```
postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=MODE
```

| Query param | Values | Notes |
|-------------|--------|-------|
| `sslmode` | `disable`, `allow`, `prefer`, `require`, `verify-ca`, `verify-full` | See SSL section below |

**Example (production):**

```env
DATABASE_URI=postgresql://mcp_readonly:SECRET@db.example.com:5432/myapp?sslmode=require
```

**Example (dev VM without SSL):**

```env
DATABASE_URI=postgresql://devuser:SECRET@192.168.1.100:5432/myapp?sslmode=prefer
```

### `ACCESS_MODE`

| Mode | Behavior |
|------|----------|
| `restricted` | Read-only SQL only; pglast AST validation; `readOnlyHint=true` on `execute_sql` |
| `unrestricted` | No SQL validation; `destructiveHint=true` on `execute_sql`; **dev only** |

### `ALLOWED_SCHEMAS`

Comma-separated list of schemas the MCP server may access for introspection and user queries.

```env
ALLOWED_SCHEMAS=public,analytics
```

When empty, all user schemas are accessible (subject to database role permissions). System schemas (`information_schema`, `pg_catalog`) are always permitted for introspection queries.

---

## CLI flags

```bash
uv run psql-mcp [DATABASE_URL] [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `DATABASE_URL` | Positional argument; overrides `DATABASE_URI` env var |
| `--access-mode` | `restricted` or `unrestricted` |
| `--transport` | `stdio`, `sse`, or `streamable-http` |
| `--sse-host` | Override `SSE_HOST` |
| `--sse-port` | Override `SSE_PORT` |
| `--streamable-http-host` | Override `STREAMABLE_HTTP_HOST` |
| `--streamable-http-port` | Override `STREAMABLE_HTTP_PORT` |

**Examples:**

```bash
# Default stdio transport (Cursor)
uv run psql-mcp --access-mode=restricted

# Override database URL on CLI
uv run psql-mcp "postgresql://user:pass@localhost:5432/mydb" --access-mode=restricted

# HTTP transport for remote RAG agents
TRANSPORT=streamable-http uv run psql-mcp --access-mode=restricted
```

---

## Configuration precedence

```
CLI argument  >  Shell environment variable  >  .env file
```

**Common pitfall:** If `DATABASE_URI` is set in your PowerShell session, it overrides `.env`. Clear it before testing:

```powershell
Remove-Item Env:DATABASE_URI -ErrorAction SilentlyContinue
```

---

## SSL configuration

| `sslmode` | Behavior | Use case |
|-----------|----------|----------|
| `disable` | Never use SSL | Trusted local dev only |
| `prefer` | Use SSL if available, else plaintext | Dev VMs, Minikube, local networks |
| `require` | Fail if SSL unavailable | Production with SSL-enabled Postgres |
| `verify-full` | Require SSL + verify hostname | High-security production |

**Error:** `server does not support SSL, but SSL was required`  
**Fix:** Change `sslmode=require` to `sslmode=prefer` or enable SSL on the Postgres server.

---

## Cursor MCP configuration

Example [`.cursor/mcp.json`](../.cursor/mcp.json):

```json
{
  "mcpServers": {
    "custom-psql": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\path\\to\\custom-psql-mcp-server",
        "psql-mcp",
        "--access-mode=restricted"
      ],
      "env": {
        "DATABASE_URI": "${env:DATABASE_URI}",
        "ALLOWED_SCHEMAS": "public",
        "ACCESS_MODE": "restricted"
      }
    }
  }
}
```

Set `DATABASE_URI` in your user environment — never commit credentials to the repository.

---

## Transport modes

| Transport | Use case | How to enable |
|-----------|----------|---------------|
| `stdio` | Cursor, Claude Desktop, local agents | Default; no extra config |
| `sse` | HTTP-based MCP clients | `TRANSPORT=sse` |
| `streamable-http` | Remote RAG orchestrators | `TRANSPORT=streamable-http` |

For HTTP transports, configure `STREAMABLE_HTTP_HOST` and `STREAMABLE_HTTP_PORT` (or `SSE_HOST`/`SSE_PORT` for SSE).

---

## Example `.env` file

See [`.env.example`](../.env.example) for a complete template with all variables documented.
