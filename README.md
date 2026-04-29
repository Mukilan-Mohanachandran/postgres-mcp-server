# Postgres MCP Server - User Guide

This repository provides a FastMCP server that connects to a PostgreSQL database and exposes tools for database introspection.

## What This Server Provides

The MCP server name is `psql-server` and currently exposes:

- `list_tables`: returns all table names in the `public` schema
- `extract_postgres_metadata`: returns structured metadata for all non-system schemas, including:
  - schema name
  - table name
  - table comment (purpose)
  - columns (name, type, comment)

## Prerequisites

- Python `3.12+`
- A running PostgreSQL instance
- Database credentials with read access to catalog metadata
- Recommended: [`uv`](https://docs.astral.sh/uv/) for environment and dependency management

## Project Setup

From the repository root:

```powershell
uv sync
```

If you do not use `uv`, install dependencies from `pyproject.toml` using your preferred environment manager.

## Environment Variables

The server reads PostgreSQL credentials from environment variables (via `.env` support):

- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASS`

Create a local environment file from `example.env.local` (or set variables directly in your MCP client config):

```env
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="postgres"
DB_USER="postgres"
DB_PASS="postgres"
```

## Running the Server

### Development mode

```powershell
uv run fastmcp dev main.py
```

### Standard execution

```powershell
uv run python main.py
```

## MCP Client Configuration Example

Use the following pattern in your MCP-enabled client config (example shown for a local Python environment):

```json
{
  "mcpServers": {
    "psql-server": {
      "command": "C:\\path\\to\\postgres-mcp-server\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\path\\to\\postgres-mcp-server\\main.py"
      ],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "postgres",
        "DB_USER": "postgres",
        "DB_PASS": "postgres"
      },
      "cwd": "C:\\path\\to\\postgres-mcp-server"
    }
  }
}
```

Replace all `C:\\path\\to\\...` values with absolute paths on your machine.

## Verifying It Works

After connecting your MCP client:

1. Call `list_tables` to confirm connectivity.
2. Call `extract_postgres_metadata` to confirm metadata extraction.

If both calls return expected data, your setup is complete.

## Troubleshooting

- **Connection refused / timeout**: verify PostgreSQL is running and host/port are correct.
- **Authentication failed**: verify `DB_USER` and `DB_PASS`.
- **No tables returned**: check whether your data is in `public`; `list_tables` currently targets only `public`.
- **Missing comments in metadata**: this is expected when table/column comments are not defined in PostgreSQL.