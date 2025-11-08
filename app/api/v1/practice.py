"""
Practice Session API endpoints.

Decision #12: Daily practice sessions with adaptive learning.
Decision #3: Adaptive question selection based on competency.
User Flow #3: Practice sessions targeting weak areas.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal

from app.models.database import get_db
from app.models.user import User
from app.models.course import Course, KnowledgeArea
from app.models.learning import Session as LearningSession, QuestionAttempt, UserCompetency
from app.models.question import Question, AnswerChoice
from app.api.dependencies import get_current_active_user
from app.schemas.practice import (
    PracticeStartRequest,
    PracticeStartResponse,
    PracticeQuestionResponse,
    PracticeSubmitRequest,
    PracticeSubmitResponse,
    PracticeSessionResponse,
    PracticeCompleteRequest,
    PracticeCompleteResponse,
    PracticeHistoryResponse
)
from app.services.spaced_repetition import create_or_update_sr_card
from app.services.question_selection import select_adaptive_question, get_already_attempted_question_ids
from app.services.competency import update_competency_after_attempt, get_weakest_ka, get_user_competencies

router = APIRouter()


@router.post("/start", response_model=PracticeStartResponse, status_code=status.HTTP_201_CREATED)
def start_practice_session(
    request: PracticeStartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start a new practice session.

    Decision #3: Adaptive learning - targets weakest KAs by default.

    If knowledge_area_id is specified, focuses on that KA.
    Otherwise, uses adaptive algorithm to target weak areas.
    """
    # Verify course exists and is active
    course = db.query(Course).filter(
        Course.course_id == str(request.course_id),
        Course.status == 'active'
    ).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or not active"
        )

    # Get target KA info if specified
    target_ka = None
    if request.knowledge_area_id:
        target_ka = db.query(KnowledgeArea).filter(
            KnowledgeArea.ka_id == str(request.knowledge_area_id),
            KnowledgeArea.course_id == str(request.course_id)
        ).first()

        if not target_ka:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge area not found for this course"
            )

    # Create practice session
    session = LearningSession(
        user_id=str(current_user.user_id),
        course_id=str(request.course_id),
        session_type='practice',
        total_questions=request.num_questions,
        correct_answers=0,
        is_completed=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return PracticeStartResponse(
        session_id=session.session_id,
        course_id=course.course_id,
        course_name=course.course_name,
        total_questions=request.num_questions,
        target_ka_id=target_ka.ka_id if target_ka else None,
        target_ka_name=target_ka.ka_name if target_ka else None,
        session_type='practice',
        started_at=session.started_at
    )


@router.get("/next-question", response_model=PracticeQuestionResponse)
def get_next_practice_question(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the next adaptive question for practice.

    Decision #3: Uses adaptive algorithm to select questions matching user's competency.

    Algorithm:
    1. Find user's weakest KA (or use session's target KA)
    2. Select question with difficulty matching competency ±0.1
    3. Exclude already-answered questions in this session
    """
    # Verify session exists and belongs to user
    session = db.query(LearningSession).filter(
        LearningSession.session_id == session_id,
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.session_type == 'practice'
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice session not found"
        )

    # Check if already completed
    if session.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Practice session already completed. Start a new session."
        )

    # Check if all questions answered
    questions_answered = db.query(QuestionAttempt).filter(
        QuestionAttempt.session_id == session_id
    ).count()

    if questions_answered >= session.total_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"All {session.total_questions} questions answered. Use /practice/complete to finish session."
        )

    # Get already attempted questions in this session
    attempted_ids = get_already_attempted_question_ids(db, current_user.user_id, session_id)

    # Select next adaptive question
    next_question = select_adaptive_question(
        db=db,
        user_id=current_user.user_id,
        course_id=session.course_id,
        exclude_question_ids=attempted_ids
    )

    if not next_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No more questions available for your competency level"
        )

    # Get KA info and user's current competency
    ka = db.query(KnowledgeArea).filter(
        KnowledgeArea.ka_id == next_question.ka_id
    ).first()

    user_competency = db.query(UserCompetency).filter(
        UserCompetency.user_id == str(current_user.user_id),
        UserCompetency.ka_id == next_question.ka_id
    ).first()

    current_competency = user_competency.competency_score if user_competency else Decimal('0.50')

    # Calculate question number (1-indexed)
    question_number = questions_answered + 1

    # Format answer choices (without is_correct field)
    choices = []
    for choice in next_question.answer_choices:
        choices.append({
            "choice_id": str(choice.choice_id),
            "choice_text": choice.choice_text,
            "choice_order": choice.choice_order
        })

    return PracticeQuestionResponse(
        question_id=next_question.question_id,
        question_number=question_number,
        total_questions=session.total_questions,
        ka_id=next_question.ka_id,
        ka_name=ka.ka_name if ka else "Unknown",
        ka_current_competency=current_competency,
        question_text=next_question.question_text,
        question_type=next_question.question_type,
        difficulty=next_question.difficulty,
        answer_choices=choices
    )


@router.post("/submit-answer", response_model=PracticeSubmitResponse)
def submit_practice_answer(
    submission: PracticeSubmitRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit an answer for a practice question.

    Decision #3: Updates competency in real-time after each answer.

    Returns immediate feedback and competency change.
    """
    # Verify session
    session = db.query(LearningSession).filter(
        LearningSession.session_id == str(submission.session_id),
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.session_type == 'practice'
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice session not found"
        )

    if session.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Practice session already completed"
        )

    # Verify question exists
    question = db.query(Question).filter(
        Question.question_id == str(submission.question_id)
    ).first()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    # Check if already attempted
    existing_attempt = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == str(current_user.user_id),
        QuestionAttempt.question_id == str(submission.question_id),
        QuestionAttempt.session_id == str(submission.session_id)
    ).first()

    if existing_attempt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question already answered in this session"
        )

    # Verify selected choice exists and belongs to this question
    selected_choice = db.query(AnswerChoice).filter(
        AnswerChoice.choice_id == str(submission.selected_choice_id),
        AnswerChoice.question_id == str(submission.question_id)
    ).first()

    if not selected_choice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid answer choice"
        )

    # Get KA info
    ka = db.query(KnowledgeArea).filter(
        KnowledgeArea.ka_id == question.ka_id
    ).first()

    # Get previous competency
    prev_competency_record = db.query(UserCompetency).filter(
        UserCompetency.user_id == str(current_user.user_id),
        UserCompetency.ka_id == question.ka_id
    ).first()

    previous_competency = prev_competency_record.competency_score if prev_competency_record else Decimal('0.50')

    # Determine correctness
    is_correct = selected_choice.is_correct

    # Create attempt record
    attempt = QuestionAttempt(
        user_id=str(current_user.user_id),
        question_id=str(submission.question_id),
        session_id=str(submission.session_id),
        selected_choice_id=str(submission.selected_choice_id),
        is_correct=is_correct,
        time_spent_seconds=submission.time_spent_seconds,
        user_competency_at_attempt=previous_competency,
        question_difficulty_at_attempt=question.difficulty
    )
    db.add(attempt)

    # Update session stats
    if is_correct:
        session.correct_answers += 1

    db.commit()
    db.refresh(attempt)

    # Update competency in real-time (Decision #3)
    updated_competency = update_competency_after_attempt(
        db=db,
        user_id=current_user.user_id,
        ka_id=question.ka_id,
        is_correct=is_correct,
        question_difficulty=question.difficulty
    )

    new_competency = updated_competency.competency_score
    competency_change = new_competency - previous_competency

    # Create/update spaced repetition card (Decision #31)
    create_or_update_sr_card(
        db=db,
        user_id=current_user.user_id,
        question_id=question.question_id,
        is_correct=is_correct,
        quality=None  # Will be inferred from is_correct (4 if correct, 2 if incorrect)
    )

    # Get correct choice for feedback
    correct_choice = db.query(AnswerChoice).filter(
        AnswerChoice.question_id == str(submission.question_id),
        AnswerChoice.is_correct == True
    ).first()

    # Calculate progress
    questions_answered = db.query(QuestionAttempt).filter(
        QuestionAttempt.session_id == str(submission.session_id)
    ).count()

    # Calculate session accuracy
    session_accuracy = (session.correct_answers / questions_answered * 100) if questions_answered > 0 else 0.0

    return PracticeSubmitResponse(
        attempt_id=attempt.attempt_id,
        is_correct=is_correct,
        correct_choice_id=correct_choice.choice_id if correct_choice else None,
        explanation=selected_choice.explanation,
        question_number=questions_answered,
        total_questions=session.total_questions,
        questions_remaining=session.total_questions - questions_answered,
        ka_id=question.ka_id,
        ka_name=ka.ka_name if ka else "Unknown",
        previous_competency=previous_competency,
        new_competency=new_competency,
        competency_change=competency_change,
        session_accuracy=session_accuracy,
        attempted_at=attempt.attempted_at
    )


