# privacy.py
import hashlib
import os

# ---------- PASSWORD HASHING ----------

def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256.
    In production, use bcrypt or argon2 instead.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password_hash(plain_password: str, stored_hash: str) -> bool:
    """
    Verify a plain password against stored hash.
    """
    return hash_password(plain_password) == stored_hash


# ---------- DATA ANONYMIZATION ----------

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
    # Handle different formats
    digits = ''.join(filter(str.isdigit, contact))
    if len(digits) >= 4:
        last4 = digits[-4:]
        return f"XXX-XXX-{last4}"
    return "XXX-XXX-XXXX"


# ---------- REVERSIBLE ENCRYPTION WITH FERNET ----------

try:
    from cryptography.fernet import Fernet
    FERNET_AVAILABLE = True
except ImportError:
    Fernet = None
    FERNET_AVAILABLE = False

# Global encryption key (In production, store this securely in environment variable!)
_ENCRYPTION_KEY = None


def initialize_encryption_key():
    """
    Initialize or load encryption key.
    In production, load from secure storage or environment variable.
    """
    global _ENCRYPTION_KEY
    
    if not FERNET_AVAILABLE:
        return None
    
    # Try to load existing key from file
    key_file = "encryption.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            _ENCRYPTION_KEY = f.read()
    else:
        # Generate new key and save it
        _ENCRYPTION_KEY = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(_ENCRYPTION_KEY)
    
    return _ENCRYPTION_KEY


def get_encryption_key():
    """Get the global encryption key, initializing if needed."""
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is None:
        initialize_encryption_key()
    return _ENCRYPTION_KEY


def encrypt_value(value: str) -> str:
    """
    Encrypt a string using Fernet.
    """
    if not FERNET_AVAILABLE:
        raise RuntimeError("cryptography package not installed. Install with: pip install cryptography")
    
    key = get_encryption_key()
    if key is None:
        raise RuntimeError("Encryption key not initialized")
    
    f = Fernet(key)
    token = f.encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(token: str) -> str:
    """
    Decrypt a string using Fernet.
    """
    if not FERNET_AVAILABLE:
        raise RuntimeError("cryptography package not installed. Install with: pip install cryptography")
    
    key = get_encryption_key()
    if key is None:
        raise RuntimeError("Encryption key not initialized")
    
    f = Fernet(key)
    try:
        value = f.decrypt(token.encode("utf-8"))
        return value.decode("utf-8")
    except Exception:
        # If decryption fails, return original (might be unencrypted legacy data)
        return token


# ---------- INPUT VALIDATION ----------

import re

def validate_contact(contact: str) -> tuple[bool, str]:
    """
    Validate contact number format.
    Returns (is_valid, error_message)
    """
    if not contact:
        return False, "Contact cannot be empty"
    
    # Remove spaces and dashes
    digits = ''.join(filter(str.isdigit, contact))
    
    if len(digits) < 10:
        return False, "Contact must have at least 10 digits"
    
    if len(digits) > 15:
        return False, "Contact number too long"
    
    return True, ""


def validate_name(name: str) -> tuple[bool, str]:
    """
    Validate name format.
    Returns (is_valid, error_message)
    """
    if not name:
        return False, "Name cannot be empty"
    
    if len(name) < 2:
        return False, "Name must be at least 2 characters"
    
    if len(name) > 100:
        return False, "Name too long (max 100 characters)"
    
    # Check if name contains only letters, spaces, dots, and hyphens
    if not re.match(r"^[a-zA-Z\s.\-']+$", name):
        return False, "Name can only contain letters, spaces, dots, and hyphens"
    
    return True, ""


def validate_diagnosis(diagnosis: str) -> tuple[bool, str]:
    """
    Validate diagnosis field.
    Returns (is_valid, error_message)
    """
    if not diagnosis:
        return False, "Diagnosis cannot be empty"
    
    if len(diagnosis) < 3:
        return False, "Diagnosis too short (min 3 characters)"
    
    if len(diagnosis) > 500:
        return False, "Diagnosis too long (max 500 characters)"
    
    return True, ""