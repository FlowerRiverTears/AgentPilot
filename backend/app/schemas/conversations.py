"""Conversation schemas."""
from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: str
    content: str


class ConversationUpsert(BaseModel):
    agent_id: str
    session_id: str = Field(min_length=1, max_length=80)
    title: str = ""
    messages: list[ConversationMessage] = Field(default_factory=list)
    summary: str = ""
    summary_to_turn: int = 0
