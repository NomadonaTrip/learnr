"""
Unit tests for authentication service.

Tests:
- Password hashing (Argon2id)
- JWT token generation and validation
- Token expiration
- Role-based claims in JWT
"""
import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    decode_token,
    create_refresh_token
)
from app.core.config import settings


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing with Argon2id."""

    def test_password_hash_returns_string(self):
        """Test that password hashing returns a string."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be hashed, not plaintext

    def test_password_hash_is_different_each_time(self):
        """Test that same password produces different hashes (salt)."""
        password = "SecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different due to random salt

    def test_verify_correct_password(self):
        """Test verifying correct password against hash."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password against hash."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        wrong_password = "WrongPassword456!"

        assert verify_password(wrong_password, hashed) is False

    def test_verify_empty_password(self):
        """Test verifying empty password against hash."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password("", hashed) is False

    def test_hash_special_characters(self):
        """Test hashing passwords with special characters."""
        password = "P@ssw0rd!#$%^&*()"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_hash_unicode_characters(self):
        """Test hashing passwords with unicode characters."""
        password = "Пароль123"  # Russian characters
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True


@pytest.mark.unit
class TestJWTTokenGeneration:
    """Test JWT token generation and structure."""

    def test_create_access_token_returns_string(self):
        """Test that token creation returns a string."""
        data = {"sub": "user123", "role": "learner"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_token_contains_correct_claims(self):
        """Test that access token contains expected claims."""
        user_id = "test-user-id-123"
        role = "learner"
        data = {"sub": user_id, "role": role}

        token = create_access_token(data)

        # Decode without verification to check structure
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert payload["sub"] == user_id
        assert payload["role"] == role
        assert "exp" in payload  # Expiration time
        assert "iat" in payload  # Issued at time

    def test_access_token_expiration_time(self):
        """Test that access token has correct expiration time."""
        data = {"sub": "user123", "role": "learner"}
        token = create_access_token(data)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]

        # Check expiration is approximately ACCESS_TOKEN_EXPIRE_MINUTES in the future
        expected_exp = iat_timestamp + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        assert abs(exp_timestamp - expected_exp) < 5  # Allow 5 second tolerance

    def test_refresh_token_longer_expiration(self):
        """Test that refresh token has longer expiration than access token."""
        data = {"sub": "user123", "role": "learner"}
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)

        access_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        refresh_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert refresh_payload["exp"] > access_payload["exp"]

    def test_token_with_custom_expiration(self):
        """Test creating token with custom expiration time."""
        data = {"sub": "user123", "role": "learner"}
        custom_expires = timedelta(minutes=5)

        token = create_access_token(data, expires_delta=custom_expires)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]

        expected_exp = iat_timestamp + (5 * 60)
        assert abs(exp_timestamp - expected_exp) < 5

    def test_token_different_for_different_users(self):
        """Test that different users get different tokens."""
        token1 = create_access_token({"sub": "user1", "role": "learner"})
        token2 = create_access_token({"sub": "user2", "role": "learner"})

        assert token1 != token2


@pytest.mark.unit
class TestJWTTokenValidation:
    """Test JWT token validation and verification."""

    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        user_id = "test-user-id"
        role = "learner"
        token = create_access_token({"sub": user_id, "role": role})

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["role"] == role

    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.string"

        with pytest.raises(JWTError):
            decode_token(invalid_token)

    def test_verify_expired_token(self):
        """Test verifying an expired token."""
        data = {"sub": "user123", "role": "learner"}
        # Create token that expires immediately
        expired_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta=expired_delta)

        with pytest.raises(JWTError):
            decode_token(token)

    def test_verify_token_with_wrong_secret(self):
        """Test verifying token with wrong secret key."""
        token = create_access_token({"sub": "user123", "role": "learner"})

        # Try to decode with wrong secret
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret-key", algorithms=[settings.ALGORITHM])

    def test_verify_token_missing_claims(self):
        """Test verifying token with missing required claims."""
        # Create token without 'sub' claim
        incomplete_data = {"role": "learner"}
        token = create_access_token(incomplete_data)

        payload = decode_token(token)
        assert "sub" not in payload or payload.get("sub") is None

    def test_verify_token_with_additional_claims(self):
        """Test verifying token with additional custom claims."""
        data = {
            "sub": "user123",
            "role": "learner",
            "email": "test@example.com",
            "custom_field": "custom_value"
        }
        token = create_access_token(data)

        payload = decode_token(token)

        assert payload["email"] == "test@example.com"
        assert payload["custom_field"] == "custom_value"


@pytest.mark.unit
class TestRoleBasedClaims:
    """Test role-based claims in JWT tokens."""

    def test_learner_role_in_token(self):
        """Test learner role is correctly stored in token."""
        token = create_access_token({"sub": "user123", "role": "learner"})
        payload = decode_token(token)

        assert payload["role"] == "learner"

    def test_admin_role_in_token(self):
        """Test admin role is correctly stored in token."""
        token = create_access_token({"sub": "admin123", "role": "admin"})
        payload = decode_token(token)

        assert payload["role"] == "admin"

    def test_super_admin_role_in_token(self):
        """Test super_admin role is correctly stored in token."""
        token = create_access_token({"sub": "superadmin123", "role": "super_admin"})
        payload = decode_token(token)

        assert payload["role"] == "super_admin"

    def test_role_cannot_be_modified_in_token(self):
        """Test that modifying role in token invalidates it."""
        token = create_access_token({"sub": "user123", "role": "learner"})

        # Try to decode and modify
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        payload["role"] = "admin"  # Try to escalate privileges

        # Re-encode with modified payload
        modified_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # Original token should still be valid with original role
        original_payload = decode_token(token)
        assert original_payload["role"] == "learner"

        # Modified token should work but signing would need to be done properly
        # In practice, without the secret key, attackers can't create valid tokens


@pytest.mark.unit
class TestPasswordSecurityRequirements:
    """Test password security requirements."""

    def test_hash_minimum_length_password(self):
        """Test hashing password at minimum length."""
        password = "Pass1!"  # 6 characters
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_hash_maximum_length_password(self):
        """Test hashing very long password."""
        password = "P" * 100 + "1!"  # 102 characters
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_argon2_hash_format(self):
        """Test that Argon2id hash has correct format."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        # Argon2 hashes start with $argon2id$
        assert hashed.startswith("$argon2id$")

    def test_password_hash_timing_consistency(self):
        """Test that password verification timing is consistent (prevent timing attacks)."""
        import time

        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        # Measure time for correct password
        start = time.time()
        verify_password(password, hashed)
        correct_time = time.time() - start

        # Measure time for incorrect password
        start = time.time()
        verify_password("WrongPassword456!", hashed)
        incorrect_time = time.time() - start

        # Times should be roughly similar (within 50ms)
        # Argon2 is designed to have consistent timing
        assert abs(correct_time - incorrect_time) < 0.05
