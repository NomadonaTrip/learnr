"""
Spaced Repetition model: SpacedRepetitionCard.

Implements SM-2 algorithm for optimal retention (Decision #31, #32).
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import uuid


class SpacedRepetitionCard(Base):
    """
    Spaced repetition cards for questions user has answered.

    Uses SM-2 algorithm for scheduling reviews.
    Decision #31: SR is essential for MVP, not deferred
    Decision #32: SM-2 algorithm chosen
    """
    __tablename__ = "spaced_repetition_cards"

    # Primary Key
    card_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    question_id = Column(String(36), ForeignKey('questions.question_id', ondelete='CASCADE'), nullable=False)

    # SM-2 Algorithm Fields
    easiness_factor = Column(DECIMAL(4, 2), nullable=False, default=2.50)  # 1.30 to 2.50+
    repetition_count = Column(Integer, nullable=False, default=0)  # Number of successful reviews
    interval_days = Column(Integer, nullable=False, default=1)  # Days until next review

    # Review Scheduling
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=False)  # When card is due for review
    is_due = Column(Boolean, nullable=False, default=True)  # Computed: next_review_at <= now()

    # Performance History
    total_reviews = Column(Integer, nullable=False, default=0)  # Total times reviewed
    successful_reviews = Column(Integer, nullable=False, default=0)  # Times answered correctly
    last_quality_rating = Column(Integer, nullable=True)  # Last SM-2 quality (0-5)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="sr_cards")
    question = relationship("Question", back_populates="sr_cards")

    def __repr__(self):
        return f"<SpacedRepetitionCard {self.card_id} - Next review: {self.next_review_at}>"
