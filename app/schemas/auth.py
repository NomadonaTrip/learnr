"""
Authentication and authorization Pydantic schemas.

Includes registration, login, JWT tokens, and 2FA (Decision #50).
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from uuid import UUID


class UserRegister(BaseModel):
    """
    User registration request.

    Decision #53: Argon2id password hashing with strong password requirements.
    """
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password meets strength requirements (Decision #53)."""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class UserLogin(BaseModel):
    """
    User login request.
    """
    email: EmailStr
    password: str


class Token(BaseModel):
    """
    JWT token response.

    Decision #53: JWT authentication with HS256 (configurable to RS256 in production).
    """
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """
    JWT token payload data (decoded from token).
    """
    user_id: UUID
    email: str
    role: str
    exp: Optional[int] = None  # Expiration timestamp
    iat: Optional[int] = None  # Issued at timestamp


class RefreshTokenRequest(BaseModel):
    """
    Refresh token request.
    """
    refresh_token: str


class TwoFactorSetup(BaseModel):
    """
    2FA setup response (Decision #50: Two-factor authentication support).

    Returns TOTP secret, QR code URL, and backup codes.
    """
    secret: str
    qr_code_url: str
    backup_codes: List[str]


class TwoFactorVerify(BaseModel):
    """
    2FA verification request (Decision #50).

    User submits 6-digit TOTP code.
    """
    code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")


class TwoFactorDisable(BaseModel):
    """
    Disable 2FA request.

    Requires password confirmation for security.
    """
    password: str


class PasswordChange(BaseModel):
    """
    Password change request.

    Decision #79: Force password change after bootstrap admin first login.
    """
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure new password meets strength requirements."""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class PasswordResetRequest(BaseModel):
    """
    Request password reset email.
    """
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """
    Confirm password reset with token.
    """
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure new password meets strength requirements."""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v
