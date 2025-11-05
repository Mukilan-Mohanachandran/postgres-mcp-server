async def list_tables(conn):
    """Lists all tables in the public schema of the PostgreSQL database.
    Returns a list of table names"""
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cur.fetchall()
    cur.close()
    return [table[0] for table in tables]