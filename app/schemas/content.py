"""
Content chunk Pydantic schemas.

Includes vector embeddings and quality evaluation (Decision #76).
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema, TimestampMixin


class ContentChunkCreate(BaseModel):
    """
    Content chunk creation.

    Decision #76: Content quality evaluation system.
    """
    course_id: UUID
    ka_id: UUID
    domain_id: Optional[UUID] = None
    content_title: str = Field(..., min_length=1, max_length=255)
    content_text: str = Field(..., min_length=10)
    content_type: str = Field(default="babok", pattern="^(babok|generated|custom)$")
    source_document: Optional[str] = None
    source_page: Optional[str] = None
    source_section: Optional[str] = None
    difficulty_level: Optional[str] = Field(None, pattern="^(basic|intermediate|advanced)$")


class ContentChunkBulkCreate(BaseModel):
    """
    Bulk content chunk import (wizard step 4).

    Used for CSV uploads when creating new courses.
    """
    course_id: UUID
    chunks: List[ContentChunkCreate] = Field(..., min_length=1)


class ContentChunkUpdate(BaseModel):
    """
    Content chunk update (admin only).
    """
    content_title: Optional[str] = Field(None, min_length=1, max_length=255)
    content_text: Optional[str] = Field(None, min_length=10)
    source_document: Optional[str] = None
    source_page: Optional[str] = None
    difficulty_level: Optional[str] = Field(None, pattern="^(basic|intermediate|advanced)$")
    review_status: Optional[str] = Field(None, pattern="^(pending|approved|flagged|rejected)$")
    is_active: Optional[bool] = None


class ContentChunkResponse(BaseSchema, TimestampMixin):
    """
    Content chunk response with quality metrics.

    Decision #76: Content quality evaluation.
    """
    chunk_id: UUID
    course_id: UUID
    ka_id: UUID
    domain_id: Optional[UUID]
    content_title: str
    content_text: str
    content_type: str
    source_document: Optional[str]
    source_page: Optional[str]
    source_section: Optional[str]
    token_count: Optional[int]
    difficulty_level: Optional[str]
    expert_reviewed: bool
    review_status: str  # 'pending' | 'approved' | 'flagged' | 'rejected'
    source_verified: bool
    is_active: bool
    # Note: embedding field (Vector) not included in response - too large


class ContentChunkWithMetricsResponse(ContentChunkResponse):
    """
    Content chunk response with quality metrics.

    Includes helpfulness score and efficacy rate.
    """
    helpfulness_score: Optional[float]  # % of users who found it helpful
    efficacy_rate: Optional[float]  # % of users who improved after reading


class ContentFeedbackCreate(BaseModel):
    """
    Submit feedback on content chunk.

    Decision #76: Content quality evaluation system.
    """
    chunk_id: UUID
    was_helpful: bool
    feedback_text: Optional[str] = None


class ContentFeedbackResponse(BaseSchema):
    """
    Content feedback response.
    """
    feedback_id: UUID
    chunk_id: UUID
    user_id: UUID
    was_helpful: bool
    feedback_text: Optional[str]
    created_at: datetime


class ContentEfficacyResponse(BaseSchema):
    """
    Content efficacy metrics.

    Decision #76: Track if reading actually improves performance.
    """
    efficacy_id: UUID
    chunk_id: UUID
    user_id: UUID
    ka_id: UUID
    read_at: datetime
    competency_before: Decimal
    competency_after: Optional[Decimal]
    measured_at: Optional[datetime]
    improved: Optional[bool]
    improvement_amount: Optional[Decimal]
    created_at: datetime


class ContentSearchRequest(BaseModel):
    """
    Semantic search request.

    Decision #5: Vector embeddings for semantic search.
    """
    query: str = Field(..., min_length=3)
    course_id: Optional[UUID] = None
    ka_id: Optional[UUID] = None
    limit: int = Field(default=10, ge=1, le=50)


class ContentSearchResult(BaseModel):
    """
    Semantic search result.

    Returns content chunks ranked by similarity.
    """
    chunk_id: UUID
    content_title: str
    content_text: str
    ka_name: str
    similarity_score: float  # 0-1, cosine similarity
    source_document: Optional[str]
    source_page: Optional[str]


class ContentReviewRequest(BaseModel):
    """
    Content review request (admin/expert only).

    Decision #76: Expert review workflow.
    """
    chunk_id: UUID
    review_status: str = Field(..., pattern="^(approved|flagged|rejected)$")
    review_notes: Optional[str] = None


class ContentGenerationRequest(BaseModel):
    """
    Generate content using LLM (admin only).

    Decision #76: LLM-generated content with quality gates.
    """
    course_id: UUID
    ka_id: UUID
    domain_id: Optional[UUID] = None
    topic: str = Field(..., min_length=3)
    difficulty_level: str = Field(..., pattern="^(basic|intermediate|advanced)$")
    word_count_target: int = Field(default=500, ge=100, le=2000)