@router.get("/session/{session_id}", response_model=PracticeSessionResponse)
def get_practice_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get practice session details and current state.

    Useful for resuming sessions or checking progress.
    """
    # Verify session
    session = db.query(LearningSession).filter(
        LearningSession.session_id == session_id,
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.session_type == 'practice'
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice session not found"
        )

    # Count answered questions
    questions_answered = db.query(QuestionAttempt).filter(
        QuestionAttempt.session_id == session_id
    ).count()

    # Calculate accuracy
    accuracy = (session.correct_answers / questions_answered * 100) if questions_answered > 0 else 0.0

    # Get recent attempts (last 5)
    recent_attempts_records = db.query(QuestionAttempt).filter(
        QuestionAttempt.session_id == session_id
    ).order_by(QuestionAttempt.attempted_at.desc()).limit(5).all()

    recent_attempts = []
    for attempt in recent_attempts_records:
        recent_attempts.append({
            "question_id": str(attempt.question_id),
            "is_correct": attempt.is_correct,
            "attempted_at": attempt.attempted_at.isoformat()
        })

    # Calculate duration
    duration_seconds = None
    if session.completed_at:
        duration_seconds = int((session.completed_at - session.started_at).total_seconds())
    elif session.started_at:
        duration_seconds = int((datetime.now(timezone.utc) - session.started_at).total_seconds())

    return PracticeSessionResponse(
        session_id=session.session_id,
        user_id=current_user.user_id,
        course_id=session.course_id,
        session_type=session.session_type,
        total_questions=session.total_questions,
        target_ka_id=None,  # Could be enhanced to store in session
        questions_answered=questions_answered,
        correct_answers=session.correct_answers,
        accuracy_percentage=accuracy,
        is_completed=session.is_completed,
        started_at=session.started_at,
        completed_at=session.completed_at,
        duration_seconds=duration_seconds,
        recent_attempts=recent_attempts
    )


@router.post("/complete", response_model=PracticeCompleteResponse)
def complete_practice_session(
    request: PracticeCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark practice session as complete and get summary.

    Shows competency improvements and recommendations.
    """
    # Verify session
    session = db.query(LearningSession).filter(
        LearningSession.session_id == str(request.session_id),
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.session_type == 'practice'
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice session not found"
        )

    if session.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Practice session already completed"
        )

    # Get all attempts from this session
    attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.session_id == str(request.session_id)
    ).all()

    if len(attempts) < session.total_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session incomplete. {len(attempts)}/{session.total_questions} questions answered."
        )

    # Track competency changes by KA
    competency_changes = {}
    for attempt in attempts:
        ka_id = str(attempt.question.ka_id)
        if ka_id not in competency_changes:
            competency_changes[ka_id] = {
                "ka_name": attempt.question.knowledge_area.ka_name,
                "before": attempt.user_competency_at_attempt or Decimal('0.50'),
                "after": None
            }

    # Get current competencies
    current_competencies = db.query(UserCompetency).filter(
        UserCompetency.user_id == str(current_user.user_id)
    ).all()

    competencies_improved = []
    for comp in current_competencies:
        ka_id = str(comp.ka_id)
        if ka_id in competency_changes:
            competency_changes[ka_id]["after"] = comp.competency_score
            competencies_improved.append({
                "ka_name": competency_changes[ka_id]["ka_name"],
                "before": float(competency_changes[ka_id]["before"]),
                "after": float(comp.competency_score),
                "change": float(comp.competency_score - competency_changes[ka_id]["before"])
            })

    # Find weakest KA
    weakest = get_weakest_ka(db, current_user.user_id)
    weakest_ka_name = weakest.knowledge_area.ka_name if weakest else "Unknown"

    # Generate recommendation
    accuracy = (session.correct_answers / len(attempts) * 100) if attempts else 0.0
    if accuracy >= 80:
        recommendation = f"Great work! You're mastering this material. Consider focusing on {weakest_ka_name} to further improve."
    elif accuracy >= 60:
        recommendation = f"Good progress. Continue practicing, especially in {weakest_ka_name}, to strengthen your understanding."
    else:
        recommendation = f"Keep practicing! Focus on reviewing {weakest_ka_name} fundamentals to build a stronger foundation."

    # Mark session as completed
    session.is_completed = True
    session.completed_at = datetime.now(timezone.utc)
    session.duration_seconds = int((session.completed_at - session.started_at).total_seconds())
    session.score_percentage = Decimal(str(accuracy))

    db.commit()
    db.refresh(session)

    # Calculate duration in minutes
    duration_minutes = session.duration_seconds // 60 if session.duration_seconds else 0

    return PracticeCompleteResponse(
        session_id=session.session_id,
        total_questions=session.total_questions,
        correct_answers=session.correct_answers,
        accuracy_percentage=accuracy,
        duration_minutes=duration_minutes,
        competencies_improved=competencies_improved,
        weakest_ka_name=weakest_ka_name,
        recommendation=recommendation,
        completed_at=session.completed_at
    )


