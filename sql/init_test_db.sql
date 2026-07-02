-- Seed schema for integration tests and local development
CREATE TABLE IF NOT EXISTS public.users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO public.users (name, email) VALUES
    ('Alice', 'alice@example.com'),
    ('Bob', 'bob@example.com')
ON CONFLICT DO NOTHING;

CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.secrets (
    id SERIAL PRIMARY KEY,
    secret TEXT NOT NULL
);

INSERT INTO auth.secrets (secret) VALUES ('should-not-be-visible')
ON CONFLICT DO NOTHING;

-- Read-only MCP role for adversarial testing
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcp_readonly') THEN
        CREATE ROLE mcp_readonly LOGIN PASSWORD 'mcp_readonly';
    END IF;
END
$$;

ALTER ROLE mcp_readonly SET statement_timeout = '5s';
GRANT CONNECT ON DATABASE psql_mcp_test TO mcp_readonly;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
