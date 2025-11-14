"""
Learning progress Pydantic schemas.

Includes competency tracking, sessions, and spaced repetition (Decision #8, #31, #32).
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema, TimestampMixin


class UserCompetencyResponse(BaseSchema, TimestampMixin):
    """
    User competency response.

    Decision #8: Competency-based success criteria.
    Decision #18: IRT-based competency estimation.
    """
    competency_id: UUID
    user_id: UUID
    ka_id: UUID
    competency_score: Decimal = Field(..., ge=0, le=1)
    confidence_interval: Optional[Decimal]
    questions_attempted: int
    questions_correct: int
    accuracy_percentage: float  # Computed property
    last_practiced_at: Optional[datetime]


class UserCompetencyWithKAResponse(UserCompetencyResponse):
    """
    User competency response with knowledge area details.

    Used for dashboard display.
    """
    ka_code: str
    ka_name: str
    ka_weight_percentage: Decimal


class SessionCreate(BaseModel):
    """
    Session creation.

    Decision #12: Daily practice sessions.
    """
    session_type: str = Field(..., pattern="^(diagnostic|practice|review|mock_exam)$")


class SessionResponse(BaseSchema):
    """
    Session response.
    """
    session_id: UUID
    user_id: UUID
    session_type: str
    total_questions: int
    correct_answers: int
    accuracy_percentage: float  # Computed property
    duration_minutes: Optional[int]
    is_completed: bool
    started_at: datetime
    completed_at: Optional[datetime]


class SessionCompleteRequest(BaseModel):
    """
    Mark session as complete.

    Optionally provide final duration.
    """
    duration_minutes: Optional[int] = Field(None, gt=0)


class DashboardResponse(BaseModel):
    """
    Dashboard data response.

    Decision #13: Progress dashboard design.
    """
    user_id: UUID
    course_id: UUID
    course_name: str
    exam_date: Optional[datetime]
    days_until_exam: Optional[int]
    
    # Competency breakdown
    competencies: List[UserCompetencyWithKAResponse]
    overall_competency_score: Decimal  # Weighted average across all KAs
    
    # Progress metrics
    reviews_due_count: int
    exam_readiness_percentage: float  # 0-100
    total_questions_attempted: int
    overall_accuracy: float  # 0-100
    
    # Streak tracking (Decision #7: Gamification)
    current_streak_days: int
    longest_streak_days: int


class ReadingConsumedCreate(BaseModel):
    """
    Submit reading consumption.

    Decision #36: Reading recommendations.
    """
    chunk_id: UUID
    time_spent_seconds: Optional[int] = Field(None, ge=0)
    completed: bool = True
    was_helpful: Optional[bool] = None
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5)


class ReadingConsumedResponse(BaseSchema):
    """
    Reading consumption response.
    """
    reading_id: UUID
    user_id: UUID
    chunk_id: UUID
    read_at: datetime
    time_spent_seconds: Optional[int]
    completed: bool
    was_helpful: Optional[bool]
    difficulty_rating: Optional[int]
    created_at: datetime


class ReadingRecommendationResponse(BaseModel):
    """
    Recommended reading content.

    Decision #36: Reading recommendations based on weak KAs.
    """
    chunk_id: UUID
    content_title: Optional[str]
    content_text: str
    ka_id: UUID
    ka_name: str
    domain_id: Optional[UUID]
    domain_name: Optional[str]
    difficulty_estimate: Optional[Decimal]
    estimated_read_time_minutes: Optional[int]
    relevance_score: float  # 0-1, based on competency gap
    reason: str  # Why recommended (e.g., "Low competency in Requirements Elicitation")


class SpacedRepetitionCardResponse(BaseSchema, TimestampMixin):
    """
    Spaced repetition card response.

    Decision #31: Spaced repetition essential for MVP.
    Decision #32: SM-2 algorithm.
    """
    card_id: UUID
    user_id: UUID
    question_id: UUID
    easiness_factor: Decimal
    interval_days: int
    repetitions: int
    last_reviewed_at: Optional[datetime]
    next_review_at: datetime
    is_due: bool


class SpacedRepetitionReviewRequest(BaseModel):
    """
    Submit spaced repetition review.

    User rates quality of recall (0-5) after seeing question.
    """
    card_id: UUID
    quality: int = Field(..., ge=0, le=5)  # SM-2 quality rating
    time_spent_seconds: Optional[int] = Field(None, ge=0)


class SpacedRepetitionReviewResponse(BaseModel):
    """
    Spaced repetition review result.

    Shows updated card schedule after review.
    """
    card_id: UUID
    new_easiness_factor: Decimal
    new_interval_days: int
    new_repetitions: int
    next_review_at: datetime
    is_due: bool


class DueCardsResponse(BaseModel):
    """
    Due spaced repetition cards for today.

    Decision #13: Show due cards count in dashboard.
    """
    due_count: int
    cards: List[SpacedRepetitionCardResponse]


# ==================== Mock Exam Schemas ====================


class MockExamCreateRequest(BaseModel):
    """
    Request to create a mock exam session.

    Mock exams simulate actual certification exam conditions with:
    - Questions distributed by KA weights
    - Full exam length (e.g., 120 questions for CBAP)
    - Randomized question order
    """
    # No parameters needed - uses user's course from profile


class MockExamResponse(BaseModel):
    """
    Mock exam session created response.

    Returns session details to begin the exam.
    """
    session_id: UUID
    session_type: str
    total_questions: int
    exam_duration_minutes: int  # Expected duration
    started_at: datetime
    instructions: str


class KAPerformance(BaseModel):
    """
    Performance metrics for a single knowledge area.
    """
    ka_id: UUID
    ka_code: Optional[str]
    ka_name: Optional[str]
    weight_percentage: float
    total_questions: int
    correct_answers: int
    score_percentage: float


class MockExamResultsResponse(BaseModel):
    """
    Comprehensive mock exam results with analytics.

    Includes overall score, KA breakdown, and personalized recommendations.
    """
    session_id: UUID
    exam_type: str
    completed_at: Optional[str]

    # Overall Performance
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    score_percentage: float
    passing_score: float
    passed: bool
    margin: float  # Difference from passing score (positive if passed)

    # Time Statistics
    duration_seconds: int
    duration_minutes: int
    avg_seconds_per_question: float

    # KA Performance (sorted by score, weakest first)
    performance_by_ka: List[KAPerformance]
    strongest_areas: List[KAPerformance]
    weakest_areas: List[KAPerformance]

    # Recommendations
    next_steps: List[str]
