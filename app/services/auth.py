"""
Authentication service.

Handles user authentication, JWT tokens, password management.
Decision #53: Argon2id password hashing, JWT authentication.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.models.security import SecurityLog
from app.schemas.auth import TokenData
from app.core.config import settings
from app.utils.security import verify_password, get_password_hash
import uuid


def authenticate_user(db: Session, email: str, password: str, ip_address: Optional[str] = None) -> Optional[User]:
    """
    Authenticate user with email and password.

    Decision #53: Argon2id password verification.

    NOTE: Due to non-deterministic Fernet encryption, we cannot directly query
    by encrypted email. Instead, we query all users and decrypt to find match.
    For production, consider using deterministic encryption or email hash for lookup.

    Args:
        db: Database session
        email: Plaintext user email (NOT encrypted)
        password: Plain text password
        ip_address: Client IP for security logging

    Returns:
        User if authentication successful, None otherwise
    """
    from app.utils.encryption import decrypt_field

    # Query all users and decrypt emails to find match
    # NOTE: This is inefficient but necessary with non-deterministic Fernet encryption
    all_users = db.query(User).all()

    user = None
    for u in all_users:
        try:
            decrypted_email = decrypt_field(u._email)
            if decrypted_email.lower() == email.lower():
                user = u
                break
        except Exception:
            # Skip users with decryption errors
            continue

    if not user:
        # Log failed login attempt
        log_security_event(
            db=db,
            event_type="failed_login",
            success=False,
            failure_reason="User not found",
            ip_address=ip_address
        )
        return None
    
    # Verify password
    if not verify_password(password, user.password_hash):
        # Log failed login attempt
        log_security_event(
            db=db,
            event_type="failed_login",
            success=False,
            user_id=user.user_id,
            failure_reason="Invalid password",
            ip_address=ip_address
        )
        return None
    
    # Check if user is active
    if not user.is_active:
        log_security_event(
            db=db,
            event_type="failed_login",
            success=False,
            user_id=user.user_id,
            failure_reason="Account inactive",
            ip_address=ip_address
        )
        # Raise exception for inactive users (different from wrong credentials)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )
    
    # Log successful login
    log_security_event(
        db=db,
        event_type="login",
        success=True,
        user_id=user.user_id,
        ip_address=ip_address
    )
    
    # Update last login time
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    
    return user


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Decision #53: JWT tokens with configurable expiry.
    
    Args:
        data: Payload data to encode
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token.
    
    Refresh tokens have longer expiry than access tokens.
    
    Args:
        data: Payload data to encode
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode JWT token and return payload as dictionary.

    Simpler version for testing - just decodes without validation.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dictionary

    Raises:
        JWTError: If token is invalid or expired
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return payload


def verify_token(token: str) -> TokenData:
    """
    Verify and decode JWT token.

    Args:
        token: JWT token to verify

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")

        # user_id is required, email is optional for some token types
        if user_id is None:
            raise credentials_exception

        # If email not in token, use a placeholder (for test tokens)
        if email is None:
            email = f"user_{user_id}@test.local"

        token_data = TokenData(
            user_id=uuid.UUID(user_id),
            email=email,
            role=role if role else "learner",
            exp=payload.get("exp"),
            iat=payload.get("iat")
        )
        return token_data

    except (JWTError, ValueError):
        raise credentials_exception


def get_current_user(db: Session, token: str) -> User:
    """
    Get current user from JWT token.
    
    Args:
        db: Database session
        token: JWT access token
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token invalid or user not found
    """
    token_data = verify_token(token)
    
    user = db.query(User).filter(User.user_id == str(token_data.user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


def log_security_event(
    db: Session,
    event_type: str,
    success: bool,
    user_id: Optional[str] = None,
    admin_user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    failure_reason: Optional[str] = None,
    event_metadata: Optional[Dict[str, Any]] = None
) -> SecurityLog:
    """
    Log security event to audit trail.
    
    Decision #41: Immutable security audit log.
    
    Args:
        db: Database session
        event_type: Type of event (login, failed_login, role_changed, etc.)
        success: Whether event was successful
        user_id: User performing/affected by action
        admin_user_id: Admin user (if applicable)
        ip_address: Client IP address
        user_agent: Client user agent
        failure_reason: Reason for failure (if applicable)
        event_metadata: Additional event data
        
    Returns:
        Created SecurityLog entry
    """
    log_entry = SecurityLog(
        user_id=user_id,
        admin_user_id=admin_user_id,
        event_type=event_type,
        event_category='authentication',
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        failure_reason=failure_reason,
        event_metadata=event_metadata
    )
    
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    
    return log_entry


def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
    """
    Change user password.
    
    Decision #79: Force password change for bootstrap admin.
    
    Args:
        db: Database session
        user: User object
        current_password: Current password (for verification)
        new_password: New password
        
    Returns:
        True if successful
        
    Raises:
        HTTPException: If current password is incorrect
    """
    # Verify current password
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash new password
    user.password_hash = get_password_hash(new_password)
    
    # Clear must_change_password flag if set
    if user.must_change_password:
        user.must_change_password = False
    
    db.commit()
    
    # Log password change
    log_security_event(
        db=db,
        event_type="password_changed",
        success=True,
        user_id=str(user.user_id)
    )
    
    return True
