import json
import psycopg2
from psycopg2.extras import RealDictCursor

def extract_postgres_metadata(conn_str: str):
    """
    Extracts table metadata (purpose, columns, and comments) from PostgreSQL.
    Returns a JSON-like Python dict ready for LLM ingestion.
    """

    query = """
    SELECT
        n.nspname AS schema_name,
        c.relname AS table_name,
        obj_description(c.oid) AS table_comment
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'r'
      AND n.nspname NOT IN ('pg_catalog', 'information_schema');
    """

    column_query = """
    SELECT
        table_schema,
        table_name,
        column_name,
        data_type,
        col_description((table_schema || '.' || table_name)::regclass::oid, ordinal_position) AS column_comment
    FROM information_schema.columns
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY table_name, ordinal_position;
    """

    with psycopg2.connect(conn_str) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Fetch table-level metadata
        cur.execute(query)
        tables = cur.fetchall()

        # Fetch column-level metadata
        cur.execute(column_query)
        columns = cur.fetchall()

    # Organize columns by table
    column_map = {}
    for col in columns:
        key = (col['table_schema'], col['table_name'])
        column_map.setdefault(key, []).append({
            "name": col['column_name'],
            "type": col['data_type'],
            "description": col['column_comment']
        })

    # Merge into structured JSON
    metadata = []
    for t in tables:
        key = (t['schema_name'], t['table_name'])
        metadata.append({
            "schema": t['schema_name'],
            "table": t['table_name'],
            "purpose": t['table_comment'] or "No description available",
            "columns": column_map.get(key, [])
        })

    return metadata


# Example usage
if __name__ == "__main__":
    CONNECTION_STRING = "dbname=postgres user=postgres password=postgres host=localhost port=5432"
    meta = extract_postgres_metadata(CONNECTION_STRING)
    print(json.dumps(meta, indent=2))