@router.get("/history", response_model=PracticeHistoryResponse)
def get_practice_history(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user's practice session history.

    Shows past sessions, overall statistics, and trends.
    """
    # Get all practice sessions
    all_sessions = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.session_type == 'practice'
    ).all()

    # Calculate totals
    total_sessions = len(all_sessions)
    total_questions = sum(s.total_questions for s in all_sessions if s.is_completed)
    total_correct = sum(s.correct_answers for s in all_sessions if s.is_completed)
    overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0.0

    # Get recent sessions (limited)
    recent_sessions = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.session_type == 'practice'
    ).order_by(LearningSession.created_at.desc()).limit(limit).all()

    # Build session summaries
    sessions = []
    for session in recent_sessions:
        questions_answered = db.query(QuestionAttempt).filter(
            QuestionAttempt.session_id == session.session_id
        ).count()

        accuracy = (session.correct_answers / questions_answered * 100) if questions_answered > 0 else 0.0

        duration_seconds = None
        if session.completed_at:
            duration_seconds = int((session.completed_at - session.started_at).total_seconds())

        sessions.append(PracticeSessionResponse(
            session_id=session.session_id,
            user_id=current_user.user_id,
            course_id=session.course_id,
            session_type=session.session_type,
            total_questions=session.total_questions,
            target_ka_id=None,
            questions_answered=questions_answered,
            correct_answers=session.correct_answers,
            accuracy_percentage=accuracy,
            is_completed=session.is_completed,
            started_at=session.started_at,
            completed_at=session.completed_at,
            duration_seconds=duration_seconds,
            recent_attempts=[]
        ))

    return PracticeHistoryResponse(
        total_sessions=total_sessions,
        total_questions_practiced=total_questions,
        overall_accuracy=overall_accuracy,
        sessions=sessions
    )
