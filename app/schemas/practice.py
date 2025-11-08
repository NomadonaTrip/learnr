"""
Practice Session Pydantic schemas.

Decision #12: Daily practice sessions with adaptive question selection.
User Flow #3: Practice sessions targeting weak knowledge areas.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema


class PracticeStartRequest(BaseModel):
    """
    Start a practice session.

    Decision #3: Adaptive learning - targets weakest KAs by default.
    """
    num_questions: int = Field(default=10, ge=5, le=50, description="Number of questions (5-50)")
    knowledge_area_id: Optional[UUID] = Field(None, description="Focus on specific KA (optional)")
    course_id: UUID = Field(..., description="Course to practice")


class PracticeStartResponse(BaseSchema):
    """
    Practice session started response.
    """
    session_id: UUID
    course_id: UUID
    course_name: str
    total_questions: int
    target_ka_id: Optional[UUID]  # If focusing on specific KA
    target_ka_name: Optional[str]
    session_type: str  # 'practice'
    started_at: datetime


class PracticeQuestionResponse(BaseSchema):
    """
    Next question in practice session.

    Adaptive algorithm selects questions based on user's competency.
    """
    question_id: UUID
    question_number: int  # Sequential position in this session (1-indexed)
    total_questions: int
    ka_id: UUID
    ka_name: str
    ka_current_competency: Decimal  # User's current score in this KA
    question_text: str
    question_type: str  # 'multiple_choice' or 'true_false'
    difficulty: Decimal  # Question difficulty (0.00-1.00)
    answer_choices: List[dict]  # [{"choice_id": UUID, "choice_text": str, "choice_order": int}]


class PracticeSubmitRequest(BaseModel):
    """
    Submit answer for practice question.
    """
    session_id: UUID
    question_id: UUID
    selected_choice_id: UUID
    time_spent_seconds: Optional[int] = Field(None, ge=0)


class PracticeSubmitResponse(BaseSchema):
    """
    Response after submitting practice answer.

    Decision #3: Real-time competency updates after each answer.
    """
    attempt_id: UUID
    is_correct: bool
    correct_choice_id: UUID
    explanation: Optional[str]

    # Progress tracking
    question_number: int
    total_questions: int
    questions_remaining: int

    # Competency update
    ka_id: UUID
    ka_name: str
    previous_competency: Decimal
    new_competency: Decimal
    competency_change: Decimal  # Positive = improved, negative = decreased

    # Session stats
    session_accuracy: float  # Current session accuracy (0-100)
    attempted_at: datetime


class PracticeSessionResponse(BaseSchema):
    """
    Practice session details and current state.
    """
    session_id: UUID
    user_id: UUID
    course_id: UUID
    session_type: str  # 'practice'

    # Configuration
    total_questions: int
    target_ka_id: Optional[UUID]

    # Progress
    questions_answered: int
    correct_answers: int
    accuracy_percentage: float  # 0-100
    is_completed: bool

    # Timing
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]

    # Recent attempts (last 5)
    recent_attempts: List[dict]  # Question IDs and results


class PracticeCompleteRequest(BaseModel):
    """
    Mark practice session as complete.
    """
    session_id: UUID


class PracticeCompleteResponse(BaseSchema):
    """
    Practice session completion summary.
    """
    session_id: UUID
    total_questions: int
    correct_answers: int
    accuracy_percentage: float
    duration_minutes: int

    # Competency improvements
    competencies_improved: List[dict]  # [{"ka_name": str, "before": Decimal, "after": Decimal}]

    # Recommendations
    weakest_ka_name: str
    recommendation: str
    completed_at: datetime


class PracticeHistoryResponse(BaseModel):
    """
    User's practice session history.
    """
    total_sessions: int
    total_questions_practiced: int
    overall_accuracy: float
    sessions: List[PracticeSessionResponse]
