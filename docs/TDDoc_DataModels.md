# Technical Design Document - Data Models
# LearnR - Adaptive Learning Platform

**Version:** 1.3.1 (Aligned with DatabaseSchema v1.3.1)  
**Date:** October 30, 2025  
**Status:** PRODUCTION READY  
**Related Documents:** 
- TDDoc_DatabaseSchema.md v1.3.1
- TDDoc_API_Endpoints.md v1.3.1
- TDDoc_Algorithms.md v1.3.1
- Decision Log (note.md) - Decisions #1-83

---

## Overview

This document specifies all data models for the Adaptive CBAP Learning Platform MVP. It defines:
- **SQLAlchemy ORM Models** (database layer)
- **Pydantic Models** (API request/response validation)
- **Hybrid Properties** (encryption, computed fields)
- **Relationships** (foreign keys, joins)
- **Validation Rules** (constraints, business logic)

**TDD Purpose:** This document serves as the executable specification for test creation. Tests can be written against these models without implementation code.

---

## Technology Stack

- **ORM:** SQLAlchemy 2.0+
- **Validation:** Pydantic 2.0+
- **Encryption:** cryptography.fernet (AES-128-CBC)
- **Type Hints:** Python 3.11+ type annotations
- **Database:** PostgreSQL 15+

---

## Architecture Principles

1. **Separation of Concerns:**
   - SQLAlchemy models = database persistence
   - Pydantic models = API validation & serialization
   - No business logic in models (move to services)

