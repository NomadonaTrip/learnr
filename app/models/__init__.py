"""
Models package initialization.

Imports all models so they're registered with SQLAlchemy Base.metadata.
This is crucial for Alembic to discover all tables during migrations.
"""

# Import Base and get_db first
from app.models.database import Base, get_db, init_db

# Import all models (order matters for foreign key relationships)
from app.models.user import User, UserProfile
from app.models.course import Course, KnowledgeArea, Domain
from app.models.question import Question, AnswerChoice
from app.models.content import ContentChunk, ContentFeedback, ContentEfficacy
from app.models.learning import Session, QuestionAttempt, UserCompetency, ReadingConsumed
from app.models.spaced_repetition import SpacedRepetitionCard
from app.models.financial import (
    SubscriptionPlan,
    Subscription,
    Payment,
    Refund,
    Chargeback,
    PaymentMethod,
    Invoice,
    RevenueEvent
)
from app.models.security import SecurityLog, RateLimitEntry

# Export all models for easy importing
__all__ = [
    # Database utilities
    "Base",
    "get_db",
    "init_db",

    # User models
    "User",
    "UserProfile",

    # Course models
    "Course",
    "KnowledgeArea",
    "Domain",

    # Question models
    "Question",
    "AnswerChoice",

    # Content models
    "ContentChunk",
    "ContentFeedback",
    "ContentEfficacy",

    # Learning models
    "Session",
    "QuestionAttempt",
    "UserCompetency",
    "ReadingConsumed",

    # Spaced Repetition
    "SpacedRepetitionCard",

    # Financial models
    "SubscriptionPlan",
    "Subscription",
    "Payment",
    "Refund",
    "Chargeback",
    "PaymentMethod",
    "Invoice",
    "RevenueEvent",

    # Security models
    "SecurityLog",
    "RateLimitEntry",
]
