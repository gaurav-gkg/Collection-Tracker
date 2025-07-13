import sqlite3
import os

def init_database():
    DB_NAME = 'collection.db'
    
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Removed existing {DB_NAME}")
    
    conn = sqlite3.connect(DB_NAME)
    print(f"Created new database: {DB_NAME}")
    
    with open('schema.sql', 'r') as f:
        schema = f.read()
    
    conn.executescript(schema)
    conn.commit()
    print("Database schema created successfully!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Created tables: {[table[0] for table in tables]}")
    
    conn.close()
    print("Database initialization complete!")

if __name__ == '__main__':
    init_database() 