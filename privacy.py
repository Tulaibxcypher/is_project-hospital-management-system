# privacy.py
import hashlib


def anonymize_name(original_name: str | None) -> str | None:
    """
    Creates fake name like ANON_ABC123 using SHA-256 hash of the real name.
    """
    if not original_name:
        return None
    digest = hashlib.sha256(original_name.encode("utf-8")).hexdigest()[:6]
    return f"ANON_{digest.upper()}"


def mask_contact(contact: str | None) -> str | None:
    """
    Mask contact like XXX-XXX-1234 (keeps only last 4 digits).
    """
    if not contact:
        return None
    last4 = contact[-4:]
    return f"XXX-XXX-{last4}"


# ---------- OPTIONAL BONUS: reversible encryption with Fernet ----------

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None  # cryptography may not be installed


def generate_key() -> bytes:
    """
    Generate a new Fernet key (bonus feature - not required for basic working).
    """
    if not Fernet:
        raise RuntimeError("cryptography package not installed.")
    return Fernet.generate_key()


def encrypt_value(value: str, key: bytes) -> str:
    """
    Encrypt a string using Fernet (bonus).
    """
    if not Fernet:
        raise RuntimeError("cryptography package not installed.")
    f = Fernet(key)
    token = f.encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(token: str, key: bytes) -> str:
    """
    Decrypt a string using Fernet (bonus).
    """
    if not Fernet:
        raise RuntimeError("cryptography package not installed.")
    f = Fernet(key)
    value = f.decrypt(token.encode("utf-8"))
    return value.decode("utf-8")
