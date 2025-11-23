-- USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,        -- stores hashed password (SHA-256)
    role        TEXT NOT NULL CHECK (role IN ('admin', 'doctor', 'receptionist'))
);

-- DEFAULT USERS (from assignment)
-- Note: These are plain text for initial setup, will be hashed on first login
INSERT OR IGNORE INTO users (username, password, role) VALUES

('admin',       'admin123',   'admin'),
('tulaib',     'tulaib123',     'doctor'),
('hammad', 'hammad123',     'receptionist');

----------------------------------------------------

-- PATIENTS TABLE
CREATE TABLE IF NOT EXISTS patients (
    patient_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT,
    contact             TEXT,
    diagnosis           TEXT,                -- Can store encrypted diagnosis
    anonymized_name     TEXT,
    anonymized_contact  TEXT,
    date_added          TEXT DEFAULT (datetime('now')),
    
    -- Constraints for data integrity
    CHECK (length(name) >= 2),
    CHECK (length(contact) >= 10)
);

----------------------------------------------------

-- LOGS TABLE
CREATE TABLE IF NOT EXISTS logs (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    role        TEXT,
    action      TEXT NOT NULL,               -- 'login', 'add_patient', 'view', 'anonymize', etc.
    timestamp   TEXT DEFAULT (datetime('now')),
    details     TEXT,                        -- extra info about the action
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

----------------------------------------------------

-- CONSENT LOG TABLE (GDPR Compliance)
CREATE TABLE IF NOT EXISTS consent_log (
    consent_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    consent_type TEXT NOT NULL,              -- 'data_processing', 'cookies', etc.
    timestamp    TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

----------------------------------------------------

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_patients_date ON patients(date_added);
CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_action ON logs(action);
CREATE INDEX IF NOT EXISTS idx_consent_user ON consent_log(user_id);