-- Production hardening script for the MCP read-only database role.
-- Replace placeholders before running as a superuser.

-- 1. Create dedicated role (not superuser)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcp_readonly') THEN
        CREATE ROLE mcp_readonly LOGIN PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
    END IF;
END
$$;

-- 2. Session safeguards
ALTER ROLE mcp_readonly SET statement_timeout = '30s';
ALTER ROLE mcp_readonly SET lock_timeout = '10s';
ALTER ROLE mcp_readonly CONNECTION LIMIT 5;

-- 3. Schema allow-list (example: public only — adjust for your environment)
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO mcp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mcp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO mcp_readonly;

-- Optional: additional application schemas
-- GRANT USAGE ON SCHEMA analytics TO mcp_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO mcp_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO mcp_readonly;

-- 4. Revoke access to sensitive system areas (adjust if introspection needs more)
REVOKE ALL ON SCHEMA pg_catalog FROM mcp_readonly;
GRANT USAGE ON SCHEMA pg_catalog TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA pg_catalog TO mcp_readonly;

-- 5. Optional audit table (append-only)
CREATE TABLE IF NOT EXISTS public.mcp_audit_log (
    id BIGSERIAL PRIMARY KEY,
    logged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    tool_name TEXT,
    success BOOLEAN NOT NULL,
    duration_ms INTEGER,
    row_count INTEGER,
    error_message TEXT
);

REVOKE INSERT, UPDATE, DELETE ON public.mcp_audit_log FROM mcp_readonly;

-- Connection string example:
-- postgresql://mcp_readonly:CHANGE_ME_STRONG_PASSWORD@localhost:5432/yourdb?sslmode=require
