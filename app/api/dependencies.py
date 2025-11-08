"""
FastAPI dependencies for authentication and authorization.

Decision #53: JWT-based authentication with role-based access control.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.user import User
from app.services.auth import get_current_user as get_user_from_token


# HTTP Bearer token security scheme (auto_error=False to return None instead of 403)
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.

    Usage: user: User = Depends(get_current_user)

    Raises 401 if no credentials provided or invalid token.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    return get_user_from_token(db, token)


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (additional check beyond authentication).
    
    Usage: user: User = Depends(get_current_active_user)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: str):
    """
    Dependency factory for role-based access control.
    
    Usage: user: User = Depends(require_role("admin"))
    
    Roles hierarchy:
    - learner: Basic user
    - admin: Can manage courses, content
    - super_admin: Full system access
    """
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        role_hierarchy = {
            'learner': 0,
            'admin': 1,
            'super_admin': 2
        }
        
        user_level = role_hierarchy.get(current_user.role, -1)
        required_level = role_hierarchy.get(required_role, 99)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return current_user
    
    return role_checker


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    
    Handles proxied requests (X-Forwarded-For header).
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> Optional[str]:
    """
    Get user agent from request headers.
    """
    return request.headers.get("User-Agent")
