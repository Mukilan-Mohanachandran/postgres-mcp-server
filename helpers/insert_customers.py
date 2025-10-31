import psycopg2
import json

# Database connection configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "postgres"
}

# Create table query
CREATE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(50),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Insert query
INSERT_QUERY = """
INSERT INTO customers (first_name, last_name, email, phone, address, city, state, postal_code)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (email) DO NOTHING;
"""

def main():
    # Connect to PostgreSQL
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Create table if not exists
    cur.execute(CREATE_TABLE_QUERY)
    conn.commit()

    # Read customer data from JSON file
    with open("customers.json", "r") as f:
        customers = json.load(f)

    # Insert each customer record
    for customer in customers:
        cur.execute(INSERT_QUERY, (
            customer["first_name"],
            customer["last_name"],
            customer["email"],
            customer["phone"],
            customer["address"],
            customer["city"],
            customer["state"],
            customer["postal_code"]
        ))

    conn.commit()
    print("✅ Customer data inserted successfully!")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
