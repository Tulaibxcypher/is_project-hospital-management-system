# auth.py
from db import get_user_by_username
from privacy import verify_password_hash


def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    Verify password against stored hash.
    Falls back to plain text comparison for legacy users.
    """
    # Check if stored password is a hash (64 chars for SHA-256)
    if len(stored_password) == 64:
        return verify_password_hash(plain_password, stored_password)
    else:
        # Legacy plain text password (for existing users)
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