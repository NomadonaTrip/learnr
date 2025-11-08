"""
Question selection service for adaptive learning and diagnostics.

Decision #32: Diagnostic assessment with 4 questions per KA.
Decision #3: Adaptive learning - select questions based on competency.
"""
from typing import List, Set
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.question import Question
from app.models.course import KnowledgeArea
from app.models.learning import QuestionAttempt, UserCompetency
import uuid


def select_diagnostic_questions(
    db: Session,
    course_id: uuid.UUID,
    questions_per_ka: int = 4
) -> List[Question]:
    """
    Select questions for diagnostic assessment.

    Decision #32: 24 questions total (4 per KA), mixed difficulty.

    Strategy:
    - For each KA in the course, select 4 questions
    - Mix difficulty levels: 1 easy (0.0-0.4), 2 medium (0.4-0.7), 1 hard (0.7-1.0)
    - Random selection within difficulty bands
    - Ensures balanced assessment across all knowledge areas

    Args:
        db: Database session
        course_id: Course ID
        questions_per_ka: Number of questions per KA (default 4)

    Returns:
        List of Question objects (typically 24 for CBAP with 6 KAs)
    """
    # Get all KAs for the course
    knowledge_areas = db.query(KnowledgeArea).filter(
        KnowledgeArea.course_id == course_id
    ).all()

    diagnostic_questions = []

    for ka in knowledge_areas:
        # Select 1 easy question (difficulty 0.0-0.4)
        easy = db.query(Question).filter(
            Question.course_id == course_id,
            Question.ka_id == ka.ka_id,
            Question.is_active == True,
            Question.difficulty >= 0.0,
            Question.difficulty < 0.4
        ).order_by(func.random()).limit(1).all()

        # Select 2 medium questions (difficulty 0.4-0.7)
        medium = db.query(Question).filter(
            Question.course_id == course_id,
            Question.ka_id == ka.ka_id,
            Question.is_active == True,
            Question.difficulty >= 0.4,
            Question.difficulty < 0.7
        ).order_by(func.random()).limit(2).all()

        # Select 1 hard question (difficulty 0.7-1.0)
        hard = db.query(Question).filter(
            Question.course_id == course_id,
            Question.ka_id == ka.ka_id,
            Question.is_active == True,
            Question.difficulty >= 0.7,
            Question.difficulty <= 1.0
        ).order_by(func.random()).limit(1).all()

        # Combine all difficulty levels
        ka_questions = easy + medium + hard

        # If we don't have enough questions in specific difficulty bands,
        # fill remaining slots with random questions from this KA
        remaining = questions_per_ka - len(ka_questions)
        if remaining > 0:
            # Get IDs of already selected questions
            selected_ids = [q.question_id for q in ka_questions]

            # Select additional random questions
            additional = db.query(Question).filter(
                Question.course_id == course_id,
                Question.ka_id == ka.ka_id,
                Question.is_active == True,
                ~Question.question_id.in_(selected_ids) if selected_ids else True
            ).order_by(func.random()).limit(remaining).all()

            ka_questions.extend(additional)

        diagnostic_questions.extend(ka_questions)

    return diagnostic_questions


def get_already_attempted_question_ids(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID
) -> Set[str]:
    """
    Get set of question IDs already attempted in a session.

    Used to prevent showing duplicate questions in same session.

    Args:
        db: Database session
        user_id: User ID
        session_id: Session ID

    Returns:
        Set of question_id strings
    """
    attempts = db.query(QuestionAttempt.question_id).filter(
        QuestionAttempt.user_id == user_id,
        QuestionAttempt.session_id == session_id
    ).all()

    return {str(attempt.question_id) for attempt in attempts}


def select_adaptive_question(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    exclude_question_ids: Set[str] = None
) -> Question:
    """
    Select next question using adaptive learning algorithm.

    Decision #3: Adaptive learning as core mechanism.

    Strategy:
    1. Find user's weakest KA (lowest competency score)
    2. Select question with difficulty matching user's competency (±0.1)
    3. Exclude recently answered questions

    Args:
        db: Database session
        user_id: User ID
        course_id: Course ID
        exclude_question_ids: Set of question IDs to exclude (recently answered)

    Returns:
        Question object matched to user's competency level
    """
    if exclude_question_ids is None:
        exclude_question_ids = set()

    # Get user's weakest KA
    weakest_competency = db.query(UserCompetency).filter(
        UserCompetency.user_id == user_id
    ).order_by(UserCompetency.competency_score.asc()).first()

    if not weakest_competency:
        # No competency data - return random question
        question = db.query(Question).filter(
            Question.course_id == course_id,
            Question.is_active == True,
            ~Question.question_id.in_(exclude_question_ids) if exclude_question_ids else True
        ).order_by(func.random()).first()
        return question

    # Target difficulty = user's competency score ± 0.1
    target_difficulty = float(weakest_competency.competency_score)
    difficulty_range_lower = max(0.0, target_difficulty - 0.1)
    difficulty_range_upper = min(1.0, target_difficulty + 0.1)

    # Select question matching difficulty for weakest KA
    question = db.query(Question).filter(
        Question.course_id == course_id,
        Question.ka_id == weakest_competency.ka_id,
        Question.is_active == True,
        Question.difficulty >= difficulty_range_lower,
        Question.difficulty <= difficulty_range_upper,
        ~Question.question_id.in_(exclude_question_ids) if exclude_question_ids else True
    ).order_by(func.random()).first()

    # Fallback: if no matching question found, select any from weakest KA
    if not question:
        question = db.query(Question).filter(
            Question.course_id == course_id,
            Question.ka_id == weakest_competency.ka_id,
            Question.is_active == True,
            ~Question.question_id.in_(exclude_question_ids) if exclude_question_ids else True
        ).order_by(func.random()).first()

    # Final fallback: if still no question, return any question from course
    if not question:
        question = db.query(Question).filter(
            Question.course_id == course_id,
            Question.is_active == True,
            ~Question.question_id.in_(exclude_question_ids) if exclude_question_ids else True
        ).order_by(func.random()).first()

    return question


