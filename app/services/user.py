"""
User service.

Handles user profile creation, updates, and onboarding.
Decision #10: 7-question onboarding flow.
"""
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserProfile
from app.models.course import Course
from app.models.learning import UserCompetency
from app.schemas.user import UserProfileCreate, UserProfileUpdate
import uuid


def create_user_profile(
    db: Session,
    user_id: uuid.UUID,
    profile_data: UserProfileCreate
) -> UserProfile:
    """
    Create user profile during onboarding.
    
    Decision #10: 7-question onboarding flow.
    
    Steps:
    1. Verify user exists
    2. Check if profile already exists
    3. Verify course exists
    4. Calculate days until exam
    5. Create profile
    6. Initialize competency tracking for all KAs
    
    Args:
        db: Database session
        user_id: User ID
        profile_data: Profile creation data
        
    Returns:
        Created UserProfile
    """
    # Verify user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if profile already exists
    existing_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile already exists"
        )
    
    # Verify course exists
    course = db.query(Course).filter(Course.course_id == str(profile_data.course_id)).first()
    if not course or course.status != 'active':
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or not active"
        )
    
    # Calculate days until exam
    days_until_exam = None
    if profile_data.exam_date:
        days_until_exam = (profile_data.exam_date - date.today()).days
        if days_until_exam < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam date cannot be in the past"
            )
    
    # Create profile
    profile = UserProfile(
        user_id=str(user_id),
        course_id=str(profile_data.course_id),
        referral_source=profile_data.referral_source,
        referral_source_detail=profile_data.referral_source_detail,
        motivation=profile_data.motivation,
        exam_date=profile_data.exam_date,
        days_until_exam=days_until_exam,
        current_level=profile_data.current_level,
        target_score_percentage=profile_data.target_score_percentage,
        daily_commitment_minutes=profile_data.daily_commitment_minutes,
        acquisition_channel=profile_data.acquisition_channel,
        referral_code=profile_data.referral_code
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Initialize competency tracking for all KAs in the course
    from app.services.competency import initialize_user_competencies
    initialize_user_competencies(db, str(user_id), str(profile_data.course_id))
    
    return profile


def update_user_profile(
    db: Session,
    user_id: uuid.UUID,
    profile_data: UserProfileUpdate
) -> UserProfile:
    """
    Update user profile.
    
    Users can update their study preferences.
    
    Args:
        db: Database session
        user_id: User ID
        profile_data: Profile update data
        
    Returns:
        Updated UserProfile
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == str(user_id)).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    # Update fields
    if profile_data.exam_date is not None:
        profile.exam_date = profile_data.exam_date
        if profile_data.exam_date:
            profile.days_until_exam = (profile_data.exam_date - date.today()).days
        else:
            profile.days_until_exam = None
    
    if profile_data.current_level is not None:
        profile.current_level = profile_data.current_level
    
    if profile_data.target_score_percentage is not None:
        profile.target_score_percentage = profile_data.target_score_percentage
    
    if profile_data.daily_commitment_minutes is not None:
        profile.daily_commitment_minutes = profile_data.daily_commitment_minutes
    
    db.commit()
    db.refresh(profile)
    
    return profile


def get_user_profile(db: Session, user_id: uuid.UUID) -> Optional[UserProfile]:
    """
    Get user profile.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        UserProfile if exists, None otherwise
    """
    return db.query(UserProfile).filter(UserProfile.user_id == str(user_id)).first()


def get_user_with_profile(db: Session, user_id: uuid.UUID) -> User:
    """
    Get user with profile loaded.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        User with profile relationship loaded
    """
    user = db.query(User).filter(User.user_id == str(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Profile will be loaded via relationship
    return user
