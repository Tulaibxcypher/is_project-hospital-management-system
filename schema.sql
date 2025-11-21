-- USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,        -- later we will store hashed password here
    role        TEXT NOT NULL CHECK (role IN ('admin', 'doctor', 'receptionist'))
);

-- DEFAULT USERS (from assignment)
INSERT OR IGNORE INTO users (username, password, role) VALUES
('admin',       'admin123',   'admin'),
('Dr. Bob',     'doc123',     'doctor'),
('Alice_recep', 'rec123',     'receptionist');

----------------------------------------------------

-- PATIENTS TABLE
CREATE TABLE IF NOT EXISTS patients (
    patient_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT,
    contact             TEXT,
    diagnosis           TEXT,
    anonymized_name     TEXT,
    anonymized_contact  TEXT,
    date_added          TEXT DEFAULT (datetime('now'))
);

----------------------------------------------------

-- LOGS TABLE
CREATE TABLE IF NOT EXISTS logs (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    role        TEXT,
    action      TEXT,                        -- 'login', 'add_patient', 'view', 'anonymize', etc.
    timestamp   TEXT DEFAULT (datetime('now')),
    details     TEXT,                        -- extra info about the action
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

