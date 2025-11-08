"""
Spaced Repetition Pydantic schemas.

Decision #31: Spaced repetition essential for MVP
Decision #32: SM-2 algorithm selected

Implements SuperMemo-2 algorithm for optimal long-term retention.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema


class SpacedRepetitionCardResponse(BaseModel):
    """
    Spaced repetition card with question details.
    """
    card_id: UUID
    question_id: UUID
    question_text: str
    ka_code: str
    ka_name: str

    # SM-2 parameters
    easiness_factor: Decimal  # 1.30-2.50
    interval_days: int
    repetition_count: int

    # Review scheduling
    last_reviewed_at: Optional[datetime]
    next_review_at: datetime
    is_due: bool

    # Performance history
    total_reviews: int
    successful_reviews: int
    success_rate: float  # 0-100


class DueCardsResponse(BaseSchema):
    """
    List of cards due for review.
    """
    cards: List[SpacedRepetitionCardResponse]
    total_due: int
    total_overdue: int  # Cards past due date
    estimated_minutes: int  # Time to complete all due cards


class ReviewAnswerRequest(BaseModel):
    """
    Answer submission for a spaced repetition card.

    SM-2 Quality Rating:
    - 5: Perfect recall
    - 4: Correct with hesitation
    - 3: Correct with difficulty (minimum passing)
    - 2: Incorrect but remembered on seeing answer
    - 1: Incorrect but familiar
    - 0: Complete blackout (no memory)
    """
    quality: int = Field(..., ge=0, le=5, description="SM-2 quality rating (0-5)")
    time_spent_seconds: int = Field(..., gt=0, description="Time spent on question")

    @field_validator('quality')
    @classmethod
    def validate_quality(cls, v):
        """Ensure quality is in valid SM-2 range."""
        if not 0 <= v <= 5:
            raise ValueError("Quality must be between 0 and 5")
        return v


class SM2UpdatedParameters(BaseModel):
    """
    Updated SM-2 parameters after review.
    """
    easiness_factor: Decimal
    interval_days: int
    repetition_count: int
    next_review_at: datetime


class ReviewAnswerResponse(BaseSchema):
    """
    Response after answering a spaced repetition card.
    """
    card_id: UUID
    question_id: UUID
    is_correct: bool  # quality >= 3

    # Previous state
    previous_ef: Decimal
    previous_interval: int

    # Updated state
    updated: SM2UpdatedParameters

    # Feedback
    quality_rating: int
    feedback_message: str  # Personalized based on quality


class ReviewStatsResponse(BaseSchema):
    """
    Overall spaced repetition statistics for user.
    """
    user_id: UUID
    total_cards: int
    cards_due_today: int
    cards_due_this_week: int
    cards_mastered: int  # EF >= 2.5 and interval >= 30 days

    # Performance metrics
    total_reviews_completed: int
    average_success_rate: float  # 0-100
    current_streak_days: int  # Consecutive days with reviews

    # Recommendations
    daily_review_target: int  # Recommended reviews per day
    estimated_daily_minutes: int
