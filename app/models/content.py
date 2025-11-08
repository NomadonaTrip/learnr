"""
Content models: ContentChunk for reading material with quality control.

Includes vector embeddings and quality evaluation (Decision #76).
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, DECIMAL, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
from pgvector.sqlalchemy import Vector
import uuid
from typing import Optional


class ContentChunk(Base):
    """
    Content chunks from BABOK v3 or other study materials.
    Includes vector embeddings for semantic search.

    Decisions: #23 (Reading content essential), #76 (Quality evaluation)
    """
    __tablename__ = "content_chunks"

    # Primary Key
    chunk_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    course_id = Column(String(36), ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    ka_id = Column(String(36), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)
    domain_id = Column(String(36), ForeignKey('domains.domain_id', ondelete='SET NULL'), nullable=True)

    # Content
    content_title = Column(String(255), nullable=False)
    content_text = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False, default='babok')  # 'babok' | 'generated' | 'custom'

    # Source Reference
    source_document = Column(String(255), nullable=True)  # e.g., "BABOK v3"
    source_page = Column(String(50), nullable=True)  # e.g., "pp. 125-130"
    source_section = Column(String(255), nullable=True)  # e.g., "5.2 Requirements Elicitation"

    # Vector Embedding (OpenAI text-embedding-3-large: 3072 dimensions)
    embedding = Column(Vector(3072), nullable=True)

    # Metadata
    token_count = Column(Integer, nullable=True)  # Number of tokens in chunk
    difficulty_level = Column(String(20), nullable=True)  # 'basic' | 'intermediate' | 'advanced'

    # Quality Control (Decision #76)
    expert_reviewed = Column(Boolean, nullable=False, default=False)
    review_status = Column(String(20), nullable=False, default='pending')  # 'pending' | 'approved' | 'flagged' | 'rejected'
    source_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=False)  # Only show approved, active content

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="content_chunks")
    knowledge_area = relationship("KnowledgeArea", back_populates="content_chunks")
    domain = relationship("Domain", back_populates="content_chunks")
    reading_consumed = relationship("ReadingConsumed", back_populates="content_chunk", cascade="all, delete-orphan")
    feedback = relationship("ContentFeedback", back_populates="chunk", cascade="all, delete-orphan")
    efficacy_records = relationship("ContentEfficacy", back_populates="chunk", cascade="all, delete-orphan")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("review_status IN ('pending', 'approved', 'flagged', 'rejected')", name='chk_review_status'),
        CheckConstraint("difficulty_level IS NULL OR difficulty_level IN ('basic', 'intermediate', 'advanced')", name='chk_difficulty_level'),
        CheckConstraint("content_type IN ('babok', 'generated', 'custom')", name='chk_content_type'),
    )

    @property
    def helpfulness_score(self) -> Optional[float]:
        """Calculate helpfulness percentage from feedback."""
        if not self.feedback:
            return None
        total = len(self.feedback)
        helpful = sum(1 for f in self.feedback if f.was_helpful)
        return round((helpful / total) * 100, 2) if total > 0 else None

    @property
    def efficacy_rate(self) -> Optional[float]:
        """Calculate efficacy percentage."""
        measured = [e for e in self.efficacy_records if e.improved is not None]
        if not measured:
            return None
        improved = sum(1 for e in measured if e.improved)
        return round((improved / len(measured)) * 100, 2)

    def __repr__(self):
        return f"<ContentChunk {self.chunk_id} - {self.content_title}>"


class ContentFeedback(Base):
    """
    User feedback on content helpfulness.

    Decision #76: Quality evaluation system
    """
    __tablename__ = "content_feedback"

    # Primary Key
    feedback_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    chunk_id = Column(String(36), ForeignKey('content_chunks.chunk_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)

    # Feedback
    was_helpful = Column(Boolean, nullable=False)
    feedback_text = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    chunk = relationship("ContentChunk", back_populates="feedback")
    user = relationship("User")

    def __repr__(self):
        return f"<ContentFeedback {self.feedback_id} - {'Helpful' if self.was_helpful else 'Not Helpful'}>"


class ContentEfficacy(Base):
    """
    Measures whether content improves user competency.

    Decision #76: Track if reading actually helps performance
    """
    __tablename__ = "content_efficacy"

    # Primary Key
    efficacy_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    chunk_id = Column(String(36), ForeignKey('content_chunks.chunk_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    ka_id = Column(String(36), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)

    # Efficacy measurement
    read_at = Column(DateTime, nullable=False)
    competency_before = Column(DECIMAL(5, 2), nullable=False)
    competency_after = Column(DECIMAL(5, 2), nullable=True)
    measured_at = Column(DateTime, nullable=True)

    # Computed
    improved = Column(Boolean, nullable=True)
    improvement_amount = Column(DECIMAL(5, 2), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    chunk = relationship("ContentChunk", back_populates="efficacy_records")
    user = relationship("User")
    knowledge_area = relationship("KnowledgeArea")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("competency_before >= 0 AND competency_before <= 1", name='chk_comp_before_range'),
        CheckConstraint("competency_after IS NULL OR (competency_after >= 0 AND competency_after <= 1)", name='chk_comp_after_range'),
    )

    def __repr__(self):
        return f"<ContentEfficacy {self.efficacy_id} - {'Improved' if self.improved else 'Pending'}>"
