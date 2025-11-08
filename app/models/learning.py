"""
Learning models: Session, QuestionAttempt, UserCompetency, ReadingConsumed.

Core models for adaptive learning and progress tracking.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, DECIMAL, CheckConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import uuid


class Session(Base):
    """
    Learning sessions (diagnostic, practice, mock exam).

    Tracks user study sessions and their outcomes.
    """
    __tablename__ = "sessions"

    # Primary Key
    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    course_id = Column(String(36), ForeignKey('courses.course_id'), nullable=False)

    # Session Type
    session_type = Column(String(20), nullable=False)  # 'diagnostic' | 'practice' | 'mock_exam' | 'review'

    # Session Metadata
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Session Outcomes
    total_questions = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    score_percentage = Column(DECIMAL(5, 2), nullable=True)

    # Status
    is_completed = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")
    course = relationship("Course")
    question_attempts = relationship("QuestionAttempt", back_populates="session", cascade="all, delete-orphan")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("session_type IN ('diagnostic', 'practice', 'mock_exam', 'review')", name='chk_session_type'),
    )

    @property
    def duration_minutes(self):
        """Convert duration_seconds to minutes."""
        if self.duration_seconds is None:
            return None
        return self.duration_seconds // 60

    @property
    def accuracy_percentage(self):
        """Calculate accuracy percentage."""
        if self.total_questions == 0:
            return 0.0
        return (self.correct_answers / self.total_questions) * 100.0

    def __repr__(self):
        return f"<Session {self.session_id} - {self.session_type} - User {self.user_id}>"


class QuestionAttempt(Base):
    """
    User attempts at answering questions.

    Tracks all question responses for competency calculation.
    """
    __tablename__ = "question_attempts"

    # Primary Key
    attempt_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    question_id = Column(String(36), ForeignKey('questions.question_id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(36), ForeignKey('sessions.session_id', ondelete='CASCADE'), nullable=False)
    selected_choice_id = Column(String(36), ForeignKey('answer_choices.choice_id'), nullable=True)

    # Attempt Data
    is_correct = Column(Boolean, nullable=False)
    time_spent_seconds = Column(Integer, nullable=True)
    confidence_level = Column(Integer, nullable=True)  # 1-5 scale (optional)

    # Competency at Time of Attempt (for IRT calculations)
    user_competency_at_attempt = Column(DECIMAL(5, 2), nullable=True)
    question_difficulty_at_attempt = Column(DECIMAL(5, 2), nullable=True)

    # Timestamps
    attempted_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="question_attempts")
    question = relationship("Question", back_populates="attempts")
    session = relationship("Session", back_populates="question_attempts")
    selected_choice = relationship("AnswerChoice")

    @property
    def competency_at_attempt(self):
        """Alias for user_competency_at_attempt for schema compatibility."""
        return self.user_competency_at_attempt

    def __repr__(self):
        return f"<QuestionAttempt {self.attempt_id} - {'✓' if self.is_correct else '✗'}>"


class UserCompetency(Base):
    """
    User competency scores per knowledge area.

    Updated in real-time using IRT after each question attempt.
    Decision #3: Adaptive learning as core mechanism
    """
    __tablename__ = "user_competency"

    # Primary Key
    competency_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    ka_id = Column(String(36), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)

    # Competency Score (0.00 to 1.00)
    competency_score = Column(DECIMAL(5, 2), nullable=False, default=0.50)  # Start at 0.50 (neutral)

    # Confidence Metrics
    standard_error = Column(DECIMAL(5, 4), nullable=True)  # Uncertainty in estimate
    attempts_count = Column(Integer, nullable=False, default=0)  # Number of questions answered in this KA

    # Performance Tracking
    correct_count = Column(Integer, nullable=False, default=0)
    incorrect_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    last_updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="competencies")
    knowledge_area = relationship("KnowledgeArea", back_populates="user_competencies")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("competency_score >= 0.00 AND competency_score <= 1.00", name='chk_competency_range'),
    )

    def __repr__(self):
        return f"<UserCompetency {self.competency_id} - Score: {self.competency_score}>"


class ReadingConsumed(Base):
    """
    Tracks which content chunks users have read.

    Used for recommendation filtering and progress tracking.
    """
    __tablename__ = "reading_consumed"

    # Primary Key
    reading_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    chunk_id = Column(String(36), ForeignKey('content_chunks.chunk_id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(36), ForeignKey('sessions.session_id', ondelete='SET NULL'), nullable=True)

    # Reading Metadata
    started_reading_at = Column(DateTime, nullable=False, server_default=func.now())
    finished_reading_at = Column(DateTime, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)

    # Engagement
    was_helpful = Column(Boolean, nullable=True)  # User feedback
    completed = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="reading_consumed")
    content_chunk = relationship("ContentChunk", back_populates="reading_consumed")
    session = relationship("Session")

    def __repr__(self):
        return f"<ReadingConsumed {self.reading_id} - User {self.user_id}>"
