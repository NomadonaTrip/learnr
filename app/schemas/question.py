"""
Question and AnswerChoice Pydantic schemas.

Includes IRT parameters and question attempt tracking (Decision #64).
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema, TimestampMixin


class AnswerChoiceBase(BaseModel):
    """
    Base answer choice fields.
    """
    choice_letter: str = Field(..., pattern="^[A-D]$")
    choice_text: str = Field(..., min_length=1)
    is_correct: bool
    explanation: Optional[str] = None


class AnswerChoiceCreate(AnswerChoiceBase):
    """
    Answer choice creation (used within QuestionCreate).
    """
    pass


class AnswerChoiceResponse(BaseSchema):
    """
    Answer choice response (includes created_at only, no updated_at).
    """
    choice_id: UUID
    question_id: UUID
    choice_letter: str
    choice_text: str
    is_correct: bool
    explanation: Optional[str]
    created_at: datetime


class AnswerChoicePublicResponse(BaseModel):
    """
    Answer choice response WITHOUT is_correct field.

    Used when showing questions to learners before they answer.
    """
    choice_id: UUID
    choice_letter: str
    choice_text: str


class QuestionBase(BaseModel):
    """
    Base question fields.
    """
    question_text: str = Field(..., min_length=10)
    question_type: str = Field(default="multiple_choice", pattern="^(multiple_choice|true_false)$")
    difficulty: Decimal = Field(..., ge=0, le=1)
    source: str = Field(default="vendor", pattern="^(vendor|generated|custom)$")


class QuestionCreate(QuestionBase):
    """
    Question creation (includes answer choices).

    Decision #64: 1PL IRT (discrimination NULL for MVP, reserved for 2PL upgrade).
    """
    course_id: UUID
    ka_id: UUID
    domain_id: Optional[UUID] = None
    answer_choices: List[AnswerChoiceBase] = Field(..., min_length=2, max_length=4)

    @field_validator('answer_choices')
    @classmethod
    def validate_answer_choices(cls, v: List[AnswerChoiceBase]) -> List[AnswerChoiceBase]:
        """Ensure exactly one correct answer."""
        correct_count = sum(1 for choice in v if choice.is_correct)
        if correct_count != 1:
            raise ValueError('Must have exactly one correct answer')
        
        # Ensure unique choice letters
        letters = [choice.choice_letter for choice in v]
        if len(letters) != len(set(letters)):
            raise ValueError('Choice letters must be unique')
        
        return v


class QuestionBulkCreate(BaseModel):
    """
    Bulk question import (wizard step 3).

    Used for CSV uploads when creating new courses.
    """
    course_id: UUID
    questions: List[QuestionCreate] = Field(..., min_length=1)


class QuestionUpdate(BaseModel):
    """
    Question update (all fields optional).
    """
    question_text: Optional[str] = Field(None, min_length=10)
    difficulty: Optional[Decimal] = Field(None, ge=0, le=1)
    discrimination: Optional[Decimal] = Field(None, ge=0, le=3)  # For 2PL upgrade
    is_active: Optional[bool] = None


class QuestionResponse(BaseSchema, TimestampMixin):
    """
    Question response (includes correct answer - for admin/review use).
    """
    question_id: UUID
    course_id: UUID
    ka_id: UUID
    domain_id: Optional[UUID]
    question_text: str
    question_type: str
    difficulty: Decimal
    discrimination: Optional[Decimal]  # NULL for MVP, Decision #64
    source: str
    is_active: bool
    answer_choices: List[AnswerChoiceResponse]


class QuestionPublicResponse(BaseSchema):
    """
    Question response WITHOUT correct answers (for learner practice sessions).

    Only shows question_id, text, and choices without is_correct field.
    """
    question_id: UUID
    course_id: UUID
    ka_id: UUID
    domain_id: Optional[UUID]
    question_text: str
    question_type: str
    created_at: datetime
    answer_choices: List[AnswerChoicePublicResponse]


class QuestionAttemptCreate(BaseModel):
    """
    Question attempt creation (learner submits answer).
    """
    question_id: UUID
    session_id: Optional[UUID] = None
    selected_choice_id: UUID
    time_spent_seconds: Optional[int] = Field(None, ge=0)


class QuestionAttemptResponse(BaseSchema):
    """
    Question attempt response (includes correctness).

    Returned immediately after submission to show if answer was correct.
    """
    attempt_id: UUID
    user_id: UUID
    question_id: UUID
    session_id: Optional[UUID]
    selected_choice_id: UUID
    is_correct: bool
    time_spent_seconds: Optional[int]
    competency_at_attempt: Optional[Decimal]  # User's competency when they answered
    attempted_at: datetime


class QuestionAttemptWithExplanationResponse(QuestionAttemptResponse):
    """
    Question attempt response with full explanation.

    Includes the correct answer and explanation after submission.
    """
    correct_choice_id: UUID
    correct_choice_letter: str
    explanation: Optional[str]
    question_text: str
    all_choices: List[AnswerChoiceResponse]
