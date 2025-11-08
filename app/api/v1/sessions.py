"""
Session API endpoints.

Handles practice sessions, question attempts, and competency tracking.
Decision #12: Daily practice sessions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.user import User
from app.models.learning import Session as LearningSession, QuestionAttempt
from app.models.question import Question, AnswerChoice
from app.schemas.learning import SessionCreate, SessionResponse, SessionCompleteRequest
from app.schemas.question import (
    QuestionPublicResponse, QuestionAttemptCreate, QuestionAttemptWithExplanationResponse
)
from app.services.competency import update_competency_after_attempt, get_weakest_ka
from app.api.dependencies import get_current_active_user
from typing import List
from datetime import datetime, timezone
import uuid as uuid_lib


router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new practice session.

    Decision #12: Daily practice sessions (diagnostic, practice, mock_exam, review).
    """
    # Get user's profile to get course_id
    from app.models.user import UserProfile
    profile = db.query(UserProfile).filter(UserProfile.user_id == str(current_user.user_id)).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile not found. Complete onboarding first."
        )

    session = LearningSession(
        user_id=str(current_user.user_id),
        course_id=profile.course_id,
        session_type=session_data.session_type,
        total_questions=0,
        correct_answers=0,
        is_completed=False
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get session details.
    """
    session = db.query(LearningSession).filter(
        LearningSession.session_id == str(session_id),
        LearningSession.user_id == str(current_user.user_id)
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return session


@router.get("/{session_id}/next-question", response_model=QuestionPublicResponse)
def get_next_question(
    session_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get next question for practice session.
    
    Decision #3: Adaptive question selection based on weakest KA.
    
    Algorithm (simplified for MVP):
    1. Find user's weakest KA
    2. Select question from that KA matching user's competency level
    3. Avoid recently attempted questions
    """
    # Verify session exists and belongs to user
    session = db.query(LearningSession).filter(
        LearningSession.session_id == str(session_id),
        LearningSession.user_id == str(current_user.user_id)
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get user's weakest KA
    weakest_competency = get_weakest_ka(db, str(current_user.user_id))
    
    if not weakest_competency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no competency records. Complete onboarding first."
        )
    
    # Get questions from weakest KA that match competency level (±0.15 range)
    from decimal import Decimal
    target_difficulty = weakest_competency.competency_score
    difficulty_range = Decimal("0.15")
    
    # Get recently attempted question IDs to exclude
    recent_attempts = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == str(current_user.user_id)
    ).order_by(QuestionAttempt.attempted_at.desc()).limit(20).all()
    recent_question_ids = [attempt.question_id for attempt in recent_attempts]
    
    # Find suitable question
    query = db.query(Question).filter(
        Question.ka_id == weakest_competency.ka_id,
        Question.is_active == True,
        Question.difficulty >= (target_difficulty - difficulty_range),
        Question.difficulty <= (target_difficulty + difficulty_range)
    )
    
    if recent_question_ids:
        query = query.filter(~Question.question_id.in_(recent_question_ids))
    
    question = query.first()
    
    if not question:
        # Fallback: get any question from weakest KA
        question = db.query(Question).filter(
            Question.ka_id == weakest_competency.ka_id,
            Question.is_active == True
        ).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No questions available for this knowledge area"
        )
    
    return question


@router.post("/{session_id}/attempt", response_model=QuestionAttemptWithExplanationResponse)
def submit_answer(
    session_id: uuid_lib.UUID,
    attempt_data: QuestionAttemptCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit answer to a question.
    
    Decision #18: Update competency after each attempt.
    
    Steps:
    1. Verify session exists
    2. Get question and check if answer is correct
    3. Update session stats
    4. Update user competency (IRT)
    5. Return result with explanation
    """
    # Verify session
    session = db.query(LearningSession).filter(
        LearningSession.session_id == str(session_id),
        LearningSession.user_id == str(current_user.user_id)
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get question
    question = db.query(Question).filter(
        Question.question_id == str(attempt_data.question_id)
    ).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    # Get selected answer choice
    selected_choice = db.query(AnswerChoice).filter(
        AnswerChoice.choice_id == str(attempt_data.selected_choice_id)
    ).first()
    
    if not selected_choice or selected_choice.question_id != question.question_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid answer choice"
        )
    
    # Check if correct
    is_correct = selected_choice.is_correct
    
    # Get current competency before update
    from app.services.competency import get_user_competencies
    competencies = get_user_competencies(db, str(current_user.user_id))
    user_competency = next((c for c in competencies if c.ka_id == question.ka_id), None)
    user_competency_score = user_competency.competency_score if user_competency else None

    # Create attempt record
    attempt = QuestionAttempt(
        user_id=str(current_user.user_id),
        question_id=question.question_id,
        session_id=str(session_id),
        selected_choice_id=str(attempt_data.selected_choice_id),
        is_correct=is_correct,
        time_spent_seconds=attempt_data.time_spent_seconds,
        user_competency_at_attempt=user_competency_score,
        question_difficulty_at_attempt=question.difficulty
    )
    
    db.add(attempt)
    
    # Update session stats
    session.total_questions += 1
    if is_correct:
        session.correct_answers += 1
    
    # Update user competency
    update_competency_after_attempt(
        db=db,
        user_id=str(current_user.user_id),
        ka_id=question.ka_id,
        is_correct=is_correct,
        question_difficulty=question.difficulty
    )
    
    db.commit()
    db.refresh(attempt)
    
    # Get correct choice for explanation
    correct_choice = db.query(AnswerChoice).filter(
        AnswerChoice.question_id == question.question_id,
        AnswerChoice.is_correct == True
    ).first()
    
    # Build response with explanation
    return QuestionAttemptWithExplanationResponse(
        attempt_id=attempt.attempt_id,
        user_id=attempt.user_id,
        question_id=attempt.question_id,
        session_id=attempt.session_id,
        selected_choice_id=attempt.selected_choice_id,
        is_correct=attempt.is_correct,
        time_spent_seconds=attempt.time_spent_seconds,
        competency_at_attempt=attempt.competency_at_attempt,
        attempted_at=attempt.attempted_at,
        correct_choice_id=correct_choice.choice_id,
        correct_choice_letter=correct_choice.choice_letter,
        explanation=correct_choice.explanation,
        question_text=question.question_text,
        all_choices=question.answer_choices
    )


@router.post("/{session_id}/complete", response_model=SessionResponse)
def complete_session(
    session_id: uuid_lib.UUID,
    complete_data: SessionCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark session as complete.
    """
    session = db.query(LearningSession).filter(
        LearningSession.session_id == str(session_id),
        LearningSession.user_id == str(current_user.user_id)
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.is_completed = True
    session.completed_at = datetime.now(timezone.utc)

    if complete_data.duration_minutes:
        session.duration_seconds = complete_data.duration_minutes * 60

    db.commit()
    db.refresh(session)

    return session
