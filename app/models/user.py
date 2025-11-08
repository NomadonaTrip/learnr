"""
User models: User and UserProfile.

Includes field-level encryption for PII (Decision #59).
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, DECIMAL, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from app.models.database import Base
from app.utils.encryption import encrypt_field, decrypt_field
import uuid
from typing import Optional


class User(Base):
    """
    User accounts and authentication.

    Decisions: #50 (2FA), #53 (Argon2id), #59 (PII encryption), #66 (Stripe), #79 (Bootstrap)
    """
    __tablename__ = "users"

    # Primary Key
    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

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
    security_logs = relationship("SecurityLog", foreign_keys="SecurityLog.user_id", back_populates="user")
    admin_security_logs = relationship("SecurityLog", foreign_keys="SecurityLog.admin_user_id", back_populates="admin_user")
    reading_consumed = relationship("ReadingConsumed", back_populates="user", cascade="all, delete-orphan")

    # Hybrid Properties for Encryption (Decision #59)
    @hybrid_property
    def email(self) -> str:
        """Decrypt email when accessed"""
        if isinstance(self._email, str):
            return decrypt_field(self._email)
        return self._email  # Return column during class-level access

    @email.setter
    def email(self, value: str):
        """Encrypt email when set"""
        self._email = encrypt_field(value)

    @hybrid_property
    def first_name(self) -> str:
        """Decrypt first_name when accessed"""
        if isinstance(self._first_name, str):
            return decrypt_field(self._first_name)
        return self._first_name  # Return column during class-level access

    @first_name.setter
    def first_name(self, value: str):
        """Encrypt first_name when set"""
        self._first_name = encrypt_field(value)

    @hybrid_property
    def last_name(self) -> str:
        """Decrypt last_name when accessed"""
        if isinstance(self._last_name, str):
            return decrypt_field(self._last_name)
        return self._last_name  # Return column during class-level access

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
    profile_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, unique=True)
    course_id = Column(String(36), ForeignKey('courses.course_id'), nullable=False)

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
