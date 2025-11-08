"""
Base Pydantic schemas for API validation.

All schemas inherit from BaseSchema for consistent configuration.
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class BaseSchema(BaseModel):
    """
    Base schema for all Pydantic models.

    Configured for SQLAlchemy ORM compatibility (Pydantic v2).
    """
    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode (Pydantic v2)
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class TimestampMixin(BaseModel):
    """
    Mixin for timestamp fields (created_at, updated_at).

    Used for models that track creation and modification times.
    """
    created_at: datetime
    updated_at: datetime
