# psql-mcp v0.1.0 Release Notes

**Release date:** July 2, 2026  
**Version:** 0.1.0  
**License:** MIT

---

## Overview

**psql-mcp** is a production-grade PostgreSQL [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server built for **agentic RAG** workflows. It gives AI agents safe, read-only access to live database schema and query results while keeping vector retrieval and embedding orchestration in your RAG pipeline.

This is the inaugural release. It ships a complete tool surface, defense-in-depth security, Docker deployment, and operational documentation.

---

## Highlights

- **8 MCP tools** for schema discovery, relationship mapping, safe SQL execution, and query planning
- **Restricted mode by default** — pglast AST validation, read-only transactions, schema allowlist, and query timeouts
- **Bounded responses** — row and cell caps prevent context window blow-up in RAG prompts
- **Transport-flexible** — stdio for Cursor, streamable-http for remote RAG orchestrators
- **Observable** — structured JSON audit logs for every tool invocation
- **Production-ready ops** — Docker, CI, DB hardening script, and adversarial security tests

---

## Requirements

| Component | Version |
|-----------|---------|
| Python | 3.12+ |
| PostgreSQL | 12+ (16 recommended) |
| Package manager | [uv](https://docs.astral.sh/uv/) |

---

## Quick install

```bash
git clone <your-repo-url> custom-psql-mcp-server
cd custom-psql-mcp-server
uv sync
cp .env.example .env
# Edit DATABASE_URI and ALLOWED_SCHEMAS in .env
uv run psql-mcp --access-mode=restricted
```

On success you should see:

```
INFO Starting psql-mcp in RESTRICTED mode
INFO Connected to database: postgresql://****:****@host:5432/dbname
```

---

## MCP tools

| Tool | Description |
|------|-------------|
| `list_schemas` | Enumerate database schemas |
| `list_objects` | List tables, views, sequences, or extensions in a schema |
| `get_object_details` | Columns, constraints, and indexes for an object |
| `get_table_relationships` | Foreign-key graph for JOIN planning |
| `search_objects` | Fuzzy name search across schemas |
| `sample_rows` | Preview rows from a table (`SELECT * LIMIT n`) |
| `execute_sql` | Run validated SQL (read-only in restricted mode) |
| `explain_query` | `EXPLAIN (FORMAT JSON)` — no ANALYZE |

See [docs/mcp-tools.md](docs/mcp-tools.md) for full parameter and response reference.

---

## Security posture

- **Default:** `ACCESS_MODE=restricted` — all SQL validated before execution
- **Schema allowlist:** `ALLOWED_SCHEMAS=public` limits introspection and query scope
- **Database role:** run `sql/setup_mcp_role.sql` to create a dedicated `mcp_readonly` user
- **Pre-production:** run `scripts/adversarial_test.py` and confirm all destructive queries fail

See [docs/security.md](docs/security.md) for the full hardening guide.

---

## Breaking changes

None — this is the initial release.

---

## Upgrade path

Not applicable for v0.1.0. Future releases will document migration steps in [CHANGELOG.md](CHANGELOG.md).

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/getting-started.md](docs/getting-started.md) | Install, configure, verify |
| [docs/configuration.md](docs/configuration.md) | Environment variables and CLI |
| [docs/mcp-tools.md](docs/mcp-tools.md) | Tool API reference |
| [docs/security.md](docs/security.md) | Security model and checklist |
| [docs/operations.md](docs/operations.md) | Docker, CI, logging |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues and fixes |
| [docs/rag-integration.md](docs/rag-integration.md) | Agentic RAG integration guide |

---

## Contributors

Initial implementation — custom-psql-mcp-server project.

---

## Feedback

Open an issue or pull request in the project repository.
