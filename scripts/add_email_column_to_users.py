# This script adds the 'email' column to the 'users' table if it does not exist.
import sqlite3

import os
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'infra.db'))

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if not column_exists(cur, 'users', 'email'):
        cur.execute("ALTER TABLE users ADD COLUMN email TEXT")
        print("Added 'email' column to 'users' table.")
    else:
        print("'email' column already exists.")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