def select_practice_questions(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    count: int = 10,
    ka_id: uuid.UUID = None
) -> List[Question]:
    """
    Select questions for practice session.

    Uses adaptive algorithm to focus on weak areas.

    Args:
        db: Database session
        user_id: User ID
        course_id: Course ID
        count: Number of questions to select
        ka_id: Optional - focus on specific KA

    Returns:
        List of Question objects
    """
    questions = []
    exclude_ids = set()

    for _ in range(count):
        # If ka_id specified, override adaptive selection
        if ka_id:
            question = db.query(Question).filter(
                Question.course_id == course_id,
                Question.ka_id == ka_id,
                Question.is_active == True,
                ~Question.question_id.in_(exclude_ids) if exclude_ids else True
            ).order_by(func.random()).first()
        else:
            question = select_adaptive_question(db, user_id, course_id, exclude_ids)

        if question:
            questions.append(question)
            exclude_ids.add(str(question.question_id))
        else:
            # No more questions available
            break

    return questions


# ============================================================================
# Question Selection Utility Functions (for testing and algorithm verification)
# ============================================================================

def select_next_question(
    db: Session,
    user_id: uuid.UUID,
    exclude_question_ids: List[str] = None
) -> Question:
    """
    Select next question for user (wrapper for select_adaptive_question).

    This is an alias function for testing compatibility.

    Args:
        db: Database session
        user_id: User ID
        exclude_question_ids: List of question IDs to exclude

    Returns:
        Question object or None
    """
    # Get user's course from their competencies
    competency = db.query(UserCompetency).filter(
        UserCompetency.user_id == user_id
    ).first()

    if not competency:
        return None

    # Get course_id from KA
    ka = db.query(KnowledgeArea).filter(
        KnowledgeArea.ka_id == competency.ka_id
    ).first()

    if not ka:
        return None

    # Convert list to set for compatibility
    exclude_ids = set(exclude_question_ids) if exclude_question_ids else set()

    return select_adaptive_question(db, user_id, ka.course_id, exclude_ids)


def get_weakest_knowledge_area(competencies: List[UserCompetency]) -> UserCompetency:
    """
    Get weakest knowledge area from a list of competencies.

    Args:
        competencies: List of UserCompetency objects

    Returns:
        UserCompetency with lowest score, or None if list is empty
    """
    if not competencies:
        return None

    return min(competencies, key=lambda c: c.competency_score)


def filter_questions_by_difficulty(
    questions: List[Question],
    target_difficulty: Decimal,
    tolerance: Decimal
) -> List[Question]:
    """
    Filter questions by difficulty range.

    Args:
        questions: List of Question objects
        target_difficulty: Target difficulty score
        tolerance: Tolerance range (e.g., 0.1 for ±0.1)

    Returns:
        Filtered list of questions within difficulty range
    """
    lower_bound = target_difficulty - tolerance
    upper_bound = target_difficulty + tolerance

    filtered = [
        q for q in questions
        if lower_bound <= q.difficulty <= upper_bound
    ]

    return filtered


def exclude_recent_questions(
    all_questions: List[Question],
    recent_attempts: List[QuestionAttempt],
    hours_window: int = 24
) -> List[Question]:
    """
    Exclude questions answered within a time window.

    Args:
        all_questions: List of all available questions
        recent_attempts: List of recent question attempts
        hours_window: Time window in hours to exclude (default 24)

    Returns:
        Filtered list excluding recently attempted questions
    """
    from datetime import datetime, timedelta, timezone

    # Calculate cutoff time
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_window)

    # Get question IDs answered within window
    recent_question_ids = {
        str(attempt.question_id)
        for attempt in recent_attempts
        if attempt.created_at >= cutoff_time
    }

    # Filter out recent questions
    filtered = [
        q for q in all_questions
        if str(q.question_id) not in recent_question_ids
    ]

    return filtered


def calculate_question_priority(
    question_difficulty: Decimal,
    user_competency: Decimal
) -> float:
    """
    Calculate priority score for question selection.

    Questions closer to user's competency get higher priority.
    Uses inverse of distance as priority metric.

    Args:
        question_difficulty: Question's difficulty score (0-1)
        user_competency: User's competency score (0-1)

    Returns:
        Priority score (higher is better)
    """
    # Calculate distance from user competency
    distance = abs(float(question_difficulty) - float(user_competency))

    # Priority is inverse of distance (closer = higher priority)
    # Add small constant to avoid division by zero
    priority = 1.0 / (distance + 0.01)

    return priority