2. **Security:**
   - Field-level encryption for PII (Decision #59)
   - No plaintext passwords (bcrypt hash only)
   - Sensitive fields masked in responses

3. **Type Safety:**
   - Full type hints on all models
   - Strict validation at API boundaries
   - Runtime type checking with Pydantic

4. **Performance:**
   - Lazy loading for relationships
   - Selective field loading (don't load all fields)
   - Efficient serialization

---

## File Structure

```
app/
â”œâ”€â”€ models/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ database.py           # SQLAlchemy base & session
â”‚   â”œâ”€â”€ user.py               # User, UserProfile models
â”‚   â”œâ”€â”€ course.py             # Course, KnowledgeArea, Domain models
â”‚   â”œâ”€â”€ question.py           # Question, AnswerChoice models
â”‚   â”œâ”€â”€ content.py            # ContentChunk model
â”‚   â”œâ”€â”€ learning.py           # UserCompetency, QuestionAttempt, Session models
â”‚   â”œâ”€â”€ spaced_repetition.py  # SpacedRepetitionCard model
â”‚   â”œâ”€â”€ financial.py          # Subscription, Payment, Refund models
â”‚   â””â”€â”€ security.py           # SecurityLog, RateLimitEntry models
â”œâ”€â”€ schemas/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ user.py               # Pydantic schemas for users
â”‚   â”œâ”€â”€ course.py             # Pydantic schemas for courses
â”‚   â”œâ”€â”€ question.py           # Pydantic schemas for questions
â”‚   â”œâ”€â”€ learning.py           # Pydantic schemas for learning
â”‚   â”œâ”€â”€ financial.py          # Pydantic schemas for payments
â”‚   â””â”€â”€ auth.py               # Authentication schemas
â””â”€â”€ utils/
    â”œâ”€â”€ encryption.py         # Field encryption utilities
    â””â”€â”€ validators.py         # Custom Pydantic validators
```

---

## Part 1: SQLAlchemy ORM Models

### 1.1 Base Configuration

**File:** `app/models/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/cbap_db")

# Engine configuration
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL logging in development
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### 1.2 User Models

**File:** `app/models/user.py`

```python
from sqlalchemy import Column, String, Boolean, DateTime, Integer, UUID, ForeignKey, Text, DECIMAL, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
from app.utils.encryption import encrypt_field, decrypt_field
from sqlalchemy.ext.hybrid import hybrid_property
import uuid

class User(Base):
    """
    User accounts and authentication.
    
    Decisions: #50 (2FA), #53 (Argon2id), #59 (PII encryption), #66 (Stripe)
    """
    __tablename__ = "users"
    
    # Primary Key
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication (encrypted)
    _email = Column("email", String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # Argon2id
    
    # Personal Information (encrypted)
    _first_name = Column("first_name", String(100), nullable=False)
    _last_name = Column("last_name", String(100), nullable=False)
    
    # Authorization
    role = Column(String(20), nullable=False, default='learner')  # 'learner' | 'admin' | 'super_admin'
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Email Verification
    email_verified = Column(Boolean, nullable=False, default=False)
    
    # Two-Factor Authentication (Decision #50)
    two_factor_enabled = Column(Boolean, nullable=False, default=False)
    two_factor_secret = Column(String(32), nullable=True)  # TOTP secret (encrypted)
    
    # Bootstrap Security (Decision #79)
    must_change_password = Column(Boolean, nullable=False, default=False)
    
    # Stripe Integration (Decision #66)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    competencies = relationship("UserCompetency", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    question_attempts = relationship("QuestionAttempt", back_populates="user", cascade="all, delete-orphan")
    sr_cards = relationship("SpacedRepetitionCard", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    security_logs = relationship("SecurityLog", foreign_keys="SecurityLog.admin_user_id", back_populates="admin_user")
    reading_consumed = relationship("ReadingConsumed", back_populates="user", cascade="all, delete-orphan")
    
    # Hybrid Properties for Encryption (Decision #59)
    @hybrid_property
    def email(self) -> str:
        """Decrypt email when accessed"""
        return decrypt_field(self._email)
    
    @email.setter
    def email(self, value: str):
        """Encrypt email when set"""
        self._email = encrypt_field(value)
    
    @hybrid_property
    def first_name(self) -> str:
        """Decrypt first_name when accessed"""
        return decrypt_field(self._first_name)
    
    @first_name.setter
    def first_name(self, value: str):
        """Encrypt first_name when set"""
        self._first_name = encrypt_field(value)
    
    @hybrid_property
    def last_name(self) -> str:
        """Decrypt last_name when accessed"""
        return decrypt_field(self._last_name)
    
    @last_name.setter
    def last_name(self, value: str):
        """Encrypt last_name when set"""
        self._last_name = encrypt_field(value)
    
    @property
    def full_name(self) -> str:
        """Computed property: full name"""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<User {self.user_id} - {self.email}>"


class UserProfile(Base):
    """
    Extended user information from onboarding.
    
    Decisions: #10 (Onboarding), #63 (Multi-course), #66 (Acquisition tracking)
    """
    __tablename__ = "user_profiles"
    
    # Primary Key
    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, unique=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey('courses.course_id'), nullable=False)
    
    # Onboarding Question 1: How did you hear about us?
    referral_source = Column(String(50), nullable=True)  # 'search' | 'social' | 'colleague' | 'other'
    referral_source_detail = Column(Text, nullable=True)
    
    # Onboarding Question 3: Why this certification?
    motivation = Column(Text, nullable=True)
    
    # Onboarding Question 4: Exam date
    exam_date = Column(Date, nullable=True)
    days_until_exam = Column(Integer, nullable=True)  # Calculated field
    
    # Onboarding Question 5: Current level
    current_level = Column(String(20), nullable=False)  # 'beginner' | 'intermediate' | 'advanced'
    
    # Onboarding Question 6: Target score
    target_score_percentage = Column(Integer, nullable=True)  # 70-100
    
    # Onboarding Question 7: Daily commitment
    daily_commitment_minutes = Column(Integer, nullable=False)  # 15-120
    
    # Acquisition Tracking (Decision #66)
    acquisition_cost = Column(DECIMAL(10, 2), nullable=True)  # CAC tracking
    acquisition_channel = Column(String(50), nullable=True)  # 'google_ads' | 'organic' | 'referral' | 'social'
    referral_code = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")
    course = relationship("Course")
    
    def __repr__(self):
        return f"<UserProfile {self.profile_id} - User {self.user_id}>"
```

---

### 1.3 Course Models

**File:** `app/models/course.py`

```python
from sqlalchemy import Column, String, Boolean, DateTime, Integer, UUID, ForeignKey, Text, DECIMAL, CheckConstraint
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
    course_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
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
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Cleanup Metadata (Decision #65)
    auto_delete_at = Column(DateTime, nullable=True)  # For abandoned drafts
    
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
    ka_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key
    course_id = Column(UUID(as_uuid=True), ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    
    # KA Identification (unique per course, not globally)
    ka_code = Column(String(20), nullable=False)  # 'BA-PA', 'BA-ED', etc.
    ka_name = Column(String(255), nullable=False)
    ka_number = Column(Integer, nullable=False)  # 1-N (display order)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Weight (Decision #63: must sum to 100% per course)
    weight_percentage = Column(DECIMAL(5, 2), nullable=False)  # 0.00-100.00
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="knowledge_areas")
    domains = relationship("Domain", back_populates="knowledge_area", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="knowledge_area", cascade="all, delete-orphan")
    user_competencies = relationship("UserCompetency", back_populates="knowledge_area", cascade="all, delete-orphan")
    
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
    domain_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key
    ka_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)
    
    # Domain Identification
    domain_code = Column(String(20), nullable=False)
    domain_name = Column(String(255), nullable=False)
    domain_number = Column(Integer, nullable=False)  # Display order within KA
    
    # Description
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    knowledge_area = relationship("KnowledgeArea", back_populates="domains")
    questions = relationship("Question", back_populates="domain", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Domain {self.domain_code} - {self.domain_name}>"
```

---

### 1.4 Question Models

**File:** `app/models/question.py`

```python
from sqlalchemy import Column, String, Boolean, DateTime, Integer, UUID, ForeignKey, Text, DECIMAL, CheckConstraint
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
    question_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    course_id = Column(UUID(as_uuid=True), ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    ka_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey('domains.domain_id', ondelete='SET NULL'), nullable=True)
    
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
    answer_choices = relationship("AnswerChoice", back_populates="question", cascade="all, delete-orphan")
    attempts = relationship("QuestionAttempt", back_populates="question", cascade="all, delete-orphan")
    sr_cards = relationship("SpacedRepetitionCard", back_populates="question", cascade="all, delete-orphan")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("difficulty >= 0.00 AND difficulty <= 1.00", name='chk_difficulty_range'),
        CheckConstraint("discrimination IS NULL OR (discrimination >= 0.00 AND discrimination <= 3.00)", name='chk_discrimination_range'),
        CheckConstraint("question_type IN ('multiple_choice', 'true_false')", name='chk_question_type'),
    )
    
    def __repr__(self):
        return f"<Question {self.question_id} - Difficulty {self.difficulty}>"


class AnswerChoice(Base):
    """
    Answer choices for multiple-choice questions.
    """
    __tablename__ = "answer_choices"
    
    # Primary Key
    choice_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key
    question_id = Column(UUID(as_uuid=True), ForeignKey('questions.question_id', ondelete='CASCADE'), nullable=False)
    
    # Choice Content
    choice_letter = Column(String(1), nullable=False)  # 'A', 'B', 'C', 'D'
    choice_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    
    # Explanation (shown after answer)
    explanation = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    question = relationship("Question", back_populates="answer_choices")
    
    def __repr__(self):
        return f"<AnswerChoice {self.choice_letter} - Question {self.question_id}>"
```

---

### 1.5 Content Models

**File:** `app/models/content.py`

```python
from sqlalchemy import Column, String, DateTime, Integer, UUID, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY
from app.models.database import Base
from pgvector.sqlalchemy import Vector
import uuid

class ContentChunk(Base):
    """
    Reading content chunks with semantic embeddings.
    
    Decisions: #5 (Vector embeddings), #17 (Qdrant initially, moved to pgvector)
    """
    __tablename__ = "content_chunks"
    
    # Primary Key
    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    course_id = Column(UUID(as_uuid=True), ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    ka_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)
    domain_id = Column(UUID(as_uuid=True), ForeignKey('domains.domain_id', ondelete='SET NULL'), nullable=True)
    
    # Content
    content_text = Column(Text, nullable=False)
    content_title = Column(String(255), nullable=True)
    
    # Source Information
    source_document = Column(String(255), nullable=True)  # e.g., 'BABOK v3'
    page_reference = Column(String(50), nullable=True)  # e.g., 'pp. 45-47'
    
    # Semantic Embeddings (Decision #5)
    # Using pgvector extension for vector storage
    embedding = Column(Vector(3072), nullable=True)  # text-embedding-3-large = 3072 dimensions
    
    # Quality Control (Decision #76)
    expert_reviewed = Column(Boolean, default=False)
    review_status = Column(String(20), default='pending')  # 'pending' | 'approved' | 'rejected'
    source_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, default=False)
    
    # Difficulty Estimate
    difficulty_estimate = Column(DECIMAL(5, 2), nullable=True)  # 0.00-1.00 (estimated from content complexity)
    
    # Metadata
    word_count = Column(Integer, nullable=True)
    estimated_read_time_minutes = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="content_chunks")
    knowledge_area = relationship("KnowledgeArea")
    domain = relationship("Domain")
    feedback = relationship("ContentFeedback", back_populates="chunk", cascade="all, delete-orphan")
    efficacy = relationship("ContentEfficacy", back_populates="chunk", cascade="all, delete-orphan")
    reading_consumed = relationship("ReadingConsumed", back_populates="chunk", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ContentChunk {self.chunk_id} - {self.content_title}>"


class ContentFeedback(Base):
    """
    User feedback on content helpfulness.
    
    Decision #76: Content quality evaluation system
    Decision #82: Post-publish quality control
    """
    __tablename__ = "content_feedback"
    
    # Primary Key
    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    chunk_id = Column(UUID(as_uuid=True), ForeignKey('content_chunks.chunk_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    
    # Feedback data
    was_helpful = Column(Boolean, nullable=False)
    feedback_text = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    chunk = relationship("ContentChunk", back_populates="feedback")
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('chunk_id', 'user_id', name='uq_feedback_chunk_user'),
    )
    
    def __repr__(self):
        return f"<ContentFeedback {self.feedback_id} - {'Helpful' if self.was_helpful else 'Not Helpful'}>"


class ContentEfficacy(Base):
    """
    Measures whether content improves user competency.
    
    Decision #76: Content quality evaluation system
    Decision #82: Post-publish quality control (efficacy tracking)
    """
    __tablename__ = "content_efficacy"
    
    # Primary Key
    efficacy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    chunk_id = Column(UUID(as_uuid=True), ForeignKey('content_chunks.chunk_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    ka_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)
    
    # Efficacy measurement
    read_at = Column(DateTime, nullable=False)
    competency_before = Column(DECIMAL(4, 2), nullable=True)
    competency_after = Column(DECIMAL(4, 2), nullable=True)
    competency_change = Column(DECIMAL(4, 2), nullable=True)
    
    # Window for measuring impact
    measurement_window_days = Column(Integer, default=7)
    
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    chunk = relationship("ContentChunk", back_populates="efficacy")
    user = relationship("User")
    knowledge_area = relationship("KnowledgeArea")
    
    def __repr__(self):
        return f"<ContentEfficacy {self.efficacy_id} - Change {self.competency_change}>"
```

---

### 1.6 Learning Progress Models

**File:** `app/models/learning.py`

```python
from sqlalchemy import Column, String, Boolean, DateTime, Integer, UUID, ForeignKey, Text, DECIMAL, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import uuid

class UserCompetency(Base):
    """
    User competency tracking per knowledge area.
    
    Decisions: #8 (Competency-based metrics), #18 (IRT competency estimation)
    """
    __tablename__ = "user_competency"
    
    # Primary Key
    competency_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    ka_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)
    
    # Competency Score (Decision #18: IRT-based)
    competency_score = Column(DECIMAL(5, 2), nullable=False, default=0.50)  # 0.00-1.00
    confidence_interval = Column(DECIMAL(5, 2), nullable=True)  # Â±uncertainty
    
    # Practice Statistics
    questions_attempted = Column(Integer, nullable=False, default=0)
    questions_correct = Column(Integer, nullable=False, default=0)
    
    # Last Activity
    last_practiced_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="competencies")
    knowledge_area = relationship("KnowledgeArea", back_populates="user_competencies")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("competency_score >= 0.00 AND competency_score <= 1.00", name='chk_competency_range'),
    )
    
    @property
    def accuracy_percentage(self) -> float:
        """Computed property: accuracy as percentage"""
        if self.questions_attempted == 0:
            return 0.0
        return (self.questions_correct / self.questions_attempted) * 100
    
    def __repr__(self):
        return f"<UserCompetency User {self.user_id} - KA {self.ka_id} - Score {self.competency_score}>"


class QuestionAttempt(Base):
    """
    Individual question attempts by users.
    
    Decisions: #18 (IRT parameter estimation), #31 (Spaced repetition)
    """
    __tablename__ = "question_attempts"
    
    # Primary Key
    attempt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey('questions.question_id', ondelete='CASCADE'), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.session_id', ondelete='SET NULL'), nullable=True)
    
    # Attempt Details
    selected_choice_id = Column(UUID(as_uuid=True), ForeignKey('answer_choices.choice_id'), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    
    # Timing
    time_spent_seconds = Column(Integer, nullable=True)
    
    # Competency at Time of Attempt (Decision #18)
    competency_at_attempt = Column(DECIMAL(5, 2), nullable=True)  # User's competency when they answered
    
    # Timestamps
    attempted_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="question_attempts")
    question = relationship("Question", back_populates="attempts")
    session = relationship("Session", back_populates="question_attempts")
    selected_choice = relationship("AnswerChoice")
    
    def __repr__(self):
        return f"<QuestionAttempt {self.attempt_id} - {'Correct' if self.is_correct else 'Incorrect'}>"


class Session(Base):
    """
    Learning sessions by users.
    
    Decisions: #12 (Daily sessions), #49 (Session analytics)
    """
    __tablename__ = "sessions"
    
    # Primary Key
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    
    # Session Type
    session_type = Column(String(20), nullable=False)  # 'diagnostic' | 'practice' | 'review' | 'mock_exam'
    
    # Session Stats
    total_questions = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    duration_minutes = Column(Integer, nullable=True)
    
    # Session State
    is_completed = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    question_attempts = relationship("QuestionAttempt", back_populates="session", cascade="all, delete-orphan")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("session_type IN ('diagnostic', 'practice', 'review', 'mock_exam')", name='chk_session_type'),
    )
    
    @property
    def accuracy_percentage(self) -> float:
        """Computed property: session accuracy"""
        if self.total_questions == 0:
            return 0.0
        return (self.correct_answers / self.total_questions) * 100
    
    def __repr__(self):
        return f"<Session {self.session_id} - {self.session_type}>"


class ReadingConsumed(Base):
    """
    Track which content chunks users have read.
    
    Decision #36: Reading recommendations
    Decision #76: Content quality evaluation system
    """
    __tablename__ = "reading_consumed"
    
    # Primary Key
    reading_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey('content_chunks.chunk_id', ondelete='CASCADE'), nullable=False)
    
    # Reading metrics
    read_at = Column(DateTime, nullable=False, server_default=func.now())
    time_spent_seconds = Column(Integer, nullable=True)
    completed = Column(Boolean, nullable=False, default=True)
    
    # User feedback
    was_helpful = Column(Boolean, nullable=True)
    difficulty_rating = Column(Integer, nullable=True)  # 1-5
    
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="reading_consumed")
    chunk = relationship("ContentChunk", back_populates="reading_consumed")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("difficulty_rating BETWEEN 1 AND 5", name='chk_difficulty_rating'),
    )
    
    def __repr__(self):
        return f"<ReadingConsumed {self.reading_id} - User {self.user_id}>"
