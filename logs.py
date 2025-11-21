# logs.py
from db import add_log


def log_action(user: dict | None, action: str, details: str = ""):
    """
    Wrapper to log user actions easily.

    user: dict from DB or None
    action: 'login', 'add_patient', 'anonymize', 'view', 'export', etc.
    """
    if user is None:
        user_id = None
        role = None
    else:
        user_id = user.get("user_id")
        role = user.get("role")

    add_log(user_id=user_id, role=role, action=action, details=details)
