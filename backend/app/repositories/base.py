"""Base repository with common utilities."""
import uuid
from typing import Optional

from app.db.session import AsyncSessionLocal


def maybe_uuid(value) -> Optional[uuid.UUID]:
    """Convert a value to UUID if possible, otherwise return None."""
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return None


def to_uuid(value: str) -> uuid.UUID:
    """Convert a string to UUID, raising ValueError if invalid."""
    return uuid.UUID(str(value))
