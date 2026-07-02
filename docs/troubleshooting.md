# Troubleshooting

Common issues when running **psql-mcp v0.1.0** and how to resolve them.

---

## Connection issues

### `server does not support SSL, but SSL was required`

**Cause:** `DATABASE_URI` uses `sslmode=require` but the Postgres server has no SSL configured.

**Fix:** Change to `sslmode=prefer` for dev environments, or enable SSL on the Postgres server for production.

```env
# Before (fails on non-SSL servers)
DATABASE_URI=postgresql://user:pass@host:5432/db?sslmode=require

# After (dev)
DATABASE_URI=postgresql://user:pass@host:5432/db?sslmode=prefer
```

See [configuration.md](configuration.md#ssl-configuration) for full SSL guidance.

---

### `couldn't get a connection after 30.00 sec`

**Cause:** TCP connection to the Postgres host timed out. The server may be healthy inside a VM/cluster but unreachable from your machine.

**Diagnosis:**

```powershell
# Windows
Test-NetConnection -ComputerName YOUR_HOST -Port 5432

# Or use the built-in test script
uv run python scripts/test_connection.py
```

If step `[1/3] TCP check` fails, the issue is network — not credentials.

**Fixes:**

| Scenario | Solution |
|----------|----------|
| Kubernetes | `kubectl port-forward svc/postgres 5432:5432` |
| Minikube VM IP | Use `minikube service` or host port-forward |
| Cloud RDS/VM | Open security group / firewall for your IP |
| VPN required | Connect to corporate VPN first |

---

### `Connection attempt failed` with correct credentials

**Cause:** Usually `pg_hba.conf` rejects your client IP, or the user lacks `CONNECT` privilege on the database.

**Fix:**

1. Check Postgres logs for `FATAL: no pg_hba.conf entry`
2. Add your client IP to `pg_hba.conf` or use SSL + cert auth
3. Grant connect: `GRANT CONNECT ON DATABASE mydb TO myuser;`

---

## Configuration issues

### `.env` values ignored — wrong database connected

**Cause:** A `DATABASE_URI` environment variable in your shell session overrides `.env`.

**Diagnosis:** `test_connection.py` shows a different host than your `.env` file.

**Fix (PowerShell):**

```powershell
Remove-Item Env:DATABASE_URI -ErrorAction SilentlyContinue
Remove-Item Env:TEST_DATABASE_URI -ErrorAction SilentlyContinue
uv run python scripts/test_connection.py
```

**Precedence reminder:** CLI argument > shell env var > `.env` file.

---

### `Schema 'auth' is not in ALLOWED_SCHEMAS`

**Cause:** `ALLOWED_SCHEMAS` is set but the agent or query references a schema not in the list.

**Fix:**

```env
# Add the schema
ALLOWED_SCHEMAS=public,auth,analytics
```

Or restrict the agent to only query allowlisted schemas.

---

## MCP server issues

### Server starts but shows no tools in terminal

**Expected behavior.** MCP servers communicate via JSON-RPC over stdio — they do not print a tool menu.

**To list tools:**

```bash
npx @modelcontextprotocol/inspector uv run psql-mcp --access-mode=restricted
```

Or see [mcp-tools.md](mcp-tools.md) for the static reference.

---

### `Starting psql-mcp in RESTRICTED mode` but `Could not connect to database`

The server starts even if the database is unreachable (MCP clients can still connect; DB operations will fail at tool call time).

**Fix:** Resolve the connection issue first using `scripts/test_connection.py`, then restart the server.

---

### Pool worker warnings on Windows

```
WARNING couldn't stop task 'pool-1-worker-0' within 5.0 seconds
```

**Cause:** Connection pool shutdown timing on Windows during a failed connection attempt.

**Fix:** Usually harmless. Resolve the underlying connection failure. The server includes `WindowsSelectorEventLoopPolicy` for psycopg3 compatibility — ensure you are on v0.1.0+.

---

## SQL and query issues

### `Only SELECT, ANALYZE, VACUUM, EXPLAIN, SHOW ... are allowed`

**Cause:** Query blocked by pglast AST validation in restricted mode.

**Fix:** Rewrite as a `SELECT` statement. For writes, use a migration tool — not the MCP server.

---

### `Query references schema(s) not in ALLOWED_SCHEMAS`

**Cause:** SQL explicitly references a schema outside the allowlist (e.g. `SELECT * FROM auth.secrets`).

**Fix:** Add the schema to `ALLOWED_SCHEMAS` or rewrite the query to use an allowlisted schema.

---

### `Query execution timed out after 30 seconds`

**Cause:** Query exceeded `QUERY_TIMEOUT_SEC`.

**Fix:**

1. Simplify the query (add filters, reduce joins)
2. Increase timeout: `QUERY_TIMEOUT_SEC=60` (not recommended for production)
3. Add indexes on the database for slow queries

---

### Results truncated unexpectedly

**Cause:** Result exceeded `MAX_ROWS` or a cell exceeded `MAX_CELL_CHARS`.

**Fix:** Adjust caps if appropriate for your use case:

```env
MAX_ROWS=5000
MAX_CELL_CHARS=1000
```

For RAG agents, smaller caps are usually better to protect context windows.

---

## Windows-specific notes

| Issue | Solution |
|-------|----------|
| psycopg3 + asyncio errors | Built-in fix in `psql_mcp/__init__.py`; use `uv run psql-mcp` |
| pytest integration tests fail | `tests/conftest.py` sets `WindowsSelectorEventLoopPolicy` |
| PowerShell env override | `Remove-Item Env:DATABASE_URI` before testing |

---

## Getting help

1. Run `uv run python scripts/test_connection.py` and note which step fails
2. Check server logs with `LOG_LEVEL=DEBUG`
3. Enable SQL audit: `AUDIT_LOG_SQL=true`
4. See [security.md](security.md) for production checklist
5. Open an issue with the obfuscated connection target and error message (never share passwords)
