import os
import psycopg
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
import os

load_dotenv()

# 1. Initialize your FastMCP server
# This name will be shown to the AI client.
mcp = FastMCP("PostgreSQL DB Server")

# 2. Get database connection string from environment variables
# This is a secure way to handle credentials.
DB_CONNECT_STRING = (
    f"host={os.getenv('DB_HOST')} "
    f"port={os.getenv('DB_PORT', 5432)} "
    f"dbname={os.getenv('DB_NAME')} "
    f"user={os.getenv('DB_USER')} "
    f"password={os.getenv('DB_PASS')}"
)


@mcp.tool
async def list_tables():
    """Lists all tables in the public schema of the PostgreSQL database.
    Returns a list of table names"""
    conn = psycopg.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cur.fetchall()
    cur.close()
    conn.close()
    return [table[0] for table in tables]

# 3. Define your first tool
@mcp.tool
async def get_all_products() -> List[Dict[str, Any]]:
    """
    Fetches a list of all products from the 'products' table.
    Returns a list of dictionaries, where each dictionary is a product.
    """
    print("AI is calling 'get_all_products'...")
    try:
        # Connect to the database asynchronously
        async with await psycopg.AsyncConnection.connect(DB_CONNECT_STRING) as aconn:
            async with aconn.cursor(row_factory=psycopg.rows.dict_row) as acur:
                
                # Execute a SAFE, hard-coded query
                await acur.execute("SELECT id, name, price, stock FROM products;")
                
                # Fetch all results
                results = await acur.fetchall()
                print(f"Found {len(results)} products.")
                return results

    except Exception as e:
        print(f"Error in get_all_products: {e}")
        # It's good practice to inform the AI an error occurred
        return [{"error": str(e)}]

# 4. Define a second tool that takes arguments
@mcp.tool
async def get_customer_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Finds a single customer by their email address.
    Takes one argument: 'email' (string)
    Returns a single customer dictionary or null if not found.
    """
    print(f"AI is calling 'get_customer_by_email' with email: {email}")
    try:
        async with await psycopg.AsyncConnection.connect(DB_CONNECT_STRING) as aconn:
            async with aconn.cursor(row_factory=psycopg.rows.dict_row) as acur:
                
                # IMPORTANT: Use parameterized queries to prevent SQL injection.
                # The '%s' is a placeholder, and psycopg safely inserts the 'email' variable.
                # NEVER use f-strings to build a query with user/AI input.
                query = "SELECT id, first_name, last_name, email FROM customers WHERE email = %s;"
                
                await acur.execute(query, (email,))
                
                # Fetch one result
                result = await acur.fetchone()
                
                if result:
                    print(f"Found customer: {result['first_name']}")
                    return result
                else:
                    print("Customer not found.")
                    return None

    except Exception as e:
        print(f"Error in get_customer_by_email: {e}")
        return {"error": str(e)}

# New tool: returns table description (columns, types, defaults, comments)
@mcp.tool
async def table_info(table_name: str) -> Dict[str, Any]:
    """
    Returns detailed description of a table in the public schema:
    - table: table name
    - table_comment: table comment (if any)
    - columns: list of { column_name, data_type, is_nullable, column_default, column_comment }
    """
    print(f"AI is calling 'table_info' for table: {table_name}")
    try:
        async with await psycopg.AsyncConnection.connect(DB_CONNECT_STRING) as aconn:
            async with aconn.cursor(row_factory=psycopg.rows.dict_row) as acur:
                await acur.execute("""
                    SELECT
                      cols.column_name,
                      cols.data_type,
                      cols.is_nullable,
                      cols.column_default,
                      pgd.description AS column_comment
                    FROM information_schema.columns cols
                    LEFT JOIN pg_catalog.pg_namespace ns ON ns.nspname = cols.table_schema
                    LEFT JOIN pg_catalog.pg_class cls ON cls.relname = cols.table_name AND cls.relnamespace = ns.oid
                    LEFT JOIN pg_catalog.pg_description pgd ON pgd.objoid = cls.oid AND pgd.objsubid = cols.ordinal_position
                    WHERE cols.table_schema = 'public' AND cols.table_name = %s
                    ORDER BY cols.ordinal_position;
                """, (table_name,))
                columns = await acur.fetchall()

                # fetch table comment
                await acur.execute("""
                    SELECT obj_description(cls.oid) AS table_comment
                    FROM pg_catalog.pg_class cls
                    JOIN pg_catalog.pg_namespace ns ON ns.oid = cls.relnamespace
                    WHERE ns.nspname = 'public' AND cls.relname = %s;
                """, (table_name,))
                tbl = await acur.fetchone()
                table_comment = tbl.get("table_comment") if tbl else None

                if not columns:
                    return {"error": "table_not_found", "message": f"Table '{table_name}' does not exist in schema 'public'."}

                cols_list = []
                for row in columns:
                    cols_list.append({
                        "column_name": row.get("column_name"),
                        "data_type": row.get("data_type"),
                        "is_nullable": row.get("is_nullable"),
                        "column_default": row.get("column_default"),
                        "column_comment": row.get("column_comment"),
                    })

                return {"table": table_name, "table_comment": table_comment, "columns": cols_list}

    except Exception as e:
        print(f"Error in table_info: {e}")
        return {"error": str(e)}

# 5. This part allows the script to be run directly
if __name__ == "__main__":
    print("Starting FastMCP server for PostgreSQL...")
    print(f"To connect, use the server: {mcp.name}")
    print("Available tools:")
    print(" - get_all_products()")
    print(" - get_customer_by_email(email: str)")
    
    # This command starts the server
    mcp.run()