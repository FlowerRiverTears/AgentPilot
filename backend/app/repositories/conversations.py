from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select

from app.db.session import AsyncSessionLocal
from app.models.conversation import Conversation


def _maybe_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


class ConversationStore:
    """对话记忆管理仓库。"""

    async def list_conversations(self, agent_id: str | None = None) -> list[dict]:
        """查询会话列表，按 updated_at desc 排序。"""
        async with AsyncSessionLocal() as session:
            stmt = select(Conversation).order_by(Conversation.updated_at.desc())
            agent_uuid = _maybe_uuid(agent_id)
            if agent_uuid:
                stmt = stmt.where(Conversation.agent_id == agent_uuid)
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "id": str(item.id),
                    "agent_id": str(item.agent_id),
                    "session_id": item.session_id,
                    "title": item.title,
                    "message_count": len(item.messages) if isinstance(item.messages, list) else 0,
                    "created_at": item.created_at.isoformat() if item.created_at else "",
                    "updated_at": item.updated_at.isoformat() if item.updated_at else "",
                }
                for item in rows
            ]

    async def get_conversation(self, conversation_id: str) -> dict | None:
        """获取单个会话详情（含 messages）。"""
        conv_uuid = _maybe_uuid(conversation_id)
        if not conv_uuid:
            return None
        async with AsyncSessionLocal() as session:
            item = await session.get(Conversation, conv_uuid)
            if not item:
                return None
            return {
                "id": str(item.id),
                "agent_id": str(item.agent_id),
                "session_id": item.session_id,
                "title": item.title,
                "messages": list(item.messages) if isinstance(item.messages, list) else [],
                "summary": item.summary or "",
                "summary_to_turn": int(item.summary_to_turn or 0),
                "created_at": item.created_at.isoformat() if item.created_at else "",
                "updated_at": item.updated_at.isoformat() if item.updated_at else "",
            }

    async def create_or_update_conversation(
        self,
        agent_id: str,
        session_id: str,
        title: str,
        messages: list[dict],
        summary: str = "",
        summary_to_turn: int = 0,
    ) -> dict:
        """按 session_id upsert 会话。"""
        agent_uuid = _maybe_uuid(agent_id)
        if not agent_uuid:
            raise ValueError("无效的 agent_id")

        async with AsyncSessionLocal() as session:
            stmt = select(Conversation).where(
                Conversation.agent_id == agent_uuid,
                Conversation.session_id == session_id,
            )
            existing = (await session.execute(stmt)).scalars().first()

            if existing:
                existing.title = title or existing.title
                existing.messages = list(messages) if messages else existing.messages
                if summary:
                    existing.summary = summary
                if summary_to_turn:
                    existing.summary_to_turn = summary_to_turn
                await session.commit()
                await session.refresh(existing)
                item = existing
            else:
                conv = Conversation(
                    agent_id=agent_uuid,
                    session_id=session_id,
                    title=title or "",
                    messages=list(messages) if messages else [],
                    summary=summary or "",
                    summary_to_turn=int(summary_to_turn or 0),
                )
                session.add(conv)
                await session.commit()
                await session.refresh(conv)
                item = conv

            return {
                "id": str(item.id),
                "agent_id": str(item.agent_id),
                "session_id": item.session_id,
                "title": item.title,
                "messages": list(item.messages) if isinstance(item.messages, list) else [],
                "summary": item.summary or "",
                "summary_to_turn": int(item.summary_to_turn or 0),
                "created_at": item.created_at.isoformat() if item.created_at else "",
                "updated_at": item.updated_at.isoformat() if item.updated_at else "",
            }

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话。"""
        conv_uuid = _maybe_uuid(conversation_id)
        if not conv_uuid:
            return False
        async with AsyncSessionLocal() as session:
            item = await session.get(Conversation, conv_uuid)
            if not item:
                return False
            await session.delete(item)
            await session.commit()
            return True

    async def search_conversations(self, keyword: str) -> list[dict]:
        """按 title 模糊搜索会话。"""
        if not keyword:
            return []
        pattern = f"%{keyword}%"
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Conversation)
                .where(or_(Conversation.title.ilike(pattern),))
                .order_by(Conversation.updated_at.desc())
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "id": str(item.id),
                    "agent_id": str(item.agent_id),
                    "session_id": item.session_id,
                    "title": item.title,
                    "message_count": len(item.messages) if isinstance(item.messages, list) else 0,
                    "created_at": item.created_at.isoformat() if item.created_at else "",
                    "updated_at": item.updated_at.isoformat() if item.updated_at else "",
                }
                for item in rows
            ]


conversation_store = ConversationStore()
