"""Initial schema with indexes

Revision ID: 001
Revises: None
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Critical indexes for query performance
    op.create_index("ix_agent_runs_agent_id", "agent_runs", ["agent_id"])
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_embedding", "document_chunks", ["embedding"], postgresql_using="ivfflat", postgresql_with={"lists": 100}, postgresql_ops={"embedding": "vector_cosine_ops"})
    op.create_index("ix_documents_knowledge_base_id", "documents", ["knowledge_base_id"])
    op.create_index("ix_conversations_agent_session", "conversations", ["agent_id", "session_id"])
    op.create_index("ix_conversations_agent_id", "conversations", ["agent_id"])
    op.create_index("ix_feedback_agent_id", "feedbacks", ["agent_id"])
    op.create_index("ix_feedback_run_id", "feedbacks", ["run_id"])
    op.create_index("ix_tool_calls_run_id", "tool_calls", ["run_id"])
    op.create_index("ix_tool_calls_tool_id", "tool_calls", ["tool_id"])
    op.create_index("ix_eval_results_dataset_id", "eval_results", ["dataset_id"])
    op.create_index("ix_run_steps_run_id", "run_steps", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_steps_run_id")
    op.drop_index("ix_eval_results_dataset_id")
    op.drop_index("ix_tool_calls_tool_id")
    op.drop_index("ix_tool_calls_run_id")
    op.drop_index("ix_feedback_run_id")
    op.drop_index("ix_feedback_agent_id")
    op.drop_index("ix_conversations_agent_id")
    op.drop_index("ix_conversations_agent_session")
    op.drop_index("ix_documents_knowledge_base_id")
    op.drop_index("ix_document_chunks_embedding")
    op.drop_index("ix_document_chunks_document_id")
    op.drop_index("ix_agent_runs_created_at")
    op.drop_index("ix_agent_runs_agent_id")
