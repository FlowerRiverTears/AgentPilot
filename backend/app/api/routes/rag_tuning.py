from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.deps import get_current_user
from app.db.session import AsyncSessionLocal
from app.models.knowledge import KnowledgeBase
from app.models.rag_config import RagConfig
from app.repositories.memory import store
from app.schemas.rag_tuning import (
    RagConfigRead,
    RagConfigUpdate,
    RetrievalTestRequest,
    RetrievalTestResult,
)

router = APIRouter()

# 默认 RAG 配置（知识库未显式配置时使用）
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_TOP_K = 5
DEFAULT_SCORE_THRESHOLD = 0.3
DEFAULT_WEIGHT_VECTOR = 0.7
DEFAULT_WEIGHT_LEXICAL = 0.3


def _to_read(kb: KnowledgeBase, config: RagConfig | None) -> RagConfigRead:
    """将知识库与其 RAG 配置（可能为空）转换为响应模型。"""
    if config is not None:
        return RagConfigRead(
            knowledge_base_id=str(kb.id),
            knowledge_base_name=kb.name,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            top_k=config.top_k,
            score_threshold=config.score_threshold,
            retrieval_weight_vector=config.retrieval_weight_vector,
            retrieval_weight_lexical=config.retrieval_weight_lexical,
        )
    return RagConfigRead(
        knowledge_base_id=str(kb.id),
        knowledge_base_name=kb.name,
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        top_k=DEFAULT_TOP_K,
        score_threshold=DEFAULT_SCORE_THRESHOLD,
        retrieval_weight_vector=DEFAULT_WEIGHT_VECTOR,
        retrieval_weight_lexical=DEFAULT_WEIGHT_LEXICAL,
    )


def _parse_kb_id(knowledge_base_id: str) -> uuid.UUID:
    """将字符串转换为 UUID，非法时抛出 404。"""
    try:
        return uuid.UUID(knowledge_base_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=404, detail="Knowledge base not found") from exc


@router.get("/configs", response_model=list[RagConfigRead])
async def list_rag_configs(_user=Depends(get_current_user)) -> list[RagConfigRead]:
    """列出所有知识库的 RAG 配置（没有则使用默认值）。"""
    async with AsyncSessionLocal() as session:
        kbs = (
            await session.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
        ).scalars().all()

        configs: dict[uuid.UUID, RagConfig] = {}
        if kbs:
            config_rows = (
                await session.execute(select(RagConfig))
            ).scalars().all()
            configs = {cfg.knowledge_base_id: cfg for cfg in config_rows}

        return [_to_read(kb, configs.get(kb.id)) for kb in kbs]


@router.get("/configs/{knowledge_base_id}", response_model=RagConfigRead)
async def get_rag_config(knowledge_base_id: str, _user=Depends(get_current_user)) -> RagConfigRead:
    """获取指定知识库的 RAG 配置（没有则返回默认值）。"""
    kb_uuid = _parse_kb_id(knowledge_base_id)
    async with AsyncSessionLocal() as session:
        kb = await session.get(KnowledgeBase, kb_uuid)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        config = (
            await session.execute(
                select(RagConfig).where(RagConfig.knowledge_base_id == kb_uuid)
            )
        ).scalars().first()
        return _to_read(kb, config)


@router.put("/configs/{knowledge_base_id}", response_model=RagConfigRead)
async def update_rag_config(
    knowledge_base_id: str,
    payload: RagConfigUpdate,
    _user=Depends(get_current_user),
) -> RagConfigRead:
    """更新（或创建）指定知识库的 RAG 配置。"""
    kb_uuid = _parse_kb_id(knowledge_base_id)
    async with AsyncSessionLocal() as session:
        kb = await session.get(KnowledgeBase, kb_uuid)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        config = (
            await session.execute(
                select(RagConfig).where(RagConfig.knowledge_base_id == kb_uuid)
            )
        ).scalars().first()

        if config is None:
            # 不存在则使用默认值创建
            config = RagConfig(
                knowledge_base_id=kb.id,
                chunk_size=DEFAULT_CHUNK_SIZE,
                chunk_overlap=DEFAULT_CHUNK_OVERLAP,
                top_k=DEFAULT_TOP_K,
                score_threshold=DEFAULT_SCORE_THRESHOLD,
                retrieval_weight_vector=DEFAULT_WEIGHT_VECTOR,
                retrieval_weight_lexical=DEFAULT_WEIGHT_LEXICAL,
            )
            session.add(config)

        # 仅更新请求中显式提供的字段
        if payload.chunk_size is not None:
            config.chunk_size = payload.chunk_size
        if payload.chunk_overlap is not None:
            config.chunk_overlap = payload.chunk_overlap
        if payload.top_k is not None:
            config.top_k = payload.top_k
        if payload.score_threshold is not None:
            config.score_threshold = payload.score_threshold
        if payload.retrieval_weight_vector is not None:
            config.retrieval_weight_vector = payload.retrieval_weight_vector
        if payload.retrieval_weight_lexical is not None:
            config.retrieval_weight_lexical = payload.retrieval_weight_lexical

        await session.commit()
        await session.refresh(config)
        return _to_read(kb, config)


@router.post("/test", response_model=RetrievalTestResult)
async def retrieval_test(
    payload: RetrievalTestRequest,
    _user=Depends(get_current_user),
) -> RetrievalTestResult:
    """检索测试：使用指定知识库的 RAG 配置实时验证检索效果。"""
    kb_uuid = _parse_kb_id(payload.knowledge_base_id)

    # 读取该知识库的 RAG 配置，用于回填默认 top_k / score_threshold
    async with AsyncSessionLocal() as session:
        kb = await session.get(KnowledgeBase, kb_uuid)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        config = (
            await session.execute(
                select(RagConfig).where(RagConfig.knowledge_base_id == kb_uuid)
            )
        ).scalars().first()

    # 优先使用请求参数，其次使用知识库配置，最后使用全局默认值
    top_k = payload.top_k or (config.top_k if config else DEFAULT_TOP_K)
    score_threshold = (
        payload.score_threshold
        if payload.score_threshold is not None
        else (config.score_threshold if config else DEFAULT_SCORE_THRESHOLD)
    )

    # 调用现有的检索方法获取候选切片
    chunks = await store.retrieve_chunks(payload.knowledge_base_id, payload.query, top_k=top_k)

    # 按相似度阈值过滤
    if score_threshold > 0:
        chunks = [chunk for chunk in chunks if chunk.score >= score_threshold]

    return RetrievalTestResult(
        query=payload.query,
        chunks=[chunk.model_dump() for chunk in chunks],
        total=len(chunks),
    )
