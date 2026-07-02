# Getting Started

This guide walks you through installing, configuring, and verifying **psql-mcp v0.1.0**.

## Prerequisites

Before you begin, ensure you have:

| Requirement | Notes |
|-------------|-------|
| **Python 3.12+** | Check with `python --version` |
| **[uv](https://docs.astral.sh/uv/)** | Python package manager used by this project |
| **PostgreSQL 12+** | A reachable database instance |
| **Network access** | Your machine must reach the Postgres host on the configured port (default 5432) |

> **Tip:** If Postgres runs inside Kubernetes or a VM (e.g. `192.168.x.x`), you may need port-forwarding or VPN access before the MCP server can connect. See [troubleshooting.md](troubleshooting.md).

---

## Step 1: Install

```bash
cd custom-psql-mcp-server
uv sync
```

This creates a virtual environment and installs all dependencies including `mcp`, `psycopg`, and `pglast`.

---

## Step 2: Configure

Copy the example environment file and edit it with your database credentials:

```bash
cp .env.example .env
```

Minimum required setting:

```env
DATABASE_URI=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=prefer
ALLOWED_SCHEMAS=public
ACCESS_MODE=restricted
```

### SSL mode guidance

| `sslmode` | When to use |
|-----------|-------------|
| `require` | Production servers with SSL enabled |
| `prefer` | Tries SSL first, falls back if unavailable (good for dev VMs) |
| `disable` | Trusted local networks only — never use in production |

See [configuration.md](configuration.md) for all options.

---

## Step 3: Verify database connection

Before starting the MCP server, confirm your connection string works:

**Linux / macOS:**

```bash
uv run python scripts/test_connection.py
```

**Windows (PowerShell):**

```powershell
# Clear any shell override so .env is used
Remove-Item Env:DATABASE_URI -ErrorAction SilentlyContinue
uv run python scripts/test_connection.py
```

Expected output on success:

```
[1/3] TCP check HOST:5432 ...
  OK — port is open
[2/3] Postgres auth (SELECT 1) ...
  OK — connected in 20 ms
[3/3] Query check ...
  database: yourdb
  user:     youruser

Connection string is valid.
```

If step 1 fails, the issue is network reachability — not credentials. See [troubleshooting.md](troubleshooting.md).

---

## Step 4: Run the MCP server

```bash
uv run psql-mcp --access-mode=restricted
```

Expected log lines:

```
INFO Starting psql-mcp in RESTRICTED mode
INFO Connected to database: postgresql://****:****@host:5432/dbname
```

The server now listens on **stdio** for MCP client connections. It will not print a tool menu in the terminal — that is normal MCP behavior.

---

## Step 5: Verify MCP tools

### Option A: MCP Inspector (recommended)

```bash
npx @modelcontextprotocol/inspector uv run psql-mcp --access-mode=restricted
```

This opens a web UI where you can browse all tools, inspect schemas, and invoke queries interactively.

### Option B: Cursor IDE

1. Copy or reference [`.cursor/mcp.json`](../.cursor/mcp.json) in your Cursor MCP settings.
2. Set `DATABASE_URI` in your user environment (do not commit credentials).
3. Open **Cursor Settings → MCP** and confirm `custom-psql` shows as connected.
4. Ask the agent: *"List schemas in my database using the Postgres MCP tools."*

### Option C: Static tool list

See [mcp-tools.md](mcp-tools.md) for the complete reference of all 8 tools.

---

## Step 6: Harden for production (optional)

For production deployments, create a dedicated read-only database role:

```bash
psql -h HOST -U admin -d DATABASE -f sql/setup_mcp_role.sql
```

Then update `DATABASE_URI` to use the `mcp_readonly` role and run the adversarial test:

```bash
ALLOWED_SCHEMAS=public uv run python scripts/adversarial_test.py
```

See [security.md](security.md) for the full production checklist.

---

## Next steps

- [Configuration reference](configuration.md) — all environment variables and CLI flags
- [MCP tools reference](mcp-tools.md) — parameters, responses, and agent workflow
- [RAG integration](rag-integration.md) — connect to your agentic RAG pipeline