```

---

### 1.7 Spaced Repetition Models

**File:** `app/models/spaced_repetition.py`

```python
from sqlalchemy import Column, Boolean, DateTime, Integer, UUID, ForeignKey, DECIMAL, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import uuid

class SpacedRepetitionCard(Base):
    """
    Spaced repetition cards for questions (SM-2 algorithm).
    
    Decisions: #31 (Spaced repetition essential), #32 (SM-2 algorithm)
    """
    __tablename__ = "spaced_repetition_cards"
    
    # Primary Key
    card_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey('questions.question_id', ondelete='CASCADE'), nullable=False)
    
    # SM-2 Algorithm Parameters (Decision #32)
    easiness_factor = Column(DECIMAL(3, 2), nullable=False, default=2.50)  # 1.30-2.50
    interval_days = Column(Integer, nullable=False, default=1)  # Days until next review
    repetitions = Column(Integer, nullable=False, default=0)  # Number of successful reviews
    
    # Review Schedule
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=False)  # When card is due
    
    # State
    is_due = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sr_cards")
    question = relationship("Question", back_populates="sr_cards")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("easiness_factor >= 1.30 AND easiness_factor <= 2.50", name='chk_easiness_range'),
        CheckConstraint("interval_days >= 1", name='chk_interval_positive'),
    )
    
    def __repr__(self):
        return f"<SpacedRepetitionCard {self.card_id} - EF {self.easiness_factor}>"
