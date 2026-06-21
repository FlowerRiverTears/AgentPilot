"""Pagination utilities for list endpoints."""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response envelope."""
    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool


def compute_pagination(total: int, limit: int, offset: int) -> dict[str, bool]:
    """Compute pagination metadata."""
    return {"has_more": offset + limit < total}


DEFAULT_LIMIT = 50
MAX_LIMIT = 200
