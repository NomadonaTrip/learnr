"""
Diagnostic Assessment API endpoints.

Decision #32: Diagnostic assessment (24 questions, 4 per KA).
User Flow #2: Initial diagnostic to establish baseline competency.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.database import get_db
from app.models.user import User
from app.models.course import Course, KnowledgeArea
from app.models.learning import Session as LearningSession, QuestionAttempt
from app.models.question import Question, AnswerChoice
from app.api.dependencies import get_current_active_user
from app.schemas.diagnostic import (
    DiagnosticStartRequest,
    DiagnosticStartResponse,
    DiagnosticQuestionResponse,
    DiagnosticAnswerSubmit,
    DiagnosticAnswerResponse,
    DiagnosticResultsResponse,
    DiagnosticKAResult,
    DiagnosticProgressResponse
)
from app.services.question_selection import select_diagnostic_questions, get_already_attempted_question_ids
from app.services.spaced_repetition import create_or_update_sr_card
from app.services.competency import (
    calculate_diagnostic_competencies,
    calculate_weighted_competency,
    determine_competency_status
)

router = APIRouter()


@router.post("/start", response_model=DiagnosticStartResponse, status_code=status.HTTP_201_CREATED)
def start_diagnostic(
    request: DiagnosticStartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start a new diagnostic assessment.

    Decision #32: 24 questions total (4 per KA), mixed difficulty.

    Creates a new diagnostic session and pre-selects all questions.
    Returns session_id for tracking progress through the diagnostic.
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

    # Check if user already has an incomplete diagnostic for this course
    existing_session = db.query(LearningSession).filter(
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.course_id == str(request.course_id),
        LearningSession.session_type == 'diagnostic',
        LearningSession.is_completed == False
    ).first()

    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have an incomplete diagnostic session. Complete it first or contact support. Session ID: {existing_session.session_id}"
        )

    # Count KAs for this course
    ka_count = db.query(KnowledgeArea).filter(
        KnowledgeArea.course_id == str(request.course_id)
    ).count()

    questions_per_ka = 4
    total_questions = ka_count * questions_per_ka

    # Create new diagnostic session
    session = LearningSession(
        user_id=str(current_user.user_id),
        course_id=str(request.course_id),
        session_type='diagnostic',
        total_questions=total_questions,
        correct_answers=0,
        is_completed=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return DiagnosticStartResponse(
        session_id=session.session_id,
        course_id=course.course_id,
        course_name=course.course_name,
        total_questions=total_questions,
        questions_per_ka=questions_per_ka,
        status='in_progress',
        started_at=session.started_at
    )


@router.get("/next-question", response_model=DiagnosticQuestionResponse)
def get_next_diagnostic_question(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the next question in the diagnostic assessment.

    Returns questions in a deterministic order (mixed across all KAs).
    Excludes already-answered questions.
    """
    # Verify session exists and belongs to user
    session = db.query(LearningSession).filter(
        LearningSession.session_id == session_id,
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.session_type == 'diagnostic'
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic session not found"
        )

    # Check if already completed
    if session.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Diagnostic already completed. Use /diagnostic/results to view results."
        )

    # Get already attempted questions
    attempted_ids = get_already_attempted_question_ids(db, current_user.user_id, session_id)

    # Get all diagnostic questions for this course
    all_questions = select_diagnostic_questions(db, session.course_id)

    # Filter out already attempted
    remaining_questions = [q for q in all_questions if str(q.question_id) not in attempted_ids]

    if not remaining_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No more questions available. Use /diagnostic/results to complete the diagnostic."
        )

    # Get first remaining question
    next_question = remaining_questions[0]

    # Get KA info
    ka = db.query(KnowledgeArea).filter(
        KnowledgeArea.ka_id == next_question.ka_id
    ).first()

    # Calculate question number (1-indexed)
    question_number = len(attempted_ids) + 1

    # Format answer choices (without is_correct field)
    choices = []
    for choice in next_question.answer_choices:
        choices.append({
            "choice_id": str(choice.choice_id),
            "choice_text": choice.choice_text,
            "choice_order": choice.choice_order
        })

    return DiagnosticQuestionResponse(
        question_id=next_question.question_id,
        question_number=question_number,
        total_questions=session.total_questions,
        ka_id=next_question.ka_id,
        ka_name=ka.ka_name if ka else "Unknown",
        question_text=next_question.question_text,
        question_type=next_question.question_type,
        answer_choices=choices
    )