```

---

### 1.8 Financial Models

**File:** `app/models/financial.py`

```python
from sqlalchemy import Column, String, Boolean, DateTime, Integer, UUID, ForeignKey, Text, DECIMAL, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import uuid

class SubscriptionPlan(Base):
    """
    Subscription pricing plans (monthly/annual).
    
    Decisions: #55 (Pricing strategy), #66 (Financial infrastructure)
    """
    __tablename__ = "subscription_plans"
    
    # Primary Key
    plan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key
    course_id = Column(UUID(as_uuid=True), ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    
    # Plan Details
    plan_name = Column(String(100), nullable=False)  # 'CBAP Monthly', 'CBAP Annual'
    billing_interval = Column(String(20), nullable=False)  # 'monthly' | 'annual' | 'one_time'
    price_amount = Column(DECIMAL(10, 2), nullable=False)  # 20.00, 200.00
    currency = Column(String(3), nullable=False, default='USD')
    
    # Stripe Integration (Decision #66)
    stripe_price_id = Column(String(255), unique=True, nullable=False)
    
    # Plan Configuration
    is_active = Column(Boolean, nullable=False, default=True)
    trial_period_days = Column(Integer, default=7)  # Decision #56: 7-day trial
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="subscription_plans")
    subscriptions = relationship("Subscription", back_populates="plan", cascade="all, delete-orphan")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("billing_interval IN ('monthly', 'annual', 'one_time')", name='chk_billing_interval'),
        CheckConstraint("price_amount > 0", name='chk_price_positive'),
    )
    
    def __repr__(self):
        return f"<SubscriptionPlan {self.plan_name} - ${self.price_amount}/{self.billing_interval}>"


class Subscription(Base):
    """
    User subscription lifecycle tracking.
    
    Decisions: #66 (Financial infrastructure)
    """
    __tablename__ = "subscriptions"
    
    # Primary Key
    subscription_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('subscription_plans.plan_id'), nullable=False)
    
    # Stripe Integration
    stripe_subscription_id = Column(String(255), unique=True, nullable=False)
    
    # Subscription Status
    status = Column(String(20), nullable=False)  # 'active' | 'canceled' | 'past_due' | 'trialing'
    
    # Dates
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("status IN ('active', 'canceled', 'past_due', 'trialing')", name='chk_subscription_status'),
    )
    
    def __repr__(self):
        return f"<Subscription {self.subscription_id} - {self.status}>"


class Payment(Base):
    """
    Transaction records (Stripe payments).
    
    Decisions: #66 (Financial infrastructure)
    """
    __tablename__ = "payments"
    
    # Primary Key
    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('subscriptions.subscription_id', ondelete='SET NULL'), nullable=True)
    
    # Stripe Integration
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=False)
    stripe_charge_id = Column(String(255), nullable=True)
    
    # Payment Details
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    status = Column(String(20), nullable=False)  # 'succeeded' | 'failed' | 'refunded' | 'disputed'
    
    # Payment Method
    payment_method_type = Column(String(20), nullable=True)  # 'card' | 'bank_account'
    payment_method_brand = Column(String(20), nullable=True)  # 'visa' | 'mastercard' | 'amex'
    payment_method_last4 = Column(String(4), nullable=True)
    
    # Fees
    stripe_fee = Column(DECIMAL(10, 2), nullable=True)  # Stripe transaction fee
    net_amount = Column(DECIMAL(10, 2), nullable=True)  # Amount after fees
    
    # Failure Details
    failure_code = Column(String(50), nullable=True)
    failure_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    paid_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    refunds = relationship("Refund", back_populates="payment", cascade="all, delete-orphan")
    chargebacks = relationship("Chargeback", back_populates="payment", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="payment")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("status IN ('succeeded', 'failed', 'refunded', 'disputed', 'pending')", name='chk_payment_status'),
        CheckConstraint("amount > 0", name='chk_amount_positive'),
    )
    
    def __repr__(self):
        return f"<Payment {self.payment_id} - ${self.amount} - {self.status}>"


class Refund(Base):
    """
    Refund tracking and management.
    
    Decisions: #66 (Financial infrastructure)
    """
    __tablename__ = "refunds"
    
    # Primary Key
    refund_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.payment_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    
    # Stripe Integration
    stripe_refund_id = Column(String(255), unique=True, nullable=False)
    
    # Refund Details
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    reason = Column(String(50), nullable=True)  # 'requested_by_customer' | 'duplicate' | 'fraudulent'
    status = Column(String(20), nullable=False)  # 'succeeded' | 'failed' | 'pending'
    
    # Admin Notes
    admin_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    refunded_at = Column(DateTime, nullable=True)
    
    # Relationships
    payment = relationship("Payment", back_populates="refunds")
    user = relationship("User")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("status IN ('succeeded', 'failed', 'pending')", name='chk_refund_status'),
        CheckConstraint("amount > 0", name='chk_refund_amount_positive'),
    )
    
    def __repr__(self):
        return f"<Refund {self.refund_id} - ${self.amount}>"


class Chargeback(Base):
    """
    Dispute/chargeback handling.
    
    Decisions: #66 (Financial infrastructure)
    """
    __tablename__ = "chargebacks"
    
    # Primary Key
    chargeback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.payment_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    
    # Stripe Integration
    stripe_dispute_id = Column(String(255), unique=True, nullable=False)
    
    # Chargeback Details
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    reason = Column(String(50), nullable=True)  # 'fraudulent' | 'unrecognized' | 'duplicate' | 'product_not_received'
    status = Column(String(30), nullable=False)  # 'warning_needs_response' | 'won' | 'lost'
    
    # Evidence
    evidence_due_by = Column(DateTime, nullable=True)
    evidence_submitted = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    disputed_at = Column(DateTime, nullable=False, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    payment = relationship("Payment", back_populates="chargebacks")
    user = relationship("User")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("status IN ('warning_needs_response', 'won', 'lost', 'under_review')", name='chk_chargeback_status'),
        CheckConstraint("amount > 0", name='chk_chargeback_amount_positive'),
    )
    
    def __repr__(self):
        return f"<Chargeback {self.chargeback_id} - ${self.amount} - {self.status}>"


class PaymentMethod(Base):
    """
    Tokenized payment methods (PCI compliant).
    
    Decisions: #66 (Financial infrastructure)
    """
    __tablename__ = "payment_methods"
    
    # Primary Key
    method_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    
    # Stripe Integration (tokenized, PCI compliant)
    stripe_payment_method_id = Column(String(255), unique=True, nullable=False)
    
    # Payment Method Details (masked)
    method_type = Column(String(20), nullable=False)  # 'card' | 'bank_account'
    brand = Column(String(20), nullable=True)  # 'visa' | 'mastercard' | 'amex'
    last4 = Column(String(4), nullable=True)  # Last 4 digits only
    exp_month = Column(Integer, nullable=True)
    exp_year = Column(Integer, nullable=True)
    
    # Status
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("method_type IN ('card', 'bank_account')", name='chk_method_type'),
    )
    
    def __repr__(self):
        return f"<PaymentMethod {self.brand} ending in {self.last4}>"


