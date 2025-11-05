import psycopg

from dotenv import load_dotenv
import os

load_dotenv()


DB_CONNECT_STRING = (
    f"host={os.getenv('DB_HOST')} "
    f"port={os.getenv('DB_PORT', 5432)} "
    f"dbname={os.getenv('DB_NAME')} "
    f"user={os.getenv('DB_USER')} "
    f"password={os.getenv('DB_PASS')}"
)

def init_connection():
    conn = psycopg.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
        
    )
    conn.autocommit = True
    return conn