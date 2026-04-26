import sqlite3
import os

def init_database():
    db_path = './database/cammina.db'
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    with open('database/schema_sqlite.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("Database initialized at " + db_path)

if __name__ == '__main__':
    init_database()
