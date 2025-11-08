"""
Unit tests for encryption utilities.

Tests field-level encryption for PII data.
"""
import pytest
from app.utils.encryption import encrypt_field, decrypt_field, generate_encryption_key


def test_encrypt_decrypt_field():
    """Test basic encryption and decryption."""
    original = "test@example.com"
    encrypted = encrypt_field(original)
    decrypted = decrypt_field(encrypted)

    assert encrypted != original  # Should be encrypted
    assert decrypted == original  # Should decrypt back to original


def test_encrypt_empty_string():
    """Test encryption of empty string."""
    original = ""
    encrypted = encrypt_field(original)
    assert encrypted == original  # Empty strings pass through


def test_encrypt_none():
    """Test encryption of None value."""
    assert encrypt_field(None) is None


def test_decrypt_none():
    """Test decryption of None value."""
    assert decrypt_field(None) is None


def test_generate_encryption_key():
    """Test encryption key generation."""
    key1 = generate_encryption_key()
    key2 = generate_encryption_key()

    assert key1 != key2  # Should generate unique keys
    assert len(key1) > 0  # Should have content
    assert isinstance(key1, str)  # Should be string


def test_decrypt_invalid_data():
    """Test decryption of invalid encrypted data."""
    with pytest.raises(ValueError):
        decrypt_field("invalid-encrypted-data")
