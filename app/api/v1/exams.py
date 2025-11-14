"""
Mock Exam API endpoints.

Handles mock exam creation and results retrieval.
Decision #3: Mock exams use fixed question distribution (not adaptive).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.database import get_db
from app.models.user import User, UserProfile
from app.api.dependencies import get_current_active_user
from app.schemas.learning import (
    MockExamResponse,
    MockExamResultsResponse
)
from app.services.mock_exam import (
    create_mock_exam_session,
    calculate_mock_exam_results
)


router = APIRouter()


@router.post("/mock", response_model=MockExamResponse, status_code=status.HTTP_201_CREATED)
def create_mock_exam(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new mock exam session.

    **What is a Mock Exam?**
    A full-length practice exam that simulates actual certification exam conditions:
    - Questions distributed proportionally by Knowledge Area weights
    - Full exam length (e.g., 120 questions for CBAP)
    - Randomized question order
    - Avoids questions you've seen in your last 50 attempts

    **Exam Structure (CBAP Example):**
    - Business Analysis Planning & Monitoring: 15% (18 questions)
    - Elicitation & Collaboration: 20% (24 questions)
    - Requirements Lifecycle Management: 25% (30 questions)
    - Strategy Analysis: 10% (12 questions)
    - Requirements Analysis & Design: 20% (24 questions)
    - Solution Evaluation: 10% (12 questions)

    **How to Use:**
    1. Create mock exam (this endpoint)
    2. Answer questions via existing session endpoints:
       - GET /v1/sessions/{session_id}/next-question
       - POST /v1/sessions/{session_id}/attempt
    3. Complete exam: POST /v1/sessions/{session_id}/complete
    4. Get results: GET /v1/exams/{session_id}/results

    **Note:** Questions are NOT adaptive - they're selected randomly
    from each KA to simulate real exam conditions.
    """
    # Get user's profile to determine course
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.user_id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile not found. Please complete onboarding first."
        )

    try:
        # Create mock exam session
        session = create_mock_exam_session(
            db=db,
            user_id=current_user.user_id,
            course_id=profile.course_id
        )

        # Get course details for response
        from app.models.course import Course
        course = db.query(Course).filter(
            Course.course_id == str(profile.course_id)
        ).first()

        exam_duration = course.exam_duration_minutes if course else 210

        return MockExamResponse(
            session_id=session.session_id,
            session_type=session.session_type,
            total_questions=session.total_questions,
            exam_duration_minutes=exam_duration,
            started_at=session.started_at,
            instructions=(
                f"This is a full-length mock exam with {session.total_questions} questions. "
                f"You have {exam_duration} minutes to complete it. "
                "Answer all questions to the best of your ability. "
                "Questions are distributed by Knowledge Area to match the actual exam. "
                "Good luck!"
            )
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{session_id}/results", response_model=MockExamResultsResponse)
def get_mock_exam_results(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive mock exam results and analytics.

    **Results Include:**

    **Overall Performance:**
    - Total score percentage
    - Pass/fail status (based on course passing score, typically 70%)
    - Margin above/below passing score
    - Number of correct vs incorrect answers

    **Time Analysis:**
    - Total time spent
    - Average time per question
    - Comparison to allowed exam duration

    **Performance by Knowledge Area:**
    - Score percentage for each KA
    - Questions answered vs total questions per KA
    - Identification of strongest and weakest areas

    **Personalized Recommendations:**
    - Next steps based on performance
    - Priority areas to improve
    - Study recommendations (content, practice, spaced repetition)

    **Requirements:**
    - Session must be completed (all questions answered)
    - User must own the session

    **Use Cases:**
    - Review performance after completing mock exam
    - Identify weak areas for targeted study
    - Track progress across multiple mock exams
    - Determine exam readiness
    """
    # Verify session belongs to user
    from app.models.learning import Session as LearningSession

    session = db.query(LearningSession).filter(
        LearningSession.session_id == str(session_id)
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.user_id != str(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session"
        )

    if session.session_type != 'mock_exam':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for mock exam sessions"
        )

    try:
        # Calculate results
        results = calculate_mock_exam_results(db=db, session_id=session_id)

        return MockExamResultsResponse(**results)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
