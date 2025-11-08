"""
Field-level encryption utilities for PII (Personally Identifiable Information).
Uses Fernet (AES-128-CBC) for symmetric encryption.

Decision #59: All PII fields (email, names) are encrypted at rest.
"""
from cryptography.fernet import Fernet
from app.core.config import settings
from typing import Optional


# Initialize Fernet cipher with key from environment
_cipher = Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_field(value: str) -> str:
    """
    Encrypt a string field (e.g., email, name).

    Args:
        value: Plaintext string to encrypt

    Returns:
        Encrypted string (base64 encoded)
    """
    if not value:
        return value

    encrypted = _cipher.encrypt(value.encode())
    return encrypted.decode()


def decrypt_field(value: Optional[str]) -> str:
    """
    Decrypt a string field.

    Args:
        value: Encrypted string (base64 encoded)

    Returns:
        Decrypted plaintext string
    """
    if not value:
        return value

    try:
        decrypted = _cipher.decrypt(value.encode())
        return decrypted.decode()
    except Exception as e:
        # Log error but don't expose encryption details
        raise ValueError("Failed to decrypt field") from e


def generate_encryption_key() -> str:
    """
    Generate a new encryption key for ENCRYPTION_KEY environment variable.

    Returns:
        Base64-encoded Fernet key

    Usage:
        python -c "from app.utils.encryption import generate_encryption_key; print(generate_encryption_key())"
    """
    key = Fernet.generate_key()
    return key.decode()
