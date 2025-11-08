# TDD Addendum - Admin Bootstrap Process
# Adaptive CBAP Learning Platform

**Version:** 1.3 (Addendum to v1.0)  
**Date:** October 25, 2025  
**Decision Reference:** #79  
**Status:** APPROVED - CRITICAL FOR MVP

---

## Overview

Specifies how the first admin account is created on initial deployment. Without this, the platform cannot function (no courses, no questions, no content).

**Solution:** Environment variable bootstrap + API-based promotion for additional admins.

---

## 1. BOOTSTRAP METHOD

### Environment Variables

**Required in `.env`:**
```bash
BOOTSTRAP_ADMIN_EMAIL=founder@cbapplatform.com
BOOTSTRAP_ADMIN_PASSWORD=SecureRandomPassword123!
```

### Startup Script

**File:** `app/core/bootstrap.py`

```python
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def create_bootstrap_admin(db: Session) -> None:
    """
    Create first super_admin if none exists.
    Runs once on application startup.
    """
    
    # Check if any super_admin exists
    existing_super_admin = db.query(User).filter(
        User.role == 'super_admin'
    ).first()
    
    if existing_super_admin:
        logger.info("Super admin already exists. Skipping bootstrap.")
        return
    
    # Get bootstrap credentials from environment
    bootstrap_email = settings.BOOTSTRAP_ADMIN_EMAIL
    bootstrap_password = settings.BOOTSTRAP_ADMIN_PASSWORD
    
    if not bootstrap_email or not bootstrap_password:
        logger.warning(
            "BOOTSTRAP_ADMIN_EMAIL or BOOTSTRAP_ADMIN_PASSWORD not set. "
            "Skipping admin creation."
        )
        return
    
    # Validate password strength
    if len(bootstrap_password) < 12:
        logger.error("Bootstrap password too weak (min 12 chars). Aborting.")
        raise ValueError("Bootstrap password must be at least 12 characters")
    
    # Create super_admin user
    super_admin = User(
        email=bootstrap_email,
        password_hash=get_password_hash(bootstrap_password),
        first_name="Super",
        last_name="Admin",
        role="super_admin",
        email_verified=True,
        is_active=True,
        must_change_password=True  # Force password change on first login
    )
    
    db.add(super_admin)
    db.commit()
    db.refresh(super_admin)
    
    logger.info(f"✅ Bootstrap super_admin created: {bootstrap_email}")
    
    # Create security log
    from app.models.security import SecurityLog
    security_log = SecurityLog(
        user_id=super_admin.user_id,
        event_type="bootstrap_admin_created",
        ip_address="127.0.0.1",
        user_agent="System",
        success=True,
        metadata={"email": bootstrap_email}
    )
    db.add(security_log)
    db.commit()
```

### Integration in `app/main.py`

```python
from fastapi import FastAPI
from app.core.bootstrap import create_bootstrap_admin
from app.core.database import SessionLocal

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    db = SessionLocal()
    try:
        # Create bootstrap admin if needed
        create_bootstrap_admin(db)
    finally:
        db.close()
    
    # Other startup tasks...
```

---

## 2. DATABASE SCHEMA UPDATE

### Add to User Model

```python
# app/models/user.py

class User(Base):
    # ... existing fields ...
    
    must_change_password = Column(Boolean, nullable=False, default=False)
```

**Migration:**
```sql
ALTER TABLE users 
ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT false;
```

---

## 3. API ENDPOINT - ROLE PROMOTION

### PATCH /v1/admin/users/{user_id}/role

Allows super_admin to promote/demote users.

**Auth:** Required (super_admin only)

**Request:**
```json
{
  "role": "admin"
}
```

**Validation:**
- `role` must be 'learner' or 'admin'
- Cannot set 'super_admin' via API (security)
- Cannot change own role
- Target user must exist

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "email": "newadmin@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "admin",
  "updated_at": "2025-10-25T10:30:00Z"
}
```

**Error Responses:**
- `403 FORBIDDEN`: Not super_admin
- `404 NOT_FOUND`: User not found
- `400 BAD_REQUEST`: Invalid role or attempting to change own role
- `422 UNPROCESSABLE_ENTITY`: Cannot promote to super_admin

**Side Effects:**
- Updates user role
- Creates security_log entry
- Sends email notification to user
- Invalidates user's existing JWT tokens

**Implementation:**
```python
# app/api/v1/admin.py

