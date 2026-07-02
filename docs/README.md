# psql-mcp Documentation

Welcome to the **psql-mcp v0.1.0** documentation. This guide covers installation, configuration, tool reference, security, operations, and integration with agentic RAG systems.

## Recommended reading order

1. **[Getting Started](getting-started.md)** — Install, configure, and verify your first connection
2. **[Configuration](configuration.md)** — Environment variables, CLI flags, and transports
3. **[MCP Tools Reference](mcp-tools.md)** — Full API for all 8 tools
4. **[Security](security.md)** — Defense-in-depth model and production checklist
5. **[RAG Integration](rag-integration.md)** — How to use psql-mcp in an agentic RAG pipeline
6. **[Operations](operations.md)** — Docker, CI, logging, and client wiring
7. **[Troubleshooting](troubleshooting.md)** — Common errors and fixes

## Release information

| Resource | Link |
|----------|------|
| Release notes | [RELEASE_NOTES_v0.1.0.md](../RELEASE_NOTES_v0.1.0.md) |
| Changelog | [CHANGELOG.md](../CHANGELOG.md) |
| Source README | [README.md](../README.md) |

## Quick links

- **Test database connection:** `uv run python scripts/test_connection.py`
- **Run security tests:** `uv run python scripts/adversarial_test.py`
- **Harden Postgres:** `sql/setup_mcp_role.sql`
- **Cursor MCP config:** `.cursor/mcp.json`

## Version

Current release: **v0.1.0**
