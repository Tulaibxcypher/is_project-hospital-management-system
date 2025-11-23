import sqlite3

conn = sqlite3.connect('hospital.db')
cursor = conn.cursor()

# Add consent_log table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS consent_log (
        consent_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL,
        consent_type TEXT NOT NULL,
        timestamp    TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
''')

# Create index
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_consent_user ON consent_log(user_id)
''')

conn.commit()
conn.close()

print("✅ consent_log table added successfully!")