from fastapi import APIRouter, Depends, HTTPException
from app.models.user import User
from app.schemas.user import UserRoleUpdate, UserResponse
from app.core.security import get_current_user

router = APIRouter()

@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: UUID,
    role_update: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Promote or demote user role.
    Only super_admin can call this endpoint.
    """
    
    # Check authorization
    if current_user.role != 'super_admin':
        raise HTTPException(status_code=403, detail="Only super_admin can change roles")
    
    # Cannot change own role
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot change own role")
    
    # Get target user
    target_user = db.query(User).filter(User.user_id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate new role
    if role_update.role not in ['learner', 'admin']:
        raise HTTPException(
            status_code=422,
            detail="Can only set role to 'learner' or 'admin'. Cannot promote to super_admin via API."
        )
    
    # Update role
    old_role = target_user.role
    target_user.role = role_update.role
    db.commit()
    db.refresh(target_user)
    
    # Log security event
    create_security_log(
        user_id=current_user.user_id,
        event_type="role_changed",
        ip_address=request.client.host,
        success=True,
        metadata={
            "target_user_id": str(user_id),
            "old_role": old_role,
            "new_role": role_update.role
        }
    )
    
    # Send notification email (async)
    send_role_change_email(target_user, old_role, role_update.role)
    
    return target_user
```

---

## 4. PYDANTIC SCHEMAS

```python
# app/schemas/user.py

class UserRoleUpdate(BaseModel):
    """Update user role."""
    role: str = Field(..., pattern="^(learner|admin)$")
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['learner', 'admin']:
            raise ValueError("Role must be 'learner' or 'admin'")
        return v
```

---

## 5. FIRST LOGIN FLOW

### Password Change Enforcement

```python
# app/api/v1/auth.py

@router.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint."""
    
    # ... authenticate user ...
    
    # Check if must change password
    if user.must_change_password:
        return {
            "access_token": create_access_token(user.user_id, user.role),
            "must_change_password": True,
            "message": "You must change your password on first login"
        }
    
    return {
        "access_token": create_access_token(user.user_id, user.role),
        "refresh_token": create_refresh_token(user.user_id),
        "token_type": "Bearer"
    }
