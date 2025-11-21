# auth.py
from db import get_user_by_username


def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    For this assignment we keep it simple: plain-text comparison.
    (In real systems you would store a hash instead.)
    """
    return plain_password == stored_password


def authenticate(username: str, password: str):
    """
    Returns user dict if credentials are valid, otherwise None.
    """
    user = get_user_by_username(username)
    if not user:
        return None

    if not verify_password(password, user["password"]):
        return None

    return user
