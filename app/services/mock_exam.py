"""
Mock Exam Generation Service.

Generates full-length mock exams that simulate the actual certification exam:
1. Questions distributed proportionally by KA weights
2. Randomized question selection
3. Comprehensive scoring and analytics

Decision #3: Adaptive learning doesn't apply to mock exams (simulates real exam conditions).
"""
from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from decimal import Decimal
from datetime import datetime, timezone
from random import sample

from app.models.course import Course, KnowledgeArea
from app.models.question import Question
from app.models.learning import Session as LearningSession, QuestionAttempt, UserCompetency
from app.models.user import User


def calculate_questions_per_ka(
    course: Course,
    total_questions: int
) -> Dict[str, int]:
    """
    Calculate how many questions should come from each KA based on weights.

    Args:
        course: Course object with knowledge_areas
        total_questions: Total number of questions in exam

    Returns:
        Dict mapping ka_id to number of questions

    Example:
        If course has 3 KAs with weights [30%, 40%, 30%] and total_questions=100:
        Returns {"ka1": 30, "ka2": 40, "ka3": 30}
    """
    distribution = {}
    total_allocated = 0

    # Sort KAs by weight (descending) for better rounding handling
    sorted_kas = sorted(
        course.knowledge_areas,
        key=lambda ka: ka.weight_percentage,
        reverse=True
    )

    for ka in sorted_kas[:-1]:  # All except last
        count = int((float(ka.weight_percentage) / 100.0) * total_questions)
        distribution[ka.ka_id] = count
        total_allocated += count

    # Last KA gets remaining questions (handles rounding)
    last_ka = sorted_kas[-1]
    distribution[last_ka.ka_id] = total_questions - total_allocated

    return distribution


def select_questions_for_mock_exam(
    db: Session,
    course_id: UUID,
    user_id: UUID,
    total_questions: int = 120
) -> List[Question]:
    """
    Select questions for a mock exam with proper KA distribution.

    Strategy:
    1. Get KA weights from course
    2. Calculate questions needed per KA
    3. Randomly select questions from each KA
    4. Avoid questions user has seen in last 50 attempts

    Args:
        db: Database session
        course_id: Course ID
        user_id: User ID (to avoid recent questions)
        total_questions: Total questions in exam (default: 120 for CBAP)

    Returns:
        List of Question objects

    Raises:
        ValueError: If insufficient questions available
    """
    # Get course with KAs
    course = db.query(Course).filter(Course.course_id == str(course_id)).first()

    if not course:
        raise ValueError(f"Course {course_id} not found")

    # Calculate distribution
    distribution = calculate_questions_per_ka(course, total_questions)

    # Get recent question IDs to avoid
    recent_attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.user_id == str(user_id)
    ).order_by(QuestionAttempt.attempted_at.desc()).limit(50).all()

    recent_question_ids = {attempt.question_id for attempt in recent_attempts}

    # Select questions from each KA
    selected_questions = []

    for ka_id, count_needed in distribution.items():
        # Query available questions for this KA
        available_questions = db.query(Question).filter(
            and_(
                Question.course_id == str(course_id),
                Question.ka_id == ka_id,
                Question.is_active == True,
                ~Question.question_id.in_(recent_question_ids) if recent_question_ids else True
            )
        ).all()

        if len(available_questions) < count_needed:
            raise ValueError(
                f"Insufficient questions for KA {ka_id}. "
                f"Need {count_needed}, have {len(available_questions)}"
            )

        # Randomly select required number
        selected = sample(available_questions, count_needed)
        selected_questions.extend(selected)

    # Shuffle final list to mix KAs
    from random import shuffle
    shuffle(selected_questions)

    return selected_questions


def create_mock_exam_session(
    db: Session,
    user_id: UUID,
    course_id: UUID
) -> LearningSession:
    """
    Create a new mock exam session with questions.

    The session is created but questions are not returned immediately.
    Questions should be retrieved one at a time via next_question endpoint.

    Args:
        db: Database session
        user_id: User ID
        course_id: Course ID

    Returns:
        Created Session object

    Raises:
        ValueError: If insufficient questions or course not found
    """
    # Get course to determine total_questions
    course = db.query(Course).filter(Course.course_id == str(course_id)).first()

    if not course:
        raise ValueError(f"Course {course_id} not found")

    total_questions_needed = course.total_questions or 120

    # Select questions
    questions = select_questions_for_mock_exam(
        db=db,
        course_id=course_id,
        user_id=user_id,
        total_questions=total_questions_needed
    )

    # Create session
    session = LearningSession(
        user_id=str(user_id),
        course_id=str(course_id),
        session_type='mock_exam',
        total_questions=len(questions),
        correct_answers=0,
        is_completed=False,
        started_at=datetime.now(timezone.utc)
    )

    db.add(session)
    db.flush()

    # Create question attempts (pre-allocated but not answered yet)
    for idx, question in enumerate(questions):
        attempt = QuestionAttempt(
            user_id=str(user_id),
            question_id=question.question_id,
            session_id=session.session_id,
            selected_choice_id=None,  # Not answered yet
            is_correct=False,  # Default, will be updated on answer
            created_at=datetime.now(timezone.utc)
        )
        db.add(attempt)

    db.commit()
    db.refresh(session)

    return session


