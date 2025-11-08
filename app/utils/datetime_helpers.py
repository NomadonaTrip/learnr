"""
Datetime utility functions.

Provides helpers for timezone-aware datetime handling.
"""
from datetime import datetime, timezone
from typing import Optional


def ensure_timezone_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure a datetime object is timezone-aware (UTC).

    If the datetime is naive (no timezone info), it assumes UTC
    and adds timezone information.

    Args:
        dt: Datetime object (may be naive or aware)

    Returns:
        Timezone-aware datetime in UTC, or None if input was None

    Examples:
        >>> naive_dt = datetime(2025, 1, 1, 12, 0, 0)
        >>> aware_dt = ensure_timezone_aware(naive_dt)
        >>> aware_dt.tzinfo
        datetime.timezone.utc
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)

    # Already timezone-aware
    return dt
