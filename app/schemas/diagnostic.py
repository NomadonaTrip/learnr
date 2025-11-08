"""
Diagnostic Assessment Pydantic schemas.

Decision #32: Diagnostic assessment (24 questions, 4 per KA).
User Flow #2: Diagnostic assessment to establish baseline competency.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema


class DiagnosticStartRequest(BaseModel):
    """
    Start a diagnostic assessment.

    The system will automatically select 24 questions (4 per KA).
    """
    course_id: UUID


class DiagnosticStartResponse(BaseSchema):
    """
    Diagnostic session started response.

    Contains session_id for tracking progress through the diagnostic.
    """
    session_id: UUID
    course_id: UUID
    course_name: str
    total_questions: int
    questions_per_ka: int
    status: str  # 'in_progress'
    started_at: datetime


class DiagnosticQuestionResponse(BaseSchema):
    """
    Next question in diagnostic assessment.

    Does NOT include correct answer (hidden until submission).
    """
    question_id: UUID
    question_number: int  # 1-24 (sequential position in diagnostic)
    total_questions: int  # Always 24
    ka_id: UUID
    ka_name: str
    question_text: str
    question_type: str  # 'multiple_choice' or 'true_false'
    answer_choices: List[dict]  # [{"choice_id": UUID, "choice_text": str, "choice_order": int}]


class DiagnosticAnswerSubmit(BaseModel):
    """
    Submit answer for current diagnostic question.
    """
    session_id: UUID
    question_id: UUID
    selected_choice_id: UUID
    time_spent_seconds: Optional[int] = Field(None, ge=0)


class DiagnosticAnswerResponse(BaseSchema):
    """
    Response after submitting diagnostic answer.

    Shows if answer was correct and provides explanation.
    """
    attempt_id: UUID
    is_correct: bool
    correct_choice_id: UUID
    explanation: Optional[str]
    question_number: int
    total_questions: int
    questions_remaining: int
    attempted_at: datetime


class DiagnosticKAResult(BaseModel):
    """
    Diagnostic result for a single Knowledge Area.
    """
    ka_id: UUID
    ka_code: str
    ka_name: str
    ka_weight_percentage: Decimal
    questions_attempted: int
    questions_correct: int
    accuracy_percentage: float
    competency_score: Decimal  # 0.00 - 1.00
    status: str  # 'below_target', 'on_track', 'above_target'


class DiagnosticResultsResponse(BaseSchema):
    """
    Complete diagnostic results.

    Decision #22: Simplified IRT approach for MVP (correct/total per KA).
    Shows per-KA competency and overall readiness.
    """
    session_id: UUID
    user_id: UUID
    course_id: UUID
    course_name: str

    # Overall metrics
    total_questions: int
    total_correct: int
    overall_accuracy: float  # 0-100
    overall_competency: Decimal  # 0.00-1.00 (weighted average across KAs)

    # Per-KA breakdown
    ka_results: List[DiagnosticKAResult]

    # Session timing
    started_at: datetime
    completed_at: datetime
    duration_minutes: int

    # Recommendations
    weakest_ka_id: UUID
    weakest_ka_name: str
    recommendation: str  # Guidance based on results


class DiagnosticProgressResponse(BaseModel):
    """
    Current progress in diagnostic assessment.

    Used to check status or resume incomplete diagnostic.
    """
    session_id: UUID
    session_type: str  # 'diagnostic'
    is_completed: bool
    questions_answered: int
    total_questions: int
    progress_percentage: float  # 0-100
    started_at: datetime