def calculate_mock_exam_results(
    db: Session,
    session_id: UUID
) -> Dict:
    """
    Calculate comprehensive mock exam results.

    Returns detailed analytics including:
    - Overall score
    - Pass/fail status
    - Performance by KA
    - Time spent
    - Comparison to passing score

    Args:
        db: Database session
        session_id: Session ID

    Returns:
        Dict with comprehensive results

    Raises:
        ValueError: If session not found or not completed
    """
    # Get session
    session = db.query(LearningSession).filter(
        LearningSession.session_id == str(session_id)
    ).first()

    if not session:
        raise ValueError(f"Session {session_id} not found")

    if not session.is_completed:
        raise ValueError("Session is not completed yet")

    # Get course for passing score
    course = db.query(Course).filter(Course.course_id == session.course_id).first()
    passing_score = float(course.passing_score_percentage) if course else 70.0

    # Get all attempts for this session
    attempts = db.query(QuestionAttempt).filter(
        QuestionAttempt.session_id == str(session_id)
    ).all()

    # Calculate overall score
    total = len(attempts)
    correct = sum(1 for a in attempts if a.is_correct)
    score_percentage = (correct / total * 100.0) if total > 0 else 0.0
    passed = score_percentage >= passing_score

    # Calculate performance by KA
    ka_performance = {}

    for attempt in attempts:
        if attempt.question and attempt.question.ka_id:
            ka_id = attempt.question.ka_id

            if ka_id not in ka_performance:
                ka = attempt.question.knowledge_area
                ka_performance[ka_id] = {
                    "ka_id": ka_id,
                    "ka_code": ka.ka_code if ka else None,
                    "ka_name": ka.ka_name if ka else None,
                    "weight_percentage": float(ka.weight_percentage) if ka else 0,
                    "total_questions": 0,
                    "correct_answers": 0,
                    "score_percentage": 0.0
                }

            ka_performance[ka_id]["total_questions"] += 1
            if attempt.is_correct:
                ka_performance[ka_id]["correct_answers"] += 1

    # Calculate KA percentages
    for ka_id, data in ka_performance.items():
        if data["total_questions"] > 0:
            data["score_percentage"] = (
                data["correct_answers"] / data["total_questions"] * 100.0
            )

    # Sort by performance (weakest first)
    ka_list = sorted(
        ka_performance.values(),
        key=lambda x: x["score_percentage"]
    )

    # Calculate time statistics
    total_time = session.duration_seconds or 0
    avg_time_per_question = (total_time / total) if total > 0 else 0

    # Identify strengths and weaknesses
    strengths = [ka for ka in ka_list if ka["score_percentage"] >= 80.0]
    weaknesses = [ka for ka in ka_list if ka["score_percentage"] < 60.0]

    return {
        "session_id": str(session_id),
        "exam_type": "CBAP Mock Exam" if course else "Mock Exam",
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,

        # Overall Performance
        "total_questions": total,
        "correct_answers": correct,
        "incorrect_answers": total - correct,
        "score_percentage": round(score_percentage, 2),
        "passing_score": passing_score,
        "passed": passed,
        "margin": round(score_percentage - passing_score, 2),

        # Time Statistics
        "duration_seconds": total_time,
        "duration_minutes": total_time // 60,
        "avg_seconds_per_question": round(avg_time_per_question, 1),

        # KA Performance
        "performance_by_ka": ka_list,
        "strongest_areas": strengths,
        "weakest_areas": weaknesses,

        # Recommendations
        "next_steps": generate_next_steps(passed, weaknesses, score_percentage, passing_score)
    }


def generate_next_steps(
    passed: bool,
    weaknesses: List[Dict],
    score: float,
    passing_score: float
) -> List[str]:
    """
    Generate personalized next steps based on exam performance.

    Args:
        passed: Whether user passed the exam
        weaknesses: List of weak KAs
        score: User's score percentage
        passing_score: Required passing score

    Returns:
        List of recommended next steps
    """
    steps = []

    if passed:
        if score >= passing_score + 10:
            steps.append("Excellent performance! You're well-prepared for the exam.")
            steps.append("Take another mock exam to maintain consistency.")
        else:
            steps.append("Good job passing! Focus on weak areas to improve your margin.")

    else:
        gap = passing_score - score
        if gap > 20:
            steps.append(f"You need {gap:.1f}% more to pass. Focus on fundamentals first.")
        else:
            steps.append(f"You're close! Focus on your weakest areas to gain {gap:.1f}%.")

    # Add specific KA recommendations
    if weaknesses:
        weak_ka_names = [ka["ka_name"] for ka in weaknesses[:2]]
        steps.append(f"Priority areas to improve: {', '.join(weak_ka_names)}")
        steps.append("Review content chunks and practice questions for these KAs.")

    # Always recommend practice
    if not passed:
        steps.append("Take focused practice sessions on weak KAs.")
        steps.append("Review spaced repetition cards to reinforce learning.")

    return steps
