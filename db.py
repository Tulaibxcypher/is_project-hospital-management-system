# db.py
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

DB_NAME = "hospital.db"


@contextmanager
def get_connection():
    """
    Opens a SQLite connection and closes it automatically.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # so we can access columns by name
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ---------- USERS ----------

def get_user_by_username(username: str):
    """
    Return user dict by username, or None.
    """
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def update_user_password(username: str, new_password_hash: str):
    """
    Update user password (used for migrating to hashed passwords).
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (new_password_hash, username)
        )


# ---------- PATIENTS ----------

def add_patient(name: str, contact: str, diagnosis: str, encrypted: bool = False):
    """
    Insert a new patient. Anonymized fields are empty initially.
    If encrypted=True, diagnosis is already encrypted.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO patients (name, contact, diagnosis)
            VALUES (?, ?, ?)
            """,
            (name, contact, diagnosis)
        )
        return cur.lastrowid


def update_patient(patient_id: int, name: str, contact: str, diagnosis: str):
    """
    Update existing patient basic fields.
    """
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE patients
            SET name = ?, contact = ?, diagnosis = ?
            WHERE patient_id = ?
            """,
            (name, contact, diagnosis, patient_id)
        )


def delete_patient(patient_id: int):
    """
    Delete a patient record (GDPR right to erasure).
    """
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM patients WHERE patient_id = ?",
            (patient_id,)
        )


def set_patient_anonymized(
    patient_id: int,
    anonymized_name: str,
    anonymized_contact: str
):
    """
    Update anonymized fields for one patient.
    """
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE patients
            SET anonymized_name = ?, anonymized_contact = ?
            WHERE patient_id = ?
            """,
            (anonymized_name, anonymized_contact, patient_id)
        )


def get_all_patients():
    """
    Return list of all patients as dicts.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT patient_id, name, contact, diagnosis,
                   anonymized_name, anonymized_contact,
                   date_added
            FROM patients
            ORDER BY patient_id DESC
            """
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_patient_by_id(patient_id: int):
    """
    Get single patient by ID.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT patient_id, name, contact, diagnosis,
                   anonymized_name, anonymized_contact,
                   date_added
            FROM patients
            WHERE patient_id = ?
            """,
            (patient_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def search_patients(search_term: str):
    """
    Search patients by name or diagnosis (admin only).
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT patient_id, name, contact, diagnosis,
                   anonymized_name, anonymized_contact,
                   date_added
            FROM patients
            WHERE name LIKE ? OR diagnosis LIKE ?
            ORDER BY patient_id DESC
            """,
            (f"%{search_term}%", f"%{search_term}%")
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# ---------- GDPR COMPLIANCE ----------

def delete_old_records(days: int = 90):
    """
    Delete patient records older than specified days (GDPR data retention).
    Returns number of deleted records.
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM patients WHERE date_added < ?",
            (cutoff_str,)
        )
        return cur.rowcount


def get_patient_count_by_age():
    """
    Get count of records by age (for data retention monitoring).
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN date_added > datetime('now', '-30 days') THEN 1 ELSE 0 END) as last_30_days,
                SUM(CASE WHEN date_added > datetime('now', '-60 days') THEN 1 ELSE 0 END) as last_60_days,
                SUM(CASE WHEN date_added > datetime('now', '-90 days') THEN 1 ELSE 0 END) as last_90_days
            FROM patients
            """
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_patients_for_deletion(days: int = 90):
    """
    Get list of patients that will be deleted based on retention policy.
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT patient_id, anonymized_name, date_added
            FROM patients
            WHERE date_added < ?
            ORDER BY date_added ASC
            """,
            (cutoff_str,)
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# ---------- LOGS ----------

def add_log(user_id: int | None, role: str | None,
            action: str, details: str = ""):
    """
    Insert a log record.
    user_id/role can be None for failed login, etc.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO logs (user_id, role, action, details)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, role, action, details)
        )


def get_logs(limit: int | None = None):
    """
    Return list of logs (newest first).
    """
    with get_connection() as conn:
        sql = """
            SELECT log_id, user_id, role, action, timestamp, details
            FROM logs
            ORDER BY log_id DESC
        """
        if limit:
            sql += " LIMIT ?"
            cur = conn.execute(sql, (limit,))
        else:
            cur = conn.execute(sql)

        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_logs_by_action(action: str, limit: int = 100):
    """
    Get logs filtered by action type.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT log_id, user_id, role, action, timestamp, details
            FROM logs
            WHERE action = ?
            ORDER BY log_id DESC
            LIMIT ?
            """,
            (action, limit)
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# ---------- CONSENT TRACKING (GDPR) ----------

def add_consent_record(user_id: int, consent_type: str):
    """
    Track user consent for GDPR compliance.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO consent_log (user_id, consent_type)
            VALUES (?, ?)
            """,
            (user_id, consent_type)
        )


def get_user_consent(user_id: int):
    """
    Check if user has given consent.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT * FROM consent_log
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None