class Invoice(Base):
    """
    Invoice generation and tracking.
    
    Decisions: #66 (Financial infrastructure)
    """
    __tablename__ = "invoices"
    
    # Primary Key
    invoice_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('subscriptions.subscription_id', ondelete='SET NULL'), nullable=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.payment_id', ondelete='SET NULL'), nullable=True)
    
    # Stripe Integration
    stripe_invoice_id = Column(String(255), unique=True, nullable=False)
    
    # Invoice Details
    invoice_number = Column(String(50), unique=True, nullable=False)
    amount_due = Column(DECIMAL(10, 2), nullable=False)
    amount_paid = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    currency = Column(String(3), nullable=False, default='USD')
    status = Column(String(20), nullable=False)  # 'draft' | 'open' | 'paid' | 'void' | 'uncollectible'
    
    # PDF Storage
    pdf_url = Column(String(500), nullable=True)  # S3 URL
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    due_date = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    subscription = relationship("Subscription")
    payment = relationship("Payment", back_populates="invoices")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'open', 'paid', 'void', 'uncollectible')", name='chk_invoice_status'),
    )
    
    def __repr__(self):
        return f"<Invoice {self.invoice_number} - ${self.amount_due} - {self.status}>"


class RevenueEvent(Base):
    """
    Financial events for analytics and reporting.
    
    Decisions: #66 (Financial infrastructure)
    """
    __tablename__ = "revenue_events"
    
    # Primary Key
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.payment_id', ondelete='SET NULL'), nullable=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('subscriptions.subscription_id', ondelete='SET NULL'), nullable=True)
    
    # Event Details
    event_type = Column(String(50), nullable=False)  # 'payment_succeeded' | 'payment_failed' | 'refund' | 'chargeback'
    amount = Column(DECIMAL(10, 2), nullable=False)  # Can be negative for refunds
    net_amount = Column(DECIMAL(10, 2), nullable=False)  # After fees
    currency = Column(String(3), nullable=False, default='USD')
    
    # Metadata
    description = Column(Text, nullable=True)
    
    # Timestamp
    occurred_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    user = relationship("User")
    payment = relationship("Payment")
    subscription = relationship("Subscription")
    
    def __repr__(self):
        return f"<RevenueEvent {self.event_type} - ${self.amount}>"
```

---

### 1.9 Security Models

**File:** `app/models/security.py`

```python
from sqlalchemy import Column, String, Boolean, DateTime, Integer, UUID, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import uuid

class SecurityLog(Base):
    """
    Immutable audit trail for security events.
    
    Decisions: #41 (Admin security), #48 (RBAC)
    """
    __tablename__ = "security_logs"
    
    # Primary Key
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=True)
    target_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=True)
    
    # Event Details
    action_type = Column(String(50), nullable=False)  # 'login' | 'logout' | 'user_view' | 'data_export' | 'user_delete'
    action_description = Column(Text, nullable=False)
    
    # Request Context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    
    # Severity
    severity = Column(String(20), nullable=False, default='INFO')  # 'INFO' | 'WARNING' | 'CRITICAL'
    
    # Timestamp (immutable)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    admin_user = relationship("User", foreign_keys=[admin_user_id], back_populates="security_logs")
    target_user = relationship("User", foreign_keys=[target_user_id])
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("severity IN ('INFO', 'WARNING', 'CRITICAL')", name='chk_severity'),
    )
    
    def __repr__(self):
        return f"<SecurityLog {self.action_type} - {self.severity}>"


class RateLimitEntry(Base):
    """
    Rate limiting tracking (brute force protection).
    
    Decisions: #41 (Admin security), #43 (Automated alerts)
    """
    __tablename__ = "rate_limit_entries"
    
    # Primary Key
    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tracking Keys
    identifier = Column(String(255), nullable=False)  # IP address or user ID
    action_type = Column(String(50), nullable=False)  # 'login_attempt' | 'api_call' | 'export_request'
    
    # Rate Limit Counters
    attempt_count = Column(Integer, nullable=False, default=1)
    window_start = Column(DateTime, nullable=False, server_default=func.now())
    window_end = Column(DateTime, nullable=False)
    
    # Blocking Status
    is_blocked = Column(Boolean, nullable=False, default=False)
    blocked_until = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<RateLimitEntry {self.identifier} - {self.action_type} - {self.attempt_count} attempts>"


class IPAllowlist(Base):
    """
    Allowed IP addresses for admin access.
    
    Decision #56: IP allowlist for admin security
    """
    __tablename__ = "ip_allowlist"
    
    # Primary Key
    allowlist_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # IP Address
    ip_address = Column(String(45), unique=True, nullable=False)  # IPv4 or IPv6
    description = Column(Text, nullable=True)
    
    # Admin tracking
    added_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    admin = relationship("User")
    
    def __repr__(self):
        return f"<IPAllowlist {self.ip_address} - Active: {self.is_active}>"


class FailedLoginAttempts(Base):
    """
    Track brute force login attempts.
    
    Decision #52: Rate limiting and brute force protection
    """
    __tablename__ = "failed_login_attempts"
    
    # Primary Key
    attempt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Attempt details
    email = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=False)  # IPv4 or IPv6
    attempted_at = Column(DateTime, nullable=False, server_default=func.now())
    user_agent = Column(Text, nullable=True)
    
    # Blocking status
    is_blocked = Column(Boolean, nullable=False, default=False)
    blocked_until = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<FailedLoginAttempt {self.email} from {self.ip_address} - Blocked: {self.is_blocked}>"
```

---

## Part 2: Pydantic Schemas (API Layer)

### 2.1 Schema Base Classes

**File:** `app/schemas/__init__.py`

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID

class BaseSchema(BaseModel):
    """
    Base schema for all Pydantic models.
    """
    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode (Pydantic v2)
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class TimestampMixin(BaseModel):
    """
    Mixin for timestamp fields.
    """
    created_at: datetime
    updated_at: datetime
```

---

### 2.2 Authentication Schemas

**File:** `app/schemas/auth.py`

```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from uuid import UUID

class UserRegister(BaseModel):
    """
    User registration request.
    
    Decision #53: Argon2id password hashing
    """
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Ensure password meets strength requirements"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class UserLogin(BaseModel):
    """
    User login request.
    """
    email: EmailStr
    password: str


class Token(BaseModel):
    """
    JWT token response.
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """
    JWT token payload data.
    """
    user_id: UUID
    email: str
    role: str


class TwoFactorSetup(BaseModel):
    """
    2FA setup response (Decision #50)
    """
    secret: str
    qr_code_url: str
    backup_codes: list[str]


class TwoFactorVerify(BaseModel):
    """
    2FA verification request (Decision #50)
    """
    code: str = Field(..., min_length=6, max_length=6)
```

---

### 2.3 User Schemas

**File:** `app/schemas/user.py`

