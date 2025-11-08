"""
Onboarding API endpoints.

Handles user profile creation (7-question onboarding).
Decision #10: Comprehensive onboarding flow.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.user import User
from app.models.course import Course
from app.schemas.user import (
    UserProfileCreate, UserProfileResponse, UserWithProfileResponse
)
from app.schemas.course import CourseResponse
from app.services.user import create_user_profile, get_user_with_profile
from app.api.dependencies import get_current_active_user
from typing import List


router = APIRouter()


@router.get("/courses", response_model=List[CourseResponse])
def get_available_courses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available courses for onboarding.

    Only shows active courses (status='active').
    Decision #65: Draft courses hidden from learners.
    """
    courses = db.query(Course).filter(
        Course.status == 'active',
        Course.is_active == True
    ).all()

    return courses


@router.post("/profile", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
def complete_onboarding(
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Complete onboarding by creating user profile.
    
    Decision #10: 7-question onboarding flow.
    
    Questions:
    1. How did you hear about us? (referral_source)
    2. [Skipped in form - acquired during signup]
    3. Why this certification? (motivation)
    4. Exam date? (exam_date)
    5. Current level? (current_level)
    6. Target score? (target_score_percentage)
    7. Daily commitment? (daily_commitment_minutes)
    
    This creates:
    - UserProfile record
    - UserCompetency records for all KAs in selected course
    """
    profile = create_user_profile(
        db=db,
        user_id=current_user.user_id,
        profile_data=profile_data
    )
    
    return profile


@router.get("/me", response_model=UserWithProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user with profile.
    
    Returns user data + profile data combined.
    Useful after onboarding to verify completion.
    """
    user = get_user_with_profile(db=db, user_id=current_user.user_id)
    return user
