from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_optional_user
from app.core.config import settings
from app.repositories.conversations import get_conversation_store
from app.schemas.auth import UserInfo
from app.schemas.conversations import ConversationMessage, ConversationUpsert

router = APIRouter()


@router.get("")
async def list_conversations(
    agent_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user: UserInfo | None = Depends(get_optional_user),
) -> list[dict]:
    """查询会话列表，支持按 agent_id 过滤。"""
    return await conversation_store.list_conversations(agent_id=agent_id, limit=limit, offset=offset)


@router.get("/search")
async def search_conversations(
    q: str = "",
    _user: UserInfo | None = Depends(get_optional_user),
) -> list[dict]:
    """按 title 模糊搜索会话。"""
    return await conversation_store.search_conversations(q)


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    _user: UserInfo | None = Depends(get_optional_user),
) -> dict:
    """获取会话详情。"""
    conv = await conversation_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("", status_code=200)
async def upsert_conversation(
    payload: ConversationUpsert,
    _user: UserInfo | None = Depends(get_optional_user),
) -> dict:
    """创建或更新会话。"""
    try:
        return await conversation_store.create_or_update_conversation(
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            title=payload.title,
            messages=[m.model_dump() for m in payload.messages],
            summary=payload.summary,
            summary_to_turn=payload.summary_to_turn,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    _user: UserInfo | None = Depends(get_optional_user),
) -> None:
    """删除会话。"""
    if settings.auth_enabled and not _user:
        raise HTTPException(status_code=401, detail="Authentication required")
    deleted = await conversation_store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