```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from app.schemas import BaseSchema, TimestampMixin

class UserBase(BaseModel):
    """
    Base user fields (no sensitive data).
    """
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """
    User creation (includes password).
    """
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """
    User update (all fields optional).
    """
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None


class UserResponse(BaseSchema, TimestampMixin):
    """
    User response (public data).
    Decision #59: PII encrypted in database, decrypted for API
    """
    user_id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    is_active: bool
    email_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime]


class UserProfileCreate(BaseModel):
    """
    User profile creation (onboarding).
    Decision #10: 7-question onboarding
    """
    course_id: UUID
    referral_source: Optional[str] = None
    referral_source_detail: Optional[str] = None
    motivation: Optional[str] = None
    exam_date: Optional[date] = None
    current_level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    target_score_percentage: Optional[int] = Field(None, ge=70, le=100)
    daily_commitment_minutes: int = Field(..., ge=15, le=120)
    acquisition_channel: Optional[str] = None
    referral_code: Optional[str] = None


class UserProfileResponse(BaseSchema, TimestampMixin):
    """
    User profile response.
    """
    profile_id: UUID
    user_id: UUID
    course_id: UUID
    referral_source: Optional[str]
    motivation: Optional[str]
    exam_date: Optional[date]
    days_until_exam: Optional[int]
    current_level: str
    target_score_percentage: Optional[int]
    daily_commitment_minutes: int
```

---

### 2.4 Course Schemas

**File:** `app/schemas/course.py`

```python
from pydantic import BaseModel, Field
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
    version: str
    passing_score_percentage: int = Field(..., ge=0, le=100)


class CourseCreate(CourseBase):
    """
    Course creation (wizard step 1).
    Decision #65: Wizard-style course creation
    """
    exam_duration_minutes: Optional[int] = None
    total_questions: Optional[int] = None
    min_questions_required: int = 200
    min_chunks_required: int = 50


class CourseResponse(BaseSchema, TimestampMixin):
    """
    Course response.
    """
    course_id: UUID
    course_code: str
    course_name: str
    description: Optional[str]
    version: str
    status: str
    wizard_completed: bool
    passing_score_percentage: int
    exam_duration_minutes: Optional[int]
    total_questions: Optional[int]
    is_active: bool


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
    """
    course_id: UUID


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


class DomainBase(BaseModel):
    """
    Base domain fields.
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
```

---

### 2.5 Question Schemas

**File:** `app/schemas/question.py`

```python
from pydantic import BaseModel, Field
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


class AnswerChoiceResponse(BaseSchema):
    """
    Answer choice response (includes created_at only).
    """
    choice_id: UUID
    question_id: UUID
    choice_letter: str
    choice_text: str
    is_correct: bool
    explanation: Optional[str]
    created_at: datetime


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
    Decision #64: 1PL IRT (discrimination NULL for MVP)
    """
    course_id: UUID
    ka_id: UUID
    domain_id: Optional[UUID] = None
    answer_choices: List[AnswerChoiceBase] = Field(..., min_length=2, max_length=4)
    
    @validator('answer_choices')
    def validate_answer_choices(cls, v):
        """Ensure exactly one correct answer"""
        correct_count = sum(1 for choice in v if choice.is_correct)
        if correct_count != 1:
            raise ValueError('Must have exactly one correct answer')
        return v


class QuestionResponse(BaseSchema, TimestampMixin):
    """
    Question response (without correct answer).
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


class QuestionAttemptCreate(BaseModel):
    """
    Question attempt creation.
    """
    question_id: UUID
    session_id: Optional[UUID] = None
    selected_choice_id: UUID
    time_spent_seconds: Optional[int] = None


class QuestionAttemptResponse(BaseSchema):
    """
    Question attempt response (includes correctness).
    """
    attempt_id: UUID
    user_id: UUID
    question_id: UUID
    session_id: Optional[UUID]
    selected_choice_id: UUID
    is_correct: bool
    time_spent_seconds: Optional[int]
    competency_at_attempt: Optional[Decimal]
    attempted_at: datetime
```

---

### 2.6 Learning Schemas

**File:** `app/schemas/learning.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema, TimestampMixin

class UserCompetencyResponse(BaseSchema, TimestampMixin):
    """
    User competency response.
    Decision #8: Competency-based success criteria
    """
    competency_id: UUID
    user_id: UUID
    ka_id: UUID
    competency_score: Decimal = Field(..., ge=0, le=1)
    confidence_interval: Optional[Decimal]
    questions_attempted: int
    questions_correct: int
    accuracy_percentage: float  # Computed property
    last_practiced_at: Optional[datetime]


class SessionCreate(BaseModel):
    """
    Session creation.
    Decision #12: Daily sessions
    """
    session_type: str = Field(..., pattern="^(diagnostic|practice|review|mock_exam)$")


class SessionResponse(BaseSchema):
    """
    Session response.
    """
    session_id: UUID
    user_id: UUID
    session_type: str
    total_questions: int
    correct_answers: int
    accuracy_percentage: float  # Computed property
    duration_minutes: Optional[int]
    is_completed: bool
    started_at: datetime
    completed_at: Optional[datetime]


class DashboardResponse(BaseModel):
    """
    Dashboard data response.
    Decision #13: Progress dashboard design
    """
    user_id: UUID
    course_name: str
    exam_date: Optional[datetime]
    days_until_exam: Optional[int]
    competencies: List[UserCompetencyResponse]
    reviews_due_count: int
    exam_readiness_percentage: float
    total_questions_attempted: int
    overall_accuracy: float


class ReadingConsumedCreate(BaseModel):
    """
    Submit reading consumption.
    Decision #36: Reading recommendations
    """
    chunk_id: UUID
    time_spent_seconds: Optional[int] = None
    completed: bool = True
    was_helpful: Optional[bool] = None
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5)


class ReadingConsumedResponse(BaseSchema, TimestampMixin):
    """
    Reading consumption response.
    """
    reading_id: UUID
    user_id: UUID
    chunk_id: UUID
    read_at: datetime
    time_spent_seconds: Optional[int]
    completed: bool
    was_helpful: Optional[bool]
    difficulty_rating: Optional[int]
```

---

### 2.7 Financial Schemas

**File:** `app/schemas/financial.py`

```python
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema, TimestampMixin

class SubscriptionPlanResponse(BaseSchema, TimestampMixin):
    """
    Subscription plan response.
    Decision #55: Pricing strategy
    """
    plan_id: UUID
    course_id: UUID
    plan_name: str
    billing_interval: str
    price_amount: Decimal
    currency: str
    trial_period_days: int
    is_active: bool


class SubscriptionResponse(BaseSchema, TimestampMixin):
    """
    Subscription response.
    Decision #66: Financial infrastructure
    """
    subscription_id: UUID
    user_id: UUID
    plan_id: UUID
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    canceled_at: Optional[datetime]


class PaymentMethodCreate(BaseModel):
    """
    Payment method creation (Stripe token).
    """
    stripe_payment_method_id: str


class PaymentMethodResponse(BaseSchema, TimestampMixin):
    """
    Payment method response (masked).
    Decision #66: PCI compliant storage
    """
    method_id: UUID
    user_id: UUID
    method_type: str
    brand: Optional[str]
    last4: Optional[str]
    exp_month: Optional[int]
    exp_year: Optional[int]
    is_default: bool
    is_active: bool


class PaymentResponse(BaseSchema):
    """
    Payment response.
    """
    payment_id: UUID
    user_id: UUID
    subscription_id: Optional[UUID]
    amount: Decimal
    currency: str
    status: str
    payment_method_brand: Optional[str]
    payment_method_last4: Optional[str]
    created_at: datetime
    paid_at: Optional[datetime]


class RefundCreate(BaseModel):
    """
    Refund creation request.
    """
    payment_id: UUID
    amount: Optional[Decimal] = None  # Full refund if None
    reason: Optional[str] = None
    admin_notes: Optional[str] = None


class RefundResponse(BaseSchema):
    """
    Refund response.
    """
    refund_id: UUID
    payment_id: UUID
    user_id: UUID
    amount: Decimal
    currency: str
    reason: Optional[str]
    status: str
    created_at: datetime
    refunded_at: Optional[datetime]
```

