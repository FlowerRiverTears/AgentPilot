from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from uuid import UUID

from app.core.deps import get_current_user, get_optional_user
from app.db.session import AsyncSessionLocal
from app.models import Agent
from app.models.feedback import Feedback
from app.schemas.auth import UserInfo

router = APIRouter()


class FeedbackCreate(BaseModel):
    run_id: str | None = None
    agent_id: str | None = None
    rating: str = Field(min_length=1, max_length=20)  # "like" or "dislike"
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


def _maybe_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


@router.post("", response_model=FeedbackOut, status_code=201)
async def create_feedback(
    payload: FeedbackCreate,
    _user: UserInfo | None = Depends(get_optional_user),
) -> FeedbackOut:
    """创建反馈记录，前台匿名也可提交。"""
    if payload.rating not in {"like", "dislike"}:
        raise HTTPException(status_code=400, detail="rating 必须是 like 或 dislike")

    run_uuid = _maybe_uuid(payload.run_id)
    agent_uuid = _maybe_uuid(payload.agent_id)

    async with AsyncSessionLocal() as session:
        feedback = Feedback(
            run_id=run_uuid,
            agent_id=agent_uuid,
            rating=payload.rating,
            comment=payload.comment or "",
        )
        session.add(feedback)
        await session.commit()
        await session.refresh(feedback)
        return FeedbackOut(
            id=str(feedback.id),
            run_id=str(feedback.run_id) if feedback.run_id else None,
            agent_id=str(feedback.agent_id) if feedback.agent_id else None,
            rating=feedback.rating,
            comment=feedback.comment,
            created_at=feedback.created_at.isoformat() if feedback.created_at else "",
        )


@router.get("", response_model=list[FeedbackOut])
async def list_feedback(
    agent_id: str | None = None,
    _user: UserInfo = Depends(get_current_user),
) -> list[FeedbackOut]:
    """后台查询反馈列表，支持按 agent_id 过滤。"""
    async with AsyncSessionLocal() as session:
        stmt = select(Feedback).order_by(Feedback.created_at.desc())
        agent_uuid = _maybe_uuid(agent_id)
        if agent_uuid:
            stmt = stmt.where(Feedback.agent_id == agent_uuid)
        rows = (await session.execute(stmt)).scalars().all()
        return [
            FeedbackOut(
                id=str(item.id),
                run_id=str(item.run_id) if item.run_id else None,
                agent_id=str(item.agent_id) if item.agent_id else None,
                rating=item.rating,
                comment=item.comment,
                created_at=item.created_at.isoformat() if item.created_at else "",
            )
            for item in rows
        ]


@router.get("/stats", response_model=list[FeedbackStatItem])
async def feedback_stats(
    _user: UserInfo = Depends(get_current_user),
) -> list[FeedbackStatItem]:
    """统计每个智能体的点赞/点踩数量。"""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(
                Feedback.agent_id,
                Agent.name,
                func.count().filter(Feedback.rating == "like").label("likes"),
                func.count().filter(Feedback.rating == "dislike").label("dislikes"),
            )
            .outerjoin(Agent, Agent.id == Feedback.agent_id)
            .group_by(Feedback.agent_id, Agent.name)
            .order_by(Feedback.agent_id.asc())
        )
        rows = (await session.execute(stmt)).all()
        return [
            FeedbackStatItem(
                agent_id=str(agent_id) if agent_id else None,
                agent_name=agent_name,
                likes=int(likes or 0),
                dislikes=int(dislikes or 0),
            )
            for agent_id, agent_name, likes, dislikes in rows
        ]
