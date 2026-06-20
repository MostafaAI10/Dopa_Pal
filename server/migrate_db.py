import sqlite3
import os

db_path = 'dopapal_dev.db'

if not os.path.exists(db_path):
    print("Database not found at", db_path)
else:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN language VARCHAR(10) DEFAULT 'ar'")
        print("Column language added successfully.")
    except sqlite3.OperationalError as e:
        print("Error or already exists:", e)
    
    conn.commit()
    conn.close()