---

### 2.8 Content Schemas

**File:** `app/schemas/content.py`

```python
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema, TimestampMixin

class ContentFeedbackCreate(BaseModel):
    """
    Submit feedback on content chunk.
    Decision #76: Content quality evaluation system
    """
    chunk_id: UUID
    was_helpful: bool
    feedback_text: Optional[str] = None


class ContentFeedbackResponse(BaseSchema, TimestampMixin):
    """
    Content feedback response.
    """
    feedback_id: UUID
    chunk_id: UUID
    user_id: UUID
    was_helpful: bool
    feedback_text: Optional[str]


class ContentEfficacyResponse(BaseSchema, TimestampMixin):
    """
    Content efficacy metrics.
    Decision #76: Content quality evaluation system
    """
    efficacy_id: UUID
    chunk_id: UUID
    user_id: UUID
    ka_id: UUID
    competency_before: Optional[Decimal]
    competency_after: Optional[Decimal]
    competency_change: Optional[Decimal]
    read_at: datetime
    measurement_window_days: int


class ContentChunkResponse(BaseSchema, TimestampMixin):
    """
    Content chunk response with quality metrics.
    Decision #76: Content quality evaluation
    """
    chunk_id: UUID
    course_id: UUID
    ka_id: UUID
    domain_id: Optional[UUID]
    content_title: Optional[str]
    content_text: str
    source_document: Optional[str]
    page_reference: Optional[str]
    difficulty_estimate: Optional[Decimal]
    word_count: Optional[int]
    estimated_read_time_minutes: Optional[int]
    expert_reviewed: bool
    review_status: str
    source_verified: bool
    is_active: bool
```

---

### 2.9 Security Schemas

**File:** `app/schemas/security.py`

```python
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.schemas import BaseSchema, TimestampMixin

class IPAllowlistCreate(BaseModel):
    """
    Add IP to allowlist.
    Decision #56: IP allowlist for admin security
    """
    ip_address: str
    description: Optional[str] = None


class IPAllowlistResponse(BaseSchema, TimestampMixin):
    """
    IP allowlist entry.
    """
    allowlist_id: UUID
    ip_address: str
    description: Optional[str]
    added_by: UUID
    is_active: bool


class FailedLoginAttemptResponse(BaseSchema):
    """
    Failed login attempt record.
    Decision #52: Rate limiting and brute force protection
    """
    attempt_id: UUID
    email: str
    ip_address: str
    attempted_at: datetime
    user_agent: Optional[str]
    is_blocked: bool
    blocked_until: Optional[datetime]


class SecurityLogResponse(BaseSchema):
    """
    Security audit log entry.
    Decision #41: Admin security
    """
    log_id: UUID
    admin_user_id: Optional[UUID]
    target_user_id: Optional[UUID]
    action_type: str
    action_description: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    severity: str
    created_at: datetime
```

---

### 2.10 Reading Schemas

**File:** `app/schemas/reading.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.schemas import BaseSchema, TimestampMixin

class ReadingConsumedCreate(BaseModel):
    """
    Track content reading.
    Decision #36: Reading recommendations
    """
    chunk_id: UUID
    time_spent_seconds: Optional[int] = None
    completed: bool = True
    was_helpful: Optional[bool] = None
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5)


class ReadingConsumedResponse(BaseSchema, TimestampMixin):
    """
    Reading consumption record.
    """
    reading_id: UUID
    user_id: UUID
    chunk_id: UUID
    read_at: datetime
    time_spent_seconds: Optional[int]
    completed: bool
    was_helpful: Optional[bool]
    difficulty_rating: Optional[int]


class ReadingRecommendationResponse(BaseModel):
    """
    Recommended reading content.
    Decision #36: Reading recommendations
    """
    chunk_id: UUID
    content_title: Optional[str]
    content_text: str
    ka_name: str
    domain_name: Optional[str]
    difficulty_estimate: Optional[float]
    estimated_read_time_minutes: Optional[int]
    relevance_score: float
    reason: str  # Why recommended
```

---

## Part 3: Utility Functions

### 3.1 Encryption Utilities

**File:** `app/utils/encryption.py`

```python
from cryptography.fernet import Fernet
import os
import base64

# Load encryption key from environment
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY environment variable not set")

# Initialize Fernet cipher
cipher = Fernet(ENCRYPTION_KEY.encode())


def encrypt_field(plaintext: str) -> str:
    """
    Encrypt a field value.
    
    Decision #59: Application-level encryption for PII
    
    Args:
        plaintext: The plain text value
        
    Returns:
        Encrypted base64-encoded string
    """
    if not plaintext:
        return plaintext
    
    encrypted_bytes = cipher.encrypt(plaintext.encode())
    return base64.b64encode(encrypted_bytes).decode()


def decrypt_field(ciphertext: str) -> str:
    """
    Decrypt a field value.
    
    Args:
        ciphertext: The encrypted base64-encoded string
        
    Returns:
        Decrypted plain text value
    """
    if not ciphertext:
        return ciphertext
    
    encrypted_bytes = base64.b64decode(ciphertext.encode())
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    return decrypted_bytes.decode()


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        Base64-encoded encryption key
    """
    return Fernet.generate_key().decode()
```

---

### 3.2 Custom Validators

**File:** `app/utils/validators.py`

```python
from pydantic import validator
from typing import Any
import re

def validate_password_strength(v: str) -> str:
    """
    Validate password strength.
    
    Decision #53: Strong password requirements
    
    Rules:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(v) < 8:
        raise ValueError('Password must be at least 8 characters long')
    
    if not re.search(r'[A-Z]', v):
        raise ValueError('Password must contain at least one uppercase letter')
    
    if not re.search(r'[a-z]', v):
        raise ValueError('Password must contain at least one lowercase letter')
    
    if not re.search(r'\d', v):
        raise ValueError('Password must contain at least one digit')
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        raise ValueError('Password must contain at least one special character')
    
    return v


def validate_email_domain_blocklist(v: str) -> str:
    """
    Validate email against domain blocklist.
    
    Prevents disposable email addresses.
    """
    blocklist = [
        'tempmail.com',
        '10minutemail.com',
        'guerrillamail.com',
        'mailinator.com'
    ]
    
    domain = v.split('@')[1].lower()
    if domain in blocklist:
        raise ValueError('Email domain is not allowed')
    
    return v


def validate_ka_weights_sum_to_100(knowledge_areas: list) -> list:
    """
    Validate that knowledge area weights sum to 100%.
    
    Decision #63: Per-course weight validation
    """
    total_weight = sum(ka.weight_percentage for ka in knowledge_areas)
    
    if abs(total_weight - 100.00) > 0.01:  # Allow for floating point precision
        raise ValueError(f'Knowledge area weights must sum to 100%, got {total_weight}%')
    
    return knowledge_areas
```

