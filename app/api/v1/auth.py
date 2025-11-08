"""
Authentication API endpoints.

Handles user registration, login, JWT tokens, password management.
Decision #53: JWT authentication with Argon2id password hashing.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.user import User
from app.schemas.auth import (
    UserRegister, UserLogin, Token, PasswordChange,
    PasswordResetRequest, PasswordResetConfirm, RefreshTokenRequest
)
from app.schemas.user import UserResponse
from app.services.auth import (
    authenticate_user, create_access_token, create_refresh_token,
    verify_token, change_password
)
from app.utils.security import get_password_hash
from app.api.dependencies import (
    get_current_active_user, get_client_ip, get_user_agent
)
from app.core.config import settings


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Decision #53: Argon2id password hashing.
    Decision #59: Field-level PII encryption.
    
    Steps:
    1. Check if email already exists
    2. Hash password with Argon2id
    3. Encrypt PII fields (email, names)
    4. Create user account
    5. Return user data (without password)
    """
    # Check if user already exists (need to check all users and decrypt)
    from app.utils.encryption import decrypt_field
    existing_user = None
    for u in db.query(User).all():
        try:
            if decrypt_field(u._email).lower() == user_data.email.lower():
                existing_user = u
                break
        except Exception:
            continue

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = get_password_hash(user_data.password)
    
    # Create user (encryption happens automatically via hybrid properties)
    new_user = User(
        email=user_data.email,
        password_hash=password_hash,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role='learner',
        is_active=True,
        email_verified=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log security event
    from app.services.auth import log_security_event
    log_security_event(
        db=db,
        event_type="user_registered",
        success=True,
        user_id=str(new_user.user_id),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return new_user


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.

    Decision #53: JWT access tokens with refresh tokens.

    Steps:
    1. Authenticate user with email/password
    2. Generate access token (1 hour expiry)
    3. Generate refresh token (7 days expiry)
    4. Return both tokens
    """
    # Authenticate user (pass plaintext email - encryption handled internally)
    user = authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password,
        ip_address=get_client_ip(request)
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user must change password (Decision #79: Bootstrap admin)
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required. Please change your password before continuing.",
            headers={"X-Password-Change-Required": "true"}
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.user_id),
            "email": user.email,
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.user_id),
            "email": user.email,
            "role": user.role
        }
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    Allows users to get new access token without re-authenticating.
    """
    try:
        # Verify refresh token
        token_data = verify_token(request.refresh_token)

        # Get user (convert UUID to string for comparison with VARCHAR field)
        user = db.query(User).filter(User.user_id == str(token_data.user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={
                "sub": str(user.user_id),
                "email": user.email,
                "role": user.role
            },
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=new_access_token,
            refresh_token=request.refresh_token,  # Reuse same refresh token
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information from JWT token.
    
    Useful for frontend to verify token and get user data.
    """
    return current_user


@router.post("/change-password")
def change_user_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password.
    
    Decision #79: Force password change for bootstrap admin.
    
    Requires current password for security.
    """
    success = change_password(
        db=db,
        user=current_user,
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )
    
    if success:
        return {"message": "Password changed successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to change password"
        )


@router.post("/logout")
def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout user (client-side token deletion).
    
    Note: JWT tokens are stateless, so logout is primarily client-side.
    Server can implement token blacklist for enhanced security (future enhancement).
    """
    return {"message": "Logged out successfully"}
