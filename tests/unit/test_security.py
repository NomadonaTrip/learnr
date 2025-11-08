"""
Unit tests for security utilities.

Tests password hashing and JWT token management.
"""
import pytest
from datetime import timedelta
from app.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)


def test_password_hashing():
    """Test password hashing with Argon2id."""
    password = "SecurePassword123!"
    hashed = get_password_hash(password)

    assert hashed != password  # Should be hashed
    assert hashed.startswith("$argon2")  # Should use Argon2


def test_verify_correct_password():
    """Test password verification with correct password."""
    password = "SecurePassword123!"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True


def test_verify_incorrect_password():
    """Test password verification with incorrect password."""
    password = "SecurePassword123!"
    wrong_password = "WrongPassword456!"
    hashed = get_password_hash(password)

    assert verify_password(wrong_password, hashed) is False


def test_create_access_token():
    """Test JWT access token creation."""
    data = {"sub": "user-123", "role": "learner"}
    token = create_access_token(data)

    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["role"] == "learner"
    assert "exp" in decoded
    assert "iat" in decoded


def test_create_refresh_token():
    """Test JWT refresh token creation."""
    data = {"sub": "user-123"}
    token = create_refresh_token(data)

    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["type"] == "refresh"
    assert "exp" in decoded


def test_create_token_custom_expiry():
    """Test token creation with custom expiration."""
    data = {"sub": "user-123"}
    expires_delta = timedelta(minutes=5)
    token = create_access_token(data, expires_delta)

    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"


def test_decode_invalid_token():
    """Test decoding invalid token."""
    with pytest.raises(ValueError):
        decode_token("invalid-token-string")


def test_hash_different_passwords():
    """Test that same password produces different hashes."""
    password = "SecurePassword123!"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Should be different due to salt
    assert hash1 != hash2
    # But both should verify
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)
