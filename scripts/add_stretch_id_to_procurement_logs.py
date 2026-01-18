
import sqlite3
import os

# Path to your SQLite DB file
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'infra.db')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Check if 'stretch_id' column already exists
c.execute("PRAGMA table_info(procurement_logs);")
columns = [row[1] for row in c.fetchall()]
if 'stretch_id' not in columns:
    try:
        c.execute("ALTER TABLE procurement_logs ADD COLUMN stretch_id INTEGER REFERENCES road_stretches(id);")
        print("Column 'stretch_id' added to procurement_logs table.")
    except Exception as e:
        print("Error while adding column:", e)
else:
    print("Column 'stretch_id' already exists in procurement_logs table.")

conn.commit()
conn.close()
