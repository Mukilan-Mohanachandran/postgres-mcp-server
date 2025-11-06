import os
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List


from util.connection_handler import init_connection
from tools.lists_tables import list_tables as _list_tables
from tools.extract_postgres_metadata import extract_postgres_metadata as _extract_postgres_metadata


mcp = FastMCP("psql-server")


@mcp.tool
async def list_tables():
    """Lists all tables in the public schema of the PostgreSQL database.
    Returns a list of table names"""
    conn = init_connection()
    result = await _list_tables(conn)
    conn.close()
    return result

@mcp.tool
async def extract_postgres_metadata():
    """
    Extracts table metadata (purpose, columns, and comments) from PostgreSQL.
    Returns a JSON-like Python dict ready for LLM ingestion.
    """
    conn = init_connection()    
    result = _extract_postgres_metadata(conn)
    # result = _extract_postgres_metadata("dbname=postgres user=postgres password=postgres host=localhost port=5432")
    conn.close()
    return result



# 5. This part allows the script to be run directly
if __name__ == "__main__":
    print("Starting FastMCP server for PostgreSQL...")
    print(f"To connect, use the server: {mcp.name}")
    print("Available tools:")
    print(" - get_all_products()")
    
    # This command starts the server
    mcp.run()