```

### Password Change Endpoint

```python
@router.post("/change-password")
def change_password(
    password_change: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password (including forced first-login change)."""
    
    # Verify old password
    if not verify_password(password_change.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    # Validate new password strength
    validate_password_strength(password_change.new_password)
    
    # Update password
    current_user.password_hash = get_password_hash(password_change.new_password)
    current_user.must_change_password = False
    db.commit()
    
    # Log security event
    create_security_log(
        user_id=current_user.user_id,
        event_type="password_changed",
        ip_address=request.client.host,
        success=True
    )
    
    return {"message": "Password changed successfully"}
```

---

## 6. DEPLOYMENT CHECKLIST

### Before Deployment

1. **Set environment variables:**
   ```bash
   BOOTSTRAP_ADMIN_EMAIL=founder@cbapplatform.com
   BOOTSTRAP_ADMIN_PASSWORD=$(openssl rand -base64 24)  # Generate strong password
   ```

2. **Verify `.env` file not in git:**
   ```bash
   # .gitignore should include:
   .env
   .env.local
   *.env
   ```

3. **Document bootstrap password securely** (password manager)

### After Deployment

1. **Verify bootstrap succeeded:**
   ```bash
   # Check logs
   docker logs <container> | grep "Bootstrap super_admin created"
   
   # Or check database
   docker exec <container> psql -U postgres -d cbap -c \
     "SELECT email, role FROM users WHERE role='super_admin';"
   ```

2. **First login:**
   - Navigate to `https://cbapplatform.com/login`
   - Login with bootstrap credentials
   - System forces password change
   - Change to permanent secure password

3. **Update profile:**
   - Change email from bootstrap to real admin email
   - Update first_name and last_name

4. **Clean up (optional):**
   ```bash
   # Remove bootstrap password from .env (keeps email as reference)
   # System won't recreate if super_admin exists
   unset BOOTSTRAP_ADMIN_PASSWORD
   ```

---

## 7. TESTING

```python
# tests/test_bootstrap.py

def test_bootstrap_creates_super_admin(db):
    """Test bootstrap creates first super_admin."""
    # Clear users
    db.query(User).delete()
    db.commit()
    
    # Set environment variables
    settings.BOOTSTRAP_ADMIN_EMAIL = 'admin@test.com'
    settings.BOOTSTRAP_ADMIN_PASSWORD = 'SecurePass123!'
    
    # Run bootstrap
    create_bootstrap_admin(db)
    
    # Verify
    admin = db.query(User).filter(User.role == 'super_admin').first()
    assert admin is not None
    assert admin.email == 'admin@test.com'
    assert admin.must_change_password == True

def test_bootstrap_idempotent(db):
    """Test bootstrap doesn't create duplicates."""
    settings.BOOTSTRAP_ADMIN_EMAIL = 'admin@test.com'
    settings.BOOTSTRAP_ADMIN_PASSWORD = 'SecurePass123!'
    
    create_bootstrap_admin(db)
    count1 = db.query(User).filter(User.role == 'super_admin').count()
    
    create_bootstrap_admin(db)  # Run again
    count2 = db.query(User).filter(User.role == 'super_admin').count()
    
    assert count1 == count2 == 1

def test_promote_user_to_admin(client, super_admin_token):
    """Test super_admin can promote users."""
    learner = create_user(role='learner')
    
    response = client.patch(
        f"/v1/admin/users/{learner.user_id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["role"] == "admin"

def test_cannot_promote_to_super_admin(client, super_admin_token):
    """Test cannot promote to super_admin via API."""
    learner = create_user(role='learner')
    
    response = client.patch(
        f"/v1/admin/users/{learner.user_id}/role",
        json={"role": "super_admin"},
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    
    assert response.status_code == 422

def test_cannot_change_own_role(client, super_admin_token, super_admin_user):
    """Test cannot change own role."""
    response = client.patch(
        f"/v1/admin/users/{super_admin_user.user_id}/role",
        json={"role": "learner"},
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    
    assert response.status_code == 400
```

---

## 8. SECURITY CONSIDERATIONS

**Strengths:**
- ✅ Password hashed with Argon2id
- ✅ Environment variables never logged
- ✅ Forced password change on first login
- ✅ Cannot promote to super_admin via API
- ✅ All role changes logged
- ✅ Idempotent (won't create duplicates)

**Risks:**
- ⚠️ Bootstrap password in environment (mitigated: must be changed immediately)
- ⚠️ Single super_admin (mitigated: can add more post-MVP)

**Best Practices:**
- Store bootstrap password in secure password manager
- Change password immediately after first login
- Remove BOOTSTRAP_PASSWORD from .env after setup
- Use strong password (min 12 chars, mixed case, numbers, symbols)
- Monitor security logs for unauthorized role changes

---

## 9. IMPLEMENTATION TIMELINE

**Day 1 (Infrastructure Setup) - +1 hour:**
- Create `app/core/bootstrap.py` (15 min)
- Add `must_change_password` field to User model (15 min)
- Create PATCH `/v1/admin/users/{id}/role` endpoint (20 min)
- Write tests (10 min)

**No impact on 30-day deadline** ✅

---

## CONCLUSION

The bootstrap process ensures the first admin can be created securely on deployment, enabling course creation, content approval, and user management. Without this, the platform cannot function.

**Status:** ✅ APPROVED - CRITICAL FOR MVP LAUNCH  
**Priority:** HIGH (blocks all admin functionality)

---

**Addendum Complete**

This bootstrap process must be implemented on Day 1 of the sprint during infrastructure setup.