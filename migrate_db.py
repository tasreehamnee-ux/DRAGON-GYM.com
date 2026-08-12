import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gym.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE settings ADD COLUMN license_expiry_date VARCHAR DEFAULT ''")
except sqlite3.OperationalError:
    pass # column might exist

try:
    cursor.execute("ALTER TABLE settings ADD COLUMN is_locally_locked BOOLEAN DEFAULT 0")
except sqlite3.OperationalError:
    pass # column might exist

conn.commit()
conn.close()
print("Migration done.")
