"""
User and UserProfile Pydantic schemas.

Includes registration, profile creation (onboarding), and responses.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from app.schemas import BaseSchema, TimestampMixin


class UserBase(BaseModel):
    """
    Base user fields (no sensitive data like password).
    """
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """
    User creation (includes password).

    Used for admin-created users. Regular users use UserRegister in auth.py.
    """
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(default='learner', pattern="^(learner|admin|super_admin)$")


class UserUpdate(BaseModel):
    """
    User update (all fields optional).

    Learners can only update their own data. Admins can update roles.
    """
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, pattern="^(learner|admin|super_admin)$")
    is_active: Optional[bool] = None


class UserResponse(BaseSchema, TimestampMixin):
    """
    User response (public data).

    Decision #59: PII encrypted in database, decrypted transparently for API response.
    """
    user_id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    is_active: bool
    email_verified: bool
    two_factor_enabled: bool
    must_change_password: bool  # Decision #79: Force password change for bootstrap admin
    last_login_at: Optional[datetime]

    @property
    def full_name(self) -> str:
        """Computed property: full name."""
        return f"{self.first_name} {self.last_name}"


class UserProfileCreate(BaseModel):
    """
    User profile creation (onboarding).

    Decision #10: 7-question onboarding flow.
    """
    course_id: UUID
    
    # Question 1: How did you hear about us?
    referral_source: Optional[str] = Field(None, pattern="^(search|social|colleague|other)$")
    referral_source_detail: Optional[str] = None
    
    # Question 3: Why this certification?
    motivation: Optional[str] = None
    
    # Question 4: Exam date
    exam_date: Optional[date] = None
    
    # Question 5: Current level
    current_level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    
    # Question 6: Target score
    target_score_percentage: Optional[int] = Field(None, ge=70, le=100)
    
    # Question 7: Daily commitment
    daily_commitment_minutes: int = Field(..., ge=15, le=120)
    
    # Acquisition tracking (Decision #66)
    acquisition_channel: Optional[str] = Field(None, pattern="^(google_ads|organic|referral|social)$")
    referral_code: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """
    User profile update (all fields optional).

    Learners can update their study preferences.
    """
    exam_date: Optional[date] = None
    current_level: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced)$")
    target_score_percentage: Optional[int] = Field(None, ge=70, le=100)
    daily_commitment_minutes: Optional[int] = Field(None, ge=15, le=120)


class UserProfileResponse(BaseSchema, TimestampMixin):
    """
    User profile response.
    """
    profile_id: UUID
    user_id: UUID
    course_id: UUID
    referral_source: Optional[str]
    referral_source_detail: Optional[str]
    motivation: Optional[str]
    exam_date: Optional[date]
    days_until_exam: Optional[int]
    current_level: str
    target_score_percentage: Optional[int]
    daily_commitment_minutes: int
    acquisition_cost: Optional[Decimal]
    acquisition_channel: Optional[str]
    referral_code: Optional[str]


class UserWithProfileResponse(UserResponse):
    """
    User response with embedded profile.

    Used for dashboard and detailed user views.
    """
    profile: Optional[UserProfileResponse]
