# psql-mcp

**v0.1.0** — Production-grade PostgreSQL MCP server for agentic RAG workflows.

Exposes schema discovery and safe, read-only SQL execution to MCP clients (Cursor, custom RAG orchestrators) without embedding vector retrieval inside MCP.

[Release Notes](RELEASE_NOTES_v0.1.0.md) · [Changelog](CHANGELOG.md) · [Documentation](docs/README.md)

---

## Features

- **8 MCP tools** for schema discovery, relationships, safe SQL, and query planning
- **Restricted mode by default** — pglast AST validation, read-only transactions, schema allowlist
- **Bounded JSON responses** — row/cell caps protect RAG context windows
- **Transports:** stdio (Cursor), SSE, streamable-http (remote agents)
- **Structured audit logging** for every tool invocation

---

## Quick start

```bash
uv sync
cp .env.example .env   # set DATABASE_URI
uv run python scripts/test_connection.py
uv run psql-mcp --access-mode=restricted
```

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Install, configure, verify connection |
| [Configuration](docs/configuration.md) | Environment variables, CLI, SSL, transports |
| [MCP Tools Reference](docs/mcp-tools.md) | Full API for all 8 tools |
| [Security](docs/security.md) | Defense-in-depth model and production checklist |
| [RAG Integration](docs/rag-integration.md) | Agentic RAG architecture and workflows |
| [Operations](docs/operations.md) | Docker, CI, logging, client wiring |
| [Troubleshooting](docs/troubleshooting.md) | Common errors and fixes |

---

## MCP tools

| Tool | Description |
|------|-------------|
| `list_schemas` | Enumerate database schemas |
| `list_objects` | Tables, views, sequences, extensions |
| `get_object_details` | Columns, constraints, indexes |
| `get_table_relationships` | Foreign-key graph for JOINs |
| `search_objects` | Fuzzy name search |
| `sample_rows` | Preview rows from a table |
| `execute_sql` | Validated SQL (read-only in restricted mode) |
| `explain_query` | `EXPLAIN (FORMAT JSON)` |

See [docs/mcp-tools.md](docs/mcp-tools.md) for parameters and response schemas.

---

## Cursor MCP config

See [`.cursor/mcp.json`](.cursor/mcp.json). Set `DATABASE_URI` in your environment.

---

## Development

```bash
uv sync --dev
uv run ruff check src tests
uv run pytest tests/unit -v
docker compose up postgres -d
uv run pytest tests/integration -m integration -v
```

---

## License

MIT
