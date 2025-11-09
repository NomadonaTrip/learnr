"""
Pydantic schemas for Admin Dashboard API.

These schemas are used exclusively for admin-only endpoints.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID


# ============================================================================
# User Management Schemas
# ============================================================================

class AdminUserListItem(BaseModel):
    """User list item for admin dashboard."""
    user_id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    """Response for GET /v1/admin/users."""
    users: List[AdminUserListItem]
    total: int
    page: int
    per_page: int
    total_pages: int


# ============================================================================
# Metrics & Analytics Schemas
# ============================================================================

class MetricsUsers(BaseModel):
    """User metrics for admin dashboard."""
    total: int
    active: int
    new_this_month: int


class MetricsRevenue(BaseModel):
    """Revenue metrics for admin dashboard."""
    mrr: Decimal = Field(description="Monthly Recurring Revenue")
    arr: Decimal = Field(description="Annual Recurring Revenue")
    total_revenue_this_month: Decimal


class MetricsEngagement(BaseModel):
    """Engagement metrics for admin dashboard."""
    daily_active_users: int
    avg_session_duration_minutes: int
    questions_answered_today: int


class MetricsCourses(BaseModel):
    """Course metrics for admin dashboard."""
    total_courses: int
    active_courses: int
    total_questions: int


class AdminMetricsOverviewResponse(BaseModel):
    """Response for GET /v1/admin/metrics/overview."""
    users: MetricsUsers
    revenue: MetricsRevenue
    engagement: MetricsEngagement
    courses: MetricsCourses


# ============================================================================
# Course Management Schemas
# ============================================================================

class AdminCourseListItem(BaseModel):
    """Course list item for admin dashboard."""
    course_id: UUID
    course_code: str
    course_name: str
    status: str
    wizard_completed: bool
    total_questions: int = 0
    total_chunks: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class AdminCourseListResponse(BaseModel):
    """Response for GET /v1/admin/courses."""
    courses: List[AdminCourseListItem]


class CreateCourseRequest(BaseModel):
    """Request for POST /v1/admin/courses."""
    course_code: str = Field(max_length=20, description="Unique course code (e.g., 'CBAP', 'PSM1')")
    course_name: str = Field(max_length=255, description="Full course name")
    version: str = Field(max_length=20, description="Version (e.g., 'v3', 'v2020')")
    description: Optional[str] = None
    passing_score_percentage: int = Field(ge=0, le=100, description="Passing score (0-100)")
    exam_duration_minutes: Optional[int] = Field(None, ge=1, description="Exam duration in minutes")
    total_questions: Optional[int] = Field(None, ge=1, description="Total questions in exam")
    min_questions_required: int = Field(default=200, description="Minimum questions before publish")
    min_chunks_required: int = Field(default=50, description="Minimum content chunks before publish")


class CreateCourseResponse(BaseModel):
    """Response for POST /v1/admin/courses."""
    course_id: UUID
    course_code: str
    status: str
    wizard_completed: bool
    auto_delete_at: Optional[datetime] = Field(description="Auto-deletion date for abandoned drafts")


class KnowledgeAreaRequest(BaseModel):
    """Single knowledge area in bulk creation request."""
    ka_code: str = Field(max_length=20)
    ka_name: str = Field(max_length=255)
    ka_number: int = Field(ge=1, description="Display order")
    weight_percentage: Decimal = Field(ge=0, le=100, description="Weight in exam (must sum to 100%)")
    description: Optional[str] = None


class CreateKnowledgeAreasRequest(BaseModel):
    """Request for POST /v1/admin/courses/{course_id}/knowledge-areas."""
    knowledge_areas: List[KnowledgeAreaRequest]

    @field_validator('knowledge_areas')
    @classmethod
    def validate_weights(cls, v):
        """Validate that weights sum to 100%."""
        total = sum(ka.weight_percentage for ka in v)
        if not (99.99 <= total <= 100.01):  # Allow 0.01% tolerance
            raise ValueError(f"Knowledge area weights must sum to 100%, got {total}")
        return v


class KnowledgeAreaResponse(BaseModel):
    """Knowledge area in response."""
    ka_id: UUID
    ka_code: str
    ka_name: str
    ka_number: int
    weight_percentage: Decimal

    class Config:
        from_attributes = True


class CreateKnowledgeAreasResponse(BaseModel):
    """Response for POST /v1/admin/courses/{course_id}/knowledge-areas."""
    course_id: UUID
    knowledge_areas: List[KnowledgeAreaResponse]
    total_weight: Decimal
    validation_passed: bool


class PublishCourseValidation(BaseModel):
    """Validation status for course publishing."""
    min_questions_met: bool
    min_chunks_met: bool
    ka_weights_valid: bool
    ready_for_learners: bool


class PublishCourseResponse(BaseModel):
    """Response for POST /v1/admin/courses/{course_id}/publish."""
    course_id: UUID
    status: str
    wizard_completed: bool
    validation: PublishCourseValidation


# ============================================================================
# Bulk Question Import Schemas
# ============================================================================

class BulkAnswerChoiceRequest(BaseModel):
    """Answer choice in bulk import."""
    choice_text: str = Field(min_length=1, max_length=1000)
    is_correct: bool
    choice_order: int = Field(ge=1, le=6, description="Display order (1-6)")
    explanation: Optional[str] = Field(None, max_length=1000)


class BulkQuestionRequest(BaseModel):
    """Single question in bulk import."""
    ka_code: str = Field(max_length=20, description="Knowledge area code")
    domain_code: Optional[str] = Field(None, max_length=20, description="Optional domain code")
    question_text: str = Field(min_length=10, max_length=5000)
    question_type: str = Field(default="multiple_choice", description="'multiple_choice' or 'true_false'")
    difficulty: Decimal = Field(ge=0, le=1, description="Difficulty (0.0-1.0)")
    source: str = Field(default="vendor", description="'vendor', 'generated', or 'custom'")
    answer_choices: List[BulkAnswerChoiceRequest] = Field(min_items=2, max_items=6)

    @field_validator('question_type')
    @classmethod
    def validate_question_type(cls, v):
        if v not in ('multiple_choice', 'true_false'):
            raise ValueError("question_type must be 'multiple_choice' or 'true_false'")
        return v

    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        if v not in ('vendor', 'generated', 'custom'):
            raise ValueError("source must be 'vendor', 'generated', or 'custom'")
        return v

    @field_validator('answer_choices')
    @classmethod
    def validate_answer_choices(cls, v):
        """Ensure exactly one correct answer."""
        correct_count = sum(1 for choice in v if choice.is_correct)
        if correct_count != 1:
            raise ValueError(f"Exactly one answer must be correct, got {correct_count}")
        return v


class BulkQuestionImportRequest(BaseModel):
    """Request for POST /v1/admin/courses/{course_id}/questions/bulk."""
    questions: List[BulkQuestionRequest] = Field(min_items=1, max_items=500)


class BulkQuestionImportResponse(BaseModel):
    """Response for POST /v1/admin/courses/{course_id}/questions/bulk."""
    course_id: UUID
    questions_imported: int
    questions_failed: int
    validation_summary: Dict
