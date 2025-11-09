"""
Course models: Course, KnowledgeArea, Domain.

Multi-course platform design (Decision #63, #65).
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, DECIMAL, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import uuid


class Course(Base):
    """
    Certification courses (CBAP, PSM1, CFA, etc.)

    Decisions: #4 (Expansion), #63 (Multi-course), #65 (Wizard)
    """
    __tablename__ = "courses"

    # Primary Key
    course_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Course Identification
    course_code = Column(String(20), unique=True, nullable=False)  # 'CBAP', 'PSM1', 'CFA-L1'
    course_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False)  # 'v3' for BABOK v3

    # Status Tracking (Decision #65)
    status = Column(String(20), nullable=False, default='draft')  # 'draft' | 'active' | 'archived'
    wizard_completed = Column(Boolean, nullable=False, default=False)

    # Exam Configuration
    passing_score_percentage = Column(Integer, nullable=False)  # 70 for CBAP
    exam_duration_minutes = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=True)  # 120 for CBAP

    # Validation Thresholds (Decision #65)
    min_questions_required = Column(Integer, default=200)
    min_chunks_required = Column(Integer, default=50)

    # Audit Trail (Decision #65)
    created_by = Column(String(36), ForeignKey('users.user_id'), nullable=True)
    updated_by = Column(String(36), ForeignKey('users.user_id'), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Cleanup Metadata (Decision #65)
    auto_delete_at = Column(DateTime(timezone=True), nullable=True)  # For abandoned drafts

    # Legacy Field (kept for backward compatibility)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    knowledge_areas = relationship("KnowledgeArea", back_populates="course", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="course", cascade="all, delete-orphan")
    content_chunks = relationship("ContentChunk", back_populates="course", cascade="all, delete-orphan")
    subscription_plans = relationship("SubscriptionPlan", back_populates="course", cascade="all, delete-orphan")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'archived')", name='chk_course_status'),
    )

    def __repr__(self):
        return f"<Course {self.course_code} - {self.course_name}>"


class KnowledgeArea(Base):
    """
    Knowledge areas within a course (6 for CBAP, 3 for PSM1, 10 for CFA)

    Decisions: #63 (Variable KA counts per course)
    """
    __tablename__ = "knowledge_areas"

    # Primary Key
    ka_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key
    course_id = Column(String(36), ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)

    # KA Identification (unique per course, not globally)
    ka_code = Column(String(20), nullable=False)  # 'BA-PA', 'BA-ED', etc.
    ka_name = Column(String(255), nullable=False)
    ka_number = Column(Integer, nullable=False)  # 1-N (display order)

    # Description
    description = Column(Text, nullable=True)

    # Weight (Decision #63: must sum to 100% per course)
    weight_percentage = Column(DECIMAL(5, 2), nullable=False)  # 0.00-100.00

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="knowledge_areas")
    domains = relationship("Domain", back_populates="knowledge_area", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="knowledge_area", cascade="all, delete-orphan")
    user_competencies = relationship("UserCompetency", back_populates="knowledge_area", cascade="all, delete-orphan")
    content_chunks = relationship("ContentChunk", back_populates="knowledge_area", cascade="all, delete-orphan")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("weight_percentage >= 0.00 AND weight_percentage <= 100.00", name='chk_weight_range'),
    )

    def __repr__(self):
        return f"<KnowledgeArea {self.ka_code} - {self.ka_name}>"


class Domain(Base):
    """
    Domains within knowledge areas (subcategories)
    """
    __tablename__ = "domains"

    # Primary Key
    domain_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key
    ka_id = Column(String(36), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)

    # Domain Identification
    domain_code = Column(String(20), nullable=False)
    domain_name = Column(String(255), nullable=False)
    domain_number = Column(Integer, nullable=False)  # Display order within KA

    # Description
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    knowledge_area = relationship("KnowledgeArea", back_populates="domains")
    questions = relationship("Question", back_populates="domain", cascade="all, delete-orphan")
    content_chunks = relationship("ContentChunk", back_populates="domain", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Domain {self.domain_code} - {self.domain_name}>"
