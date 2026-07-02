# MCP Tools Reference

**psql-mcp v0.1.0** exposes eight MCP tools. All tools return JSON text content blocks. Query tools (`execute_sql`, `sample_rows`) use a standardized response envelope.

## Response formats

### Query tools (`execute_sql`, `sample_rows`)

```json
{
  "columns": ["id", "name", "email"],
  "rows": [[1, "Alice", "alice@example.com"]],
  "row_count": 1,
  "truncated": false,
  "execution_ms": 12
}
```

| Field | Type | Description |
|-------|------|-------------|
| `columns` | `string[]` | Column names from the result set |
| `rows` | `array[]` | Row values as arrays (cell values may be truncated) |
| `row_count` | `integer` | Number of rows returned (after cap) |
| `truncated` | `boolean` | `true` if more rows existed beyond `MAX_ROWS` |
| `execution_ms` | `integer` | Query execution time in milliseconds |

### Introspection tools

Return JSON arrays or objects directly (schema lists, object metadata, relationship graphs).

### Error responses

```json
{
  "error": "Schema 'auth' is not in ALLOWED_SCHEMAS. Allowed: public"
}
```

---

## Recommended agent workflow

For best results in agentic RAG, agents should discover schema before querying:

```
list_schemas
  → list_objects (schema)
    → get_object_details (table)
      → get_table_relationships (schema)  [optional, for JOINs]
        → execute_sql (validated SELECT)
```

Use `search_objects` when the agent knows a table name but not its schema. Use `sample_rows` for quick data previews without writing SQL.

---

## Tool reference

### `list_schemas`

List all schemas in the database, filtered by `ALLOWED_SCHEMAS` when configured.

| Property | Value |
|----------|-------|
| `readOnlyHint` | `true` |
| Parameters | None |

**Example agent prompt:** *"What schemas are available in the database?"*

**Sample response:**

```json
[
  {
    "schema_name": "public",
    "schema_owner": "postgres",
    "schema_type": "User Schema"
  }
]
```

---

### `list_objects`

List objects of a given type within a schema.

| Property | Value |
|----------|-------|
| `readOnlyHint` | `true` |

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `schema_name` | `string` | required | Schema to inspect |
| `object_type` | `string` | `"table"` | One of: `table`, `view`, `sequence`, `extension` |

**Example agent prompt:** *"List all tables in the public schema."*

**Sample response:**

```json
[
  { "schema": "public", "name": "users", "type": "BASE TABLE" },
  { "schema": "public", "name": "orders", "type": "BASE TABLE" }
]
```

---

### `get_object_details`

Return columns, constraints, and indexes for a database object.

| Property | Value |
|----------|-------|
| `readOnlyHint` | `true` |

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `schema_name` | `string` | required | Schema name |
| `object_name` | `string` | required | Object name |
| `object_type` | `string` | `"table"` | One of: `table`, `view`, `sequence`, `extension` |

**Example agent prompt:** *"Show me the columns and indexes on public.users."*

**Sample response (table):**

```json
{
  "basic": { "schema": "public", "name": "users", "type": "table" },
  "columns": [
    { "column": "id", "data_type": "integer", "is_nullable": "NO", "default": "nextval(...)" },
    { "column": "email", "data_type": "text", "is_nullable": "NO", "default": null }
  ],
  "constraints": [
    { "name": "users_pkey", "type": "PRIMARY KEY", "columns": ["id"] }
  ],
  "indexes": [
    { "name": "users_pkey", "definition": "CREATE UNIQUE INDEX ..." }
  ]
}
```

---

### `get_table_relationships`

Return foreign-key relationships for all tables in a schema. Helps agents write correct JOINs.

| Property | Value |
|----------|-------|
| `readOnlyHint` | `true` |

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `schema_name` | `string` | required | Schema to inspect |

**Example agent prompt:** *"What foreign keys exist in the public schema?"*

**Sample response:**

```json
[
  {
    "source_schema": "public",
    "source_table": "orders",
    "source_column": "user_id",
    "target_schema": "public",
    "target_table": "users",
    "target_column": "id",
    "constraint_name": "orders_user_id_fkey"
  }
]
```

---

### `search_objects`

Search for tables and views by name pattern across schemas.

| Property | Value |
|----------|-------|
| `readOnlyHint` | `true` |

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pattern` | `string` | required | Case-insensitive substring to match against object names |
| `object_types` | `string[]` | `["table", "view"]` | Types to include |

Results are capped at 100 objects and filtered by `ALLOWED_SCHEMAS`.

**Example agent prompt:** *"Find all tables with 'user' in the name."*

---

### `sample_rows`

Return a small preview of rows from a table without the agent writing SQL.

| Property | Value |
|----------|-------|
| `readOnlyHint` | `true` |

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `schema_name` | `string` | required | Schema name |
| `table_name` | `string` | required | Table name |
| `limit` | `integer` | `10` | Max rows (1–100, further capped by `MAX_ROWS`) |

**Example agent prompt:** *"Show me 5 sample rows from public.users."*

Returns the standard query response envelope (see above).

---

### `execute_sql`

Execute a SQL query. In **restricted** mode (default), only validated read-only statements are permitted.

| Property | Value |
|----------|-------|
| `readOnlyHint` | `true` (restricted) / `false` (unrestricted) |
| `destructiveHint` | `true` (unrestricted only) |

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sql` | `string` | required | SQL query to execute |

**Allowed in restricted mode:** `SELECT`, `EXPLAIN`, `SHOW`, `VACUUM`/`ANALYZE` (read-only forms).

**Blocked in restricted mode:** `INSERT`, `UPDATE`, `DELETE`, DDL, transactions, `EXPLAIN ANALYZE`, locking clauses.

**Example agent prompt:** *"How many active users are in the users table?"*

```sql
SELECT COUNT(*) AS total FROM public.users WHERE active = true
```

Returns the standard query response envelope.

---

### `explain_query`

Return the execution plan for a SQL query using `EXPLAIN (FORMAT JSON)`. Does not run `EXPLAIN ANALYZE`.

| Property | Value |
|----------|-------|
| `readOnlyHint` | `true` |

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sql` | `string` | required | SQL query to explain |

**Example agent prompt:** *"Explain the query plan for selecting all users ordered by created_at."*

Returns PostgreSQL's JSON explain plan.

---

## Tool annotations summary

| Tool | readOnlyHint | destructiveHint |
|------|:---:|:---:|
| `list_schemas` | yes | — |
| `list_objects` | yes | — |
| `get_object_details` | yes | — |
| `get_table_relationships` | yes | — |
| `search_objects` | yes | — |
| `sample_rows` | yes | — |
| `explain_query` | yes | — |
| `execute_sql` (restricted) | yes | — |
| `execute_sql` (unrestricted) | — | yes |
