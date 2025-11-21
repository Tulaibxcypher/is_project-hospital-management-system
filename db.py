# db.py
import sqlite3
from contextlib import contextmanager

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


# ---------- PATIENTS ----------

def add_patient(name: str, contact: str, diagnosis: str):
    """
    Insert a new patient. Anonymized fields are empty initially.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO patients (name, contact, diagnosis)
            VALUES (?, ?, ?)
            """,
            (name, contact, diagnosis)
        )


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