---

## Part 4: Model Usage Examples

### 4.1 User Creation

```python
from app.models.user import User, UserProfile
from app.schemas.user import UserCreate, UserProfileCreate
from app.utils.encryption import encrypt_field
from argon2 import PasswordHasher
from sqlalchemy.orm import Session

# Password hashing (Decision #53)
ph = PasswordHasher()

def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user account"""
    
    # Hash password with Argon2id
    password_hash = ph.hash(user_data.password)
    
    # Create user (encryption happens automatically via hybrid properties)
    db_user = User(
        email=user_data.email,  # Encrypted automatically
        password_hash=password_hash,
        first_name=user_data.first_name,  # Encrypted automatically
        last_name=user_data.last_name,  # Encrypted automatically
        role='learner'
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def create_user_profile(db: Session, user_id: UUID, profile_data: UserProfileCreate) -> UserProfile:
    """Create user profile during onboarding"""
    
    # Calculate days until exam
    days_until_exam = None
    if profile_data.exam_date:
        days_until_exam = (profile_data.exam_date - datetime.now().date()).days
    
    db_profile = UserProfile(
        user_id=user_id,
        course_id=profile_data.course_id,
        referral_source=profile_data.referral_source,
        motivation=profile_data.motivation,
        exam_date=profile_data.exam_date,
        days_until_exam=days_until_exam,
        current_level=profile_data.current_level,
        target_score_percentage=profile_data.target_score_percentage,
        daily_commitment_minutes=profile_data.daily_commitment_minutes,
        acquisition_channel=profile_data.acquisition_channel,
        referral_code=profile_data.referral_code
    )
    
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    
    return db_profile
```

### 4.2 Question Creation

```python
from app.models.question import Question, AnswerChoice
from app.schemas.question import QuestionCreate
from sqlalchemy.orm import Session

def create_question(db: Session, question_data: QuestionCreate) -> Question:
    """Create a question with answer choices"""
    
    # Create question (Decision #64: discrimination NULL for 1PL IRT)
    db_question = Question(
        course_id=question_data.course_id,
        ka_id=question_data.ka_id,
        domain_id=question_data.domain_id,
        question_text=question_data.question_text,
        question_type=question_data.question_type,
        difficulty=question_data.difficulty,
        discrimination=None,  # NULL for MVP
        source=question_data.source
    )
    
    db.add(db_question)
    db.flush()  # Get question_id without committing
    
    # Create answer choices
    for choice_data in question_data.answer_choices:
        db_choice = AnswerChoice(
            question_id=db_question.question_id,
            choice_letter=choice_data.choice_letter,
            choice_text=choice_data.choice_text,
            is_correct=choice_data.is_correct,
            explanation=choice_data.explanation
        )
        db.add(db_choice)
    
    db.commit()
    db.refresh(db_question)
    
    return db_question
```

### 4.3 Competency Update

```python
from app.models.learning import UserCompetency
from sqlalchemy.orm import Session
from decimal import Decimal

def update_competency(db: Session, user_id: UUID, ka_id: UUID, new_score: Decimal) -> UserCompetency:
    """Update user competency for a knowledge area"""
    
    # Find existing competency record
    competency = db.query(UserCompetency).filter(
        UserCompetency.user_id == user_id,
        UserCompetency.ka_id == ka_id
    ).first()
    
    if not competency:
        # Create new competency record
        competency = UserCompetency(
            user_id=user_id,
            ka_id=ka_id,
            competency_score=new_score,
            questions_attempted=1,
            questions_correct=1 if new_score > 0.5 else 0,
            last_practiced_at=datetime.now()
        )
        db.add(competency)
    else:
        # Update existing record
        competency.competency_score = new_score
        competency.questions_attempted += 1
        competency.last_practiced_at = datetime.now()
    
    db.commit()
    db.refresh(competency)
    
    return competency
```

---

## Part 5: Database Indexes (Performance)

### 5.1 Critical Indexes

All indexes are defined in `TDDoc_DatabaseSchema.md`, but here are the most critical for model performance:

```sql
-- User lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_stripe ON users(stripe_customer_id);

-- Competency queries
CREATE INDEX idx_competency_user_ka ON user_competency(user_id, ka_id);

-- Question selection
CREATE INDEX idx_questions_course_ka ON questions(course_id, ka_id, difficulty);

-- Session retrieval
CREATE INDEX idx_sessions_user ON sessions(user_id, started_at DESC);

-- Spaced repetition
CREATE INDEX idx_sr_cards_due ON spaced_repetition_cards(user_id, next_review_at) WHERE is_due = true;

-- Financial queries
CREATE INDEX idx_payments_user ON payments(user_id, created_at DESC);
CREATE INDEX idx_subscriptions_user ON subscriptions(user_id, status);
```

---

## Part 6: Testing Guidance

### 6.1 Model Tests

```python
# Test user encryption
def test_user_email_encryption():
    user = User(email="test@example.com", ...)
    assert user._email != "test@example.com"  # Encrypted in DB
    assert user.email == "test@example.com"   # Decrypted on access

# Test competency score constraints
def test_competency_score_range():
    with pytest.raises(ValueError):
        competency = UserCompetency(competency_score=1.5)  # Out of range

# Test KA weight validation
def test_ka_weights_sum_to_100():
    kas = [
        KnowledgeArea(weight_percentage=50),
        KnowledgeArea(weight_percentage=30)
    ]
    with pytest.raises(ValueError):
        validate_ka_weights_sum_to_100(kas)  # Only sums to 80%
```

---

## Next Steps

After this document is approved:
1. âœ… Database Schema (Complete)
2. ðŸ”„ Data Models (This Document - In Progress)
3. â³ API Endpoints (TDDoc_API_Endpoints.md)
4. â³ Algorithm Specifications (TDDoc_Algorithms.md)
5. â³ Write Tests (using TDDocs as spec)
6. â³ Implement Code (TDD red-green-refactor)

---

**Status:** DRAFT - IN PROGRESS  
**Version:** 1.0  
**Completion:** ~80% complete

**Remaining Work:**
- Add more Pydantic schema examples
- Add validation test examples
- Add relationship loading examples
- Add migration script templates

---

**Key Design Decisions Implemented:**
- âœ… SQLAlchemy 2.0+ with type hints
- âœ… Pydantic v2 for API validation
- âœ… Field-level encryption for PII (Decision #59)
- âœ… 1PL IRT with 2PL upgrade path (Decision #64)
- âœ… Multi-course extensibility (Decision #63)
- âœ… Financial infrastructure (Decision #66)
- âœ… Hybrid properties for encryption
- âœ… Comprehensive validation rules
- âœ… Security-first design
