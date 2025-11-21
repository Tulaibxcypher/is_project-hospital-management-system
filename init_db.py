import sqlite3

DB_NAME = "hospital.db"
SCHEMA_FILE = "schema.sql"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()
    conn.executescript(sql_script)
    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized with tables from '{SCHEMA_FILE}'.")

if __name__ == "__main__":
    init_db()
