"""
Security models: SecurityLog and RateLimitEntry.

Immutable audit trail and rate limiting (Decision #56).
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import uuid


class SecurityLog(Base):
    """
    Immutable audit trail for security events.

    Cannot be updated or deleted - permanent record for compliance.
    """
    __tablename__ = "security_logs"

    # Primary Key
    log_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Actor (who performed the action)
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=True)  # NULL for system events
    admin_user_id = Column(String(36), ForeignKey('users.user_id'), nullable=True)  # For admin actions

    # Event Details
    event_type = Column(String(50), nullable=False)  # 'login' | 'failed_login' | 'role_changed' | 'bootstrap_admin_created'
    event_category = Column(String(30), nullable=False, default='authentication')  # 'authentication' | 'authorization' | 'data_access'

    # Request Context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    request_path = Column(String(255), nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, etc.

    # Event Outcome
    success = Column(Boolean, nullable=False)
    failure_reason = Column(Text, nullable=True)

    # Additional Context (renamed from 'metadata' which is reserved in SQLAlchemy)
    event_metadata = Column(JSON, nullable=True)  # Flexible storage for event-specific data

    # Timestamp (immutable - no updated_at)
    occurred_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="security_logs")
    admin_user = relationship("User", foreign_keys=[admin_user_id], back_populates="admin_security_logs")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_security_logs_user', 'user_id', 'occurred_at'),
        Index('idx_security_logs_event_type', 'event_type', 'occurred_at'),
        Index('idx_security_logs_failed_logins', 'event_type', 'success', 'ip_address', 'occurred_at'),
    )

    def __repr__(self):
        return f"<SecurityLog {self.log_id} - {self.event_type} - {'✓' if self.success else '✗'}>"


class RateLimitEntry(Base):
    """
    Rate limiting tracking per user/IP.

    Prevents abuse and brute force attacks.
    Decision #56: Rate limiting 100 req/min for authenticated users
    """
    __tablename__ = "rate_limit_entries"

    # Primary Key
    entry_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Identifier (user_id OR ip_address, not both)
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Rate Limit Tracking
    endpoint = Column(String(255), nullable=False)  # API endpoint being rate limited
    request_count = Column(Integer, nullable=False, default=1)
    window_start = Column(DateTime, nullable=False, server_default=func.now())
    window_end = Column(DateTime, nullable=False)

    # Status
    is_blocked = Column(Boolean, nullable=False, default=False)
    blocked_until = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")

    # Indexes for performance
    __table_args__ = (
        Index('idx_rate_limit_user', 'user_id', 'endpoint', 'window_end'),
        Index('idx_rate_limit_ip', 'ip_address', 'endpoint', 'window_end'),
    )

    def __repr__(self):
        identifier = f"User {self.user_id}" if self.user_id else f"IP {self.ip_address}"
        return f"<RateLimitEntry {self.entry_id} - {identifier} - {self.request_count} reqs>"
