"""
Question models: Question and AnswerChoice.

Includes IRT parameters for adaptive learning (Decision #64).
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, DECIMAL, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import uuid


class Question(Base):
    """
    Multiple-choice questions for practice and assessment.

    Decisions: #22 (Vendor questions), #64 (1PL IRT with 2PL upgrade path)
    """
    __tablename__ = "questions"

    # Primary Key
    question_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    course_id = Column(String(36), ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    ka_id = Column(String(36), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)
    domain_id = Column(String(36), ForeignKey('domains.domain_id', ondelete='SET NULL'), nullable=True)

    # Question Content
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), nullable=False, default='multiple_choice')  # 'multiple_choice' | 'true_false'

    # IRT Parameters (Decision #64)
    difficulty = Column(DECIMAL(5, 2), nullable=False)  # 0.00 to 1.00 (1PL IRT)
    discrimination = Column(DECIMAL(5, 2), nullable=True)  # NULL for MVP, populated for 2PL upgrade

    # Metadata
    source = Column(String(50), nullable=False, default='vendor')  # 'vendor' | 'generated' | 'custom'
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="questions")
    knowledge_area = relationship("KnowledgeArea", back_populates="questions")
    domain = relationship("Domain", back_populates="questions")
    answer_choices = relationship("AnswerChoice", back_populates="question", cascade="all, delete-orphan", order_by="AnswerChoice.choice_order")
    attempts = relationship("QuestionAttempt", back_populates="question", cascade="all, delete-orphan")
    sr_cards = relationship("SpacedRepetitionCard", back_populates="question", cascade="all, delete-orphan")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("difficulty >= 0.00 AND difficulty <= 1.00", name='chk_difficulty_range'),
        CheckConstraint("discrimination IS NULL OR (discrimination >= 0.00 AND discrimination <= 3.00)", name='chk_discrimination_range'),
        CheckConstraint("question_type IN ('multiple_choice', 'true_false')", name='chk_question_type'),
        CheckConstraint("source IN ('vendor', 'generated', 'custom')", name='chk_source'),
    )

    def __repr__(self):
        return f"<Question {self.question_id} - {self.question_text[:50]}...>"


class AnswerChoice(Base):
    """
    Answer choices for multiple-choice questions.
    """
    __tablename__ = "answer_choices"

    # Primary Key
    choice_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key
    question_id = Column(String(36), ForeignKey('questions.question_id', ondelete='CASCADE'), nullable=False)

    # Choice Content
    choice_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    choice_order = Column(Integer, nullable=False)  # Display order (A, B, C, D)

    # Explanation
    explanation = Column(Text, nullable=True)  # Why this answer is correct/incorrect

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    question = relationship("Question", back_populates="answer_choices")

    @property
    def choice_letter(self):
        """Convert choice_order to letter (1=A, 2=B, 3=C, 4=D)."""
        if self.choice_order is None:
            return None
        # Convert 1-based order to letter
        letter_map = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F'}
        return letter_map.get(self.choice_order, chr(64 + self.choice_order))

    def __repr__(self):
        return f"<AnswerChoice {self.choice_id} - {'✓' if self.is_correct else '✗'} {self.choice_text[:30]}...>"
