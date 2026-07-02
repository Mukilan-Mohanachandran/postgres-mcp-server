# Security Guide

**psql-mcp v0.1.0** uses a defense-in-depth security model. No single layer is sufficient on its own — combine application controls, database role hardening, and infrastructure controls for production deployments.

## Security architecture

```mermaid
flowchart TB
    subgraph layer1 [Layer1_Application]
        AST[pglast AST allowlist]
        RO[ReadOnly transactions]
        SchemaFilter[ALLOWED_SCHEMAS]
        Timeout[Query timeout]
    end
    subgraph layer2 [Layer2_Database]
        Role[mcp_readonly role]
        Grants[Schema grants]
        StmtTimeout[statement_timeout]
    end
    subgraph layer3 [Layer3_Infrastructure]
        Network[Private network]
        SSL[TLS when available]
        Audit[Structured audit logs]
    end
    Agent[MCP Client] --> layer1 --> layer2 --> layer3
```

---

## Layer 1: Application controls

These are enforced by the MCP server before any SQL reaches PostgreSQL.

| Control | Implementation | Config |
|---------|----------------|--------|
| SQL allowlist | pglast AST validation in `SafeSqlDriver` | Automatic in `restricted` mode |
| Read-only transactions | `BEGIN TRANSACTION READ ONLY` on every query | Automatic in `restricted` mode |
| Schema allowlist | Rejects queries referencing non-allowed schemas | `ALLOWED_SCHEMAS` |
| Query timeout | asyncio timeout + optional DB `statement_timeout` | `QUERY_TIMEOUT_SEC` |
| Response caps | Row and cell truncation | `MAX_ROWS`, `MAX_CELL_CHARS` |
| Credential hygiene | Passwords stripped from logs and errors | Automatic |
| Function allowlist | Hundreds of read-only functions permitted | `safe_sql.py` |
| Blocked statements | DDL, DML, transactions, `EXPLAIN ANALYZE`, locking | `safe_sql.py` |

### Access modes

| Mode | Default | Production use |
|------|---------|----------------|
| `restricted` | Yes | **Required** for production |
| `unrestricted` | No | Local development only — logs a startup warning |

Never run `unrestricted` mode against production databases.

---

## Layer 2: Database controls

Run [`sql/setup_mcp_role.sql`](../sql/setup_mcp_role.sql) as a PostgreSQL superuser to create a dedicated read-only role.

The script:

1. Creates `mcp_readonly` role (not superuser)
2. Sets `statement_timeout = 30s` and `CONNECTION LIMIT 5`
3. Grants `SELECT` only on allowed schemas
4. Revokes dangerous default privileges
5. Optionally creates an `mcp_audit_log` table

**After running the script**, update `DATABASE_URI` to use the `mcp_readonly` credentials:

```env
DATABASE_URI=postgresql://mcp_readonly:PASSWORD@host:5432/db?sslmode=require
```

---

## Layer 3: Infrastructure controls

| Control | Recommendation |
|---------|----------------|
| Network | Run MCP inside VPC; database not publicly exposed |
| SSL/TLS | Use `sslmode=require` in production |
| Credentials | Separate prod and dev MCP instances with different DB roles |
| Secrets | Store `DATABASE_URI` in a secret manager, not in git |
| Audit | Enable `AUDIT_LOG_SQL=true` only for debugging; use stdout JSON logs in production |
| Firewall | Allow only MCP server IP to reach Postgres port 5432 |

---

## Adversarial acceptance test

Before going to production, run the adversarial test script as the `mcp_readonly` role:

```bash
DATABASE_URI=postgresql://mcp_readonly:PASS@host:5432/db \
ALLOWED_SCHEMAS=public \
uv run python scripts/adversarial_test.py
```

All three tests must **fail** (blocked) and be logged:

| Test | Expected result |
|------|-----------------|
| `DROP TABLE users` | Blocked by AST validation |
| `SELECT * FROM auth.secrets` | Blocked by schema allowlist |
| `SELECT pg_sleep(60)` | Killed by query timeout |

---

## Production go-live checklist

- [ ] `ACCESS_MODE=restricted` on all production instances
- [ ] Dedicated `mcp_readonly` database role (not application or admin user)
- [ ] `ALLOWED_SCHEMAS` set to minimum required schemas
- [ ] `sslmode=require` (or `verify-full`) in `DATABASE_URI`
- [ ] `statement_timeout` set on the database role
- [ ] `CONNECTION LIMIT` set on the database role
- [ ] Adversarial test passes (all destructive queries blocked)
- [ ] `DATABASE_URI` stored in secret manager, not committed to git
- [ ] MCP server runs in private network (not public internet)
- [ ] Separate MCP instances for prod (read-only) and dev (if write needed)
- [ ] Audit logging reviewed and log aggregation configured
- [ ] `AUDIT_LOG_SQL=false` in production (enable only for debugging)

---

## Known risks and mitigations

| Risk | Mitigation |
|------|------------|
| Prompt injection → destructive SQL | pglast AST gate + read-only DB role |
| Unqualified table access via `search_path` | Set explicit `search_path` on DB role; use `ALLOWED_SCHEMAS` |
| Unsafe stored procedures (PL/Python) | Revoke `EXECUTE` on untrusted functions |
| Context overflow from large results | `MAX_ROWS` and `MAX_CELL_CHARS` caps |
| Connection exhaustion | Pool limits + `CONNECTION LIMIT` on DB role |

---

## Non-goals

psql-mcp is intentionally **not**:

- A vector search or embedding store (use pgvector in your RAG pipeline separately)
- A database migration tool (use Flyway, Alembic, or similar)
- A replacement for application-level authorization (use RLS for multi-tenant isolation)
- A write path for production agents (use migrations for schema changes)

See [rag-integration.md](rag-integration.md) for how MCP fits alongside your RAG system.