@router.post("/submit-answer", response_model=DiagnosticAnswerResponse)
def submit_diagnostic_answer(
    submission: DiagnosticAnswerSubmit,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit an answer for a diagnostic question.

    Records the attempt and returns immediate feedback (correct/incorrect).
    Does NOT update competency yet - that happens when results are requested.
    """
    # Verify session
    session = db.query(LearningSession).filter(
        LearningSession.session_id == str(submission.session_id),
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.session_type == 'diagnostic'
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic session not found"
        )

    if session.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Diagnostic already completed"
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
        user_competency_at_attempt=None,  # Will be calculated at results
        question_difficulty_at_attempt=question.difficulty
    )
    db.add(attempt)

    # Update session stats
    if is_correct:
        session.correct_answers += 1

    db.commit()
    db.refresh(attempt)

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

    return DiagnosticAnswerResponse(
        attempt_id=attempt.attempt_id,
        is_correct=is_correct,
        correct_choice_id=correct_choice.choice_id if correct_choice else None,
        explanation=selected_choice.explanation,
        question_number=questions_answered,
        total_questions=session.total_questions,
        questions_remaining=session.total_questions - questions_answered,
        attempted_at=attempt.attempted_at
    )


@router.get("/results", response_model=DiagnosticResultsResponse)
def get_diagnostic_results(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get diagnostic assessment results and calculate initial competencies.

    Decision #22: Simplified IRT approach (correct/total per KA).

    This endpoint:
    1. Calculates competency scores for each KA
    2. Stores competencies in user_competency table
    3. Marks session as completed
    4. Returns detailed results with recommendations
    """
    # Verify session
    session = db.query(LearningSession).filter(
        LearningSession.session_id == session_id,
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.session_type == 'diagnostic'
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic session not found"
        )

    # Get course info
    course = db.query(Course).filter(
        Course.course_id == session.course_id
    ).first()

    # Check if all questions answered
    attempts_count = db.query(QuestionAttempt).filter(
        QuestionAttempt.session_id == session_id
    ).count()

    if attempts_count < session.total_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Diagnostic incomplete. Answered {attempts_count}/{session.total_questions} questions."
        )

    # Calculate competencies (Decision #22)
    competencies = calculate_diagnostic_competencies(db, current_user.user_id, session_id)

    # Build KA results
    ka_results = []
    for competency in competencies:
        ka = db.query(KnowledgeArea).filter(
            KnowledgeArea.ka_id == competency.ka_id
        ).first()

        if ka:
            accuracy = (competency.correct_count / competency.attempts_count * 100) if competency.attempts_count > 0 else 0
            status_label = determine_competency_status(competency.competency_score)

            ka_results.append(DiagnosticKAResult(
                ka_id=competency.ka_id,
                ka_code=ka.ka_code,
                ka_name=ka.ka_name,
                ka_weight_percentage=ka.weight_percentage,
                questions_attempted=competency.attempts_count,
                questions_correct=competency.correct_count,
                accuracy_percentage=accuracy,
                competency_score=competency.competency_score,
                status=status_label
            ))

    # Sort by competency score (weakest first)
    ka_results.sort(key=lambda x: x.competency_score)

    # Calculate overall metrics
    overall_accuracy = (session.correct_answers / session.total_questions * 100) if session.total_questions > 0 else 0
    overall_competency = calculate_weighted_competency(db, current_user.user_id, session.course_id)

    # Find weakest KA
    weakest_ka = ka_results[0] if ka_results else None

    # Generate recommendation
    if not weakest_ka:
        recommendation = "Complete more questions to establish baseline competency."
    elif overall_competency >= Decimal('0.80'):
        recommendation = f"Excellent performance! You're well-prepared. Focus on maintaining mastery in {weakest_ka.ka_name} to ensure balanced readiness."
    elif overall_competency >= Decimal('0.60'):
        recommendation = f"Good foundation. Focus your study on {weakest_ka.ka_name} (current: {float(weakest_ka.competency_score)*100:.0f}%) to improve overall readiness."
    else:
        recommendation = f"Significant preparation needed. Start with {weakest_ka.ka_name} and build foundational knowledge across all areas."

    # Mark session as completed
    if not session.is_completed:
        session.is_completed = True
        session.completed_at = datetime.now(timezone.utc)

        # Calculate duration
        if session.started_at and session.completed_at:
            duration = session.completed_at - session.started_at
            session.duration_seconds = int(duration.total_seconds())

        # Calculate score percentage
        session.score_percentage = Decimal(str(overall_accuracy))

        db.commit()
        db.refresh(session)

    # Calculate duration in minutes
    duration_minutes = 0
    if session.duration_seconds:
        duration_minutes = session.duration_seconds // 60

    return DiagnosticResultsResponse(
        session_id=session.session_id,
        user_id=current_user.user_id,
        course_id=course.course_id,
        course_name=course.course_name,
        total_questions=session.total_questions,
        total_correct=session.correct_answers,
        overall_accuracy=overall_accuracy,
        overall_competency=overall_competency,
        ka_results=ka_results,
        started_at=session.started_at,
        completed_at=session.completed_at,
        duration_minutes=duration_minutes,
        weakest_ka_id=weakest_ka.ka_id if weakest_ka else None,
        weakest_ka_name=weakest_ka.ka_name if weakest_ka else "Unknown",
        recommendation=recommendation
    )


@router.get("/progress", response_model=DiagnosticProgressResponse)
def get_diagnostic_progress(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current progress in diagnostic assessment.

    Useful for resuming incomplete diagnostics or checking status.
    """
    # Verify session
    session = db.query(LearningSession).filter(
        LearningSession.session_id == session_id,
        LearningSession.user_id == str(current_user.user_id),
        LearningSession.session_type == 'diagnostic'
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic session not found"
        )

    # Count answered questions
    questions_answered = db.query(QuestionAttempt).filter(
        QuestionAttempt.session_id == session_id
    ).count()

    # Calculate progress percentage
    progress_percentage = (questions_answered / session.total_questions * 100) if session.total_questions > 0 else 0

    return DiagnosticProgressResponse(
        session_id=session.session_id,
        session_type=session.session_type,
        is_completed=session.is_completed,
        questions_answered=questions_answered,
        total_questions=session.total_questions,
        progress_percentage=progress_percentage,
        started_at=session.started_at
    )
