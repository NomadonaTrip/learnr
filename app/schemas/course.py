"""
Course, KnowledgeArea, and Domain Pydantic schemas.

Includes multi-course support and wizard-style course creation (Decision #63, #65).
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema, TimestampMixin


class CourseBase(BaseModel):
    """
    Base course fields.
    """
    course_code: str = Field(..., min_length=2, max_length=20)
    course_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    version: str = Field(..., min_length=1, max_length=20)
    passing_score_percentage: int = Field(..., ge=0, le=100)


class CourseCreate(CourseBase):
    """
    Course creation (wizard step 1).

    Decision #65: Wizard-style course creation (draft → active workflow).
    """
    exam_duration_minutes: Optional[int] = Field(None, gt=0)
    total_questions: Optional[int] = Field(None, gt=0)
    min_questions_required: int = Field(default=200, gt=0)
    min_chunks_required: int = Field(default=50, gt=0)


class CourseUpdate(BaseModel):
    """
    Course update (all fields optional).
    """
    course_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = None
    passing_score_percentage: Optional[int] = Field(None, ge=0, le=100)
    exam_duration_minutes: Optional[int] = Field(None, gt=0)
    total_questions: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(None, pattern="^(draft|active|archived)$")


class CourseResponse(BaseSchema, TimestampMixin):
    """
    Course response.
    """
    course_id: UUID
    course_code: str
    course_name: str
    description: Optional[str]
    version: str
    status: str  # 'draft' | 'active' | 'archived'
    wizard_completed: bool
    passing_score_percentage: int
    exam_duration_minutes: Optional[int]
    total_questions: Optional[int]
    min_questions_required: int
    min_chunks_required: int
    is_active: bool


class CourseWithKAsResponse(CourseResponse):
    """
    Course response with embedded knowledge areas.

    Used for course details view.
    """
    knowledge_areas: List['KnowledgeAreaResponse'] = []


class KnowledgeAreaBase(BaseModel):
    """
    Base knowledge area fields.
    """
    ka_code: str = Field(..., min_length=2, max_length=20)
    ka_name: str = Field(..., min_length=1, max_length=255)
    ka_number: int = Field(..., ge=1)
    weight_percentage: Decimal = Field(..., ge=0, le=100)
    description: Optional[str] = None


class KnowledgeAreaCreate(KnowledgeAreaBase):
    """
    Knowledge area creation (wizard step 2).

    Decision #63: Variable KA counts per course (6 for CBAP, 3 for PSM1, etc.).
    Note: Weights must sum to 100% (validated at service layer or database trigger).
    """
    course_id: UUID


class KnowledgeAreaBulkCreate(BaseModel):
    """
    Bulk create knowledge areas for a course.

    Validates that weights sum to 100%.
    """
    course_id: UUID
    knowledge_areas: List[KnowledgeAreaBase] = Field(..., min_length=1)

    @field_validator('knowledge_areas')
    @classmethod
    def validate_weights_sum_to_100(cls, v: List[KnowledgeAreaBase]) -> List[KnowledgeAreaBase]:
        """Ensure knowledge area weights sum to 100% (Decision #63)."""
        total_weight = sum(ka.weight_percentage for ka in v)
        if abs(total_weight - Decimal('100.00')) > Decimal('0.01'):
            raise ValueError(f'Knowledge area weights must sum to 100%, got {total_weight}%')
        return v


class KnowledgeAreaUpdate(BaseModel):
    """
    Knowledge area update (all fields optional).
    """
    ka_name: Optional[str] = Field(None, min_length=1, max_length=255)
    ka_number: Optional[int] = Field(None, ge=1)
    weight_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    description: Optional[str] = None


class KnowledgeAreaResponse(BaseSchema, TimestampMixin):
    """
    Knowledge area response.
    """
    ka_id: UUID
    course_id: UUID
    ka_code: str
    ka_name: str
    ka_number: int
    weight_percentage: Decimal
    description: Optional[str]


class KnowledgeAreaWithDomainsResponse(KnowledgeAreaResponse):
    """
    Knowledge area response with embedded domains.
    """
    domains: List['DomainResponse'] = []


class DomainBase(BaseModel):
    """
    Base domain fields (subcategories within knowledge areas).
    """
    domain_code: str = Field(..., min_length=2, max_length=20)
    domain_name: str = Field(..., min_length=1, max_length=255)
    domain_number: int = Field(..., ge=1)
    description: Optional[str] = None


class DomainCreate(DomainBase):
    """
    Domain creation.
    """
    ka_id: UUID


class DomainUpdate(BaseModel):
    """
    Domain update (all fields optional).
    """
    domain_name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain_number: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None


class DomainResponse(BaseSchema, TimestampMixin):
    """
    Domain response.
    """
    domain_id: UUID
    ka_id: UUID
    domain_code: str
    domain_name: str
    domain_number: int
    description: Optional[str]
