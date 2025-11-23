# init_db.py
import sqlite3
from privacy import hash_password

DB_NAME = "hospital.db"
SCHEMA_FILE = "schema.sql"

def init_db():
    """Initialize database and migrate passwords to hashed format"""
    conn = sqlite3.connect(DB_NAME)
    
    # Execute schema
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()
    conn.executescript(sql_script)
    conn.commit()
    
    print(f"✅ Database '{DB_NAME}' initialized with tables from '{SCHEMA_FILE}'.")
    
    # Migrate plain text passwords to hashed (if not already hashed)
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, password FROM users")
    users = cur.fetchall()
    
    for user_id, username, password in users:
        # Check if password is already hashed (SHA-256 = 64 chars)
        if len(password) != 64:
            hashed = hash_password(password)
            cur.execute(
                "UPDATE users SET password = ? WHERE user_id = ?",
                (hashed, user_id)
            )
            print(f"🔒 Migrated password for user: {username}")
    
    conn.commit()
    conn.close()
    print("✅ Password migration complete!")

if __name__ == "__main__":
    init_db()