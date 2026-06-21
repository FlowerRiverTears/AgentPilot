"""Feedback schemas."""
from typing import Literal

from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    run_id: str | None = None
    agent_id: str | None = None
    rating: Literal["like", "dislike"]
    comment: str = ""


class FeedbackOut(BaseModel):
    id: str
    run_id: str | None = None
    agent_id: str | None = None
    rating: str
    comment: str
    created_at: str


class FeedbackStatItem(BaseModel):
    agent_id: str | None = None
    agent_name: str | None = None
    likes: int = 0
    dislikes: int = 0
