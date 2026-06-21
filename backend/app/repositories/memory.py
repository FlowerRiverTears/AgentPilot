from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models import Agent, AgentRun, Conversation, Document, DocumentChunk, Feedback, KnowledgeBase, RunStep, Tool, ToolCall, User
from app.rag.pipeline import rag_pipeline
from app.rag.document_loader import ExtractedImage, ParsedDocument
from app.rag.relevance import lexical_relevance
from app.rag.text_quality import is_readable_text
from app.repositories.base import maybe_uuid, to_uuid
from app.schemas.agents import AgentCreate, AgentRead, AgentRunDetail, AgentRunSummary, AgentUpdate
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseRead, RetrievedChunk
from app.vector.embeddings import get_embedding_service
from app.llm.gateway import get_llm_gateway


class DatabaseStore:
    async def initialize(self) -> None:
        async with AsyncSessionLocal() as session:
            await self._ensure_rag_standard_columns(session)
            await self._ensure_default_user(session)
            await self._seed_defaults(session)
            await self._backfill_agent_model_configs(session)
            await self._cleanup_unreadable_chunks(session)

    async def list_agents(self, limit: int = 50, offset: int = 0) -> list[AgentRead]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Agent).where(Agent.status != "deleted").order_by(Agent.created_at.desc()).offset(offset).limit(limit)
            )
            return [self._agent_to_read(agent) for agent in result.scalars().all()]

    async def list_published_agents(self) -> list[AgentRead]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Agent).where(Agent.status == "published").order_by(Agent.created_at.desc())
            )
            return [self._agent_to_read(agent) for agent in result.scalars().all()]

    async def create_agent(self, payload: AgentCreate) -> AgentRead:
        async with AsyncSessionLocal() as session:
            model_config_id = await self._resolve_model_config_id(payload.model_config_id)
            agent = Agent(
                name=payload.name,
                description=payload.description,
                system_prompt=payload.system_prompt,
                model=payload.model,
                status="draft",
                config={
                    "model_config_id": model_config_id,
                    "knowledge_base_ids": payload.knowledge_base_ids,
                    "tool_ids": payload.tool_ids,
                },
            )
            session.add(agent)
            await session.commit()
            await session.refresh(agent)
            return self._agent_to_read(agent)

    async def update_agent(self, agent_id: str, payload: AgentUpdate) -> AgentRead | None:
        agent_uuid = maybe_uuid(agent_id)
        if not agent_uuid:
            return None
        async with AsyncSessionLocal() as session:
            agent = await session.get(Agent, agent_uuid)
            if not agent or agent.status == "deleted":
                return None

            if payload.name is not None:
                agent.name = payload.name
            if payload.description is not None:
                agent.description = payload.description
            if payload.system_prompt is not None:
                agent.system_prompt = payload.system_prompt
            if payload.model is not None:
                agent.model = payload.model

            config = dict(agent.config or {})
            if payload.model_config_id is not None:
                config["model_config_id"] = await self._resolve_model_config_id(payload.model_config_id)
            if payload.knowledge_base_ids is not None:
                config["knowledge_base_ids"] = payload.knowledge_base_ids
            if payload.tool_ids is not None:
                config["tool_ids"] = payload.tool_ids
            agent.config = config
            await session.commit()
            await session.refresh(agent)
            return self._agent_to_read(agent)

    async def set_agent_status(self, agent_id: str, status: str) -> AgentRead | None:
        agent_uuid = maybe_uuid(agent_id)
        if not agent_uuid:
            return None
        async with AsyncSessionLocal() as session:
            agent = await session.get(Agent, agent_uuid)
            if not agent or agent.status == "deleted":
                return None
            agent.status = status
            await session.commit()
            await session.refresh(agent)
            return self._agent_to_read(agent)

    async def delete_agent(self, agent_id: str) -> bool:
        agent_uuid = maybe_uuid(agent_id)
        if not agent_uuid:
            return False
        async with AsyncSessionLocal() as session:
            agent = await session.get(Agent, agent_uuid)
            if not agent or agent.status == "deleted":
                return False
            agent.status = "deleted"
            await session.commit()
            return True

    async def duplicate_agent(self, agent_id: str) -> AgentRead | None:
        agent_uuid = maybe_uuid(agent_id)
        if not agent_uuid:
            return None
        async with AsyncSessionLocal() as session:
            agent = await session.get(Agent, agent_uuid)
            if not agent or agent.status == "deleted":
                return None
            copy = Agent(
                name=f"{agent.name} 副本",
                description=agent.description,
                system_prompt=agent.system_prompt,
                model=agent.model,
                status="draft",
                config=dict(agent.config or {}),
            )
            session.add(copy)
            await session.commit()
            await session.refresh(copy)
            return self._agent_to_read(copy)

    async def get_agent(self, agent_id: str) -> AgentRead | None:
        agent_uuid = maybe_uuid(agent_id)
        if not agent_uuid:
            return None
        async with AsyncSessionLocal() as session:
            agent = await session.get(Agent, agent_uuid)
            if not agent or agent.status == "deleted":
                return None
            return self._agent_to_read(agent)

    async def list_knowledge_bases(self, limit: int = 50, offset: int = 0) -> list[KnowledgeBaseRead]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(KnowledgeBase, func.count(Document.id))
                .outerjoin(Document, Document.knowledge_base_id == KnowledgeBase.id)
                .group_by(KnowledgeBase.id)
                .order_by(KnowledgeBase.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = await session.execute(stmt)
            return [self._kb_to_read(kb, count) for kb, count in rows.all()]

    async def create_knowledge_base(self, payload: KnowledgeBaseCreate) -> KnowledgeBaseRead:
        async with AsyncSessionLocal() as session:
            kb = KnowledgeBase(name=payload.name, description=payload.description)
            session.add(kb)
            await session.commit()
            await session.refresh(kb)
            return self._kb_to_read(kb, 0)

    async def delete_knowledge_base(self, kb_id: str) -> bool:
        kb_uuid = maybe_uuid(kb_id)
        if not kb_uuid:
            return False
        async with AsyncSessionLocal() as session:
            kb = await session.get(KnowledgeBase, kb_uuid)
            if not kb:
                return False

            document_ids = (
                await session.execute(select(Document.id).where(Document.knowledge_base_id == kb_uuid))
            ).scalars().all()

            if document_ids:
                await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id.in_(document_ids)))
                await session.execute(delete(Document).where(Document.id.in_(document_ids)))

            await session.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_uuid))

            agents = (await session.execute(select(Agent))).scalars().all()
            for agent in agents:
                config = dict(agent.config or {})
                knowledge_base_ids = [
                    item for item in config.get("knowledge_base_ids", []) if item != kb_id
                ]
                if knowledge_base_ids != config.get("knowledge_base_ids", []):
                    config["knowledge_base_ids"] = knowledge_base_ids
                    agent.config = config

            await session.commit()
            return True

    async def list_documents(self, kb_id: str) -> list[dict]:
        """列出知识库下的所有文档。"""
        kb_uuid = maybe_uuid(kb_id)
        if not kb_uuid:
            return []
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(Document).where(Document.knowledge_base_id == kb_uuid).order_by(Document.created_at.desc())
                )
            ).scalars().all()
            return [
                {
                    "id": str(doc.id),
                    "knowledge_base_id": str(doc.knowledge_base_id),
                    "filename": doc.filename,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat() if doc.created_at else "",
                }
                for doc in rows
            ]

    async def delete_document(self, kb_id: str, doc_id: str) -> bool:
        """删除单个文档及其所有切片。"""
        doc_uuid = maybe_uuid(doc_id)
        if not doc_uuid:
            return False
        async with AsyncSessionLocal() as session:
            doc = await session.get(Document, doc_uuid)
            if not doc or str(doc.knowledge_base_id) != kb_id:
                return False
            await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc_uuid))
            await session.execute(delete(Document).where(Document.id == doc_uuid))
            await session.commit()
            return True

    async def add_document(self, kb_id: str, filename: str, text: str) -> list[RetrievedChunk]:
        kb_uuid = maybe_uuid(kb_id)
        if not kb_uuid:
            return []
        chunks = rag_pipeline.build_chunks(filename, text)
        if not chunks:
            raise ValueError("No readable chunks were generated from this document")
        async with AsyncSessionLocal() as session:
            kb = await session.get(KnowledgeBase, kb_uuid)
            if not kb:
                return []

            document = Document(knowledge_base_id=kb_uuid, filename=filename, status="indexed")
            session.add(document)
            await session.flush()

            # Batch embed all chunks in parallel
            import asyncio
            texts = [chunk.content for chunk in chunks]
            embeddings = await asyncio.gather(*[get_embedding_service().embed_text(t) for t in texts])

            stored_chunks: list[RetrievedChunk] = []
            for chunk, embedding in zip(chunks, embeddings):
                row = DocumentChunk(
                    document_id=document.id,
                    content=chunk.content,
                    content_type=chunk.content_type,
                    source=filename,
                    source_uri=chunk.source_uri or filename,
                    section_path=chunk.section_path,
                    page_number=chunk.page_number,
                    token_count=chunk.token_count,
                    chunk_metadata=chunk.metadata,
                    embedding=embedding,
                )
                session.add(row)
                await session.flush()
                stored_chunks.append(self._chunk_to_retrieved(row, score=0.0))

            await session.commit()
            return stored_chunks

    async def add_document_multimodal(
        self, kb_id: str, filename: str, parsed: ParsedDocument
    ) -> list[RetrievedChunk]:
        kb_uuid = maybe_uuid(kb_id)
        if not kb_uuid:
            return []

        text_chunks = rag_pipeline.build_chunks(filename, parsed.text)
        image_chunks = rag_pipeline.build_image_chunks(filename, parsed.images)
        all_chunks = text_chunks + image_chunks

        if not all_chunks:
            raise ValueError("No readable chunks were generated from this document")

        async with AsyncSessionLocal() as session:
            kb = await session.get(KnowledgeBase, kb_uuid)
            if not kb:
                return []

            document = Document(knowledge_base_id=kb_uuid, filename=filename, status="indexed")
            session.add(document)
            await session.flush()

            image_map: dict[str, str] = {}
            if parsed.images:
                image_map = await self._upload_images_to_minio(
                    filename, document.id, parsed.images
                )

            stored_chunks: list[RetrievedChunk] = []
            image_by_chunk_id = {
                rag_pipeline.build_image_chunk_id(img): img for img in parsed.images
            }

            # Batch embed all chunks in parallel
            import asyncio
            async def _embed_chunk(chunk):
                if chunk.content_type == "image":
                    img_data = image_by_chunk_id.get(chunk.chunk_id)
                    if img_data and get_embedding_service().multimodal_available:
                        return await get_embedding_service().embed_image(img_data.image_bytes)
                    else:
                        return await get_embedding_service().embed_text(chunk.content)
                else:
                    return await get_embedding_service().embed_text(chunk.content)

            embeddings = await asyncio.gather(*[_embed_chunk(c) for c in all_chunks])

            for chunk, embedding in zip(all_chunks, embeddings):
                image_url = image_map.get(chunk.chunk_id, "")

                row = DocumentChunk(
                    document_id=document.id,
                    content=chunk.content,
                    content_type=chunk.content_type,
                    source=filename,
                    source_uri=chunk.source_uri or filename,
                    section_path=chunk.section_path,
                    page_number=chunk.page_number,
                    token_count=chunk.token_count,
                    chunk_metadata=chunk.metadata,
                    image_url=image_url,
                    embedding=embedding,
                )
                session.add(row)
                await session.flush()
                stored_chunks.append(self._chunk_to_retrieved(row, score=0.0))

            await session.commit()
            return stored_chunks

    async def _upload_images_to_minio(
        self, filename: str, document_id, images: list[ExtractedImage]
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        try:
            from minio import Minio
            from app.core.config import settings as app_settings

            client = Minio(
                app_settings.minio_endpoint,
                access_key=app_settings.minio_access_key,
                secret_key=app_settings.minio_secret_key,
                secure=app_settings.minio_secure,
            )
            bucket = app_settings.minio_bucket
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)

            base_name = Path(filename).stem
            for img in images:
                chunk_key = rag_pipeline.build_image_chunk_id(img)
                ext = ".png"
                if img.content_type == "image/jpeg":
                    ext = ".jpg"
                object_name = (
                    f"documents/{document_id}/{base_name}_"
                    f"p{img.page_number}_img{img.image_index}{ext}"
                )
                client.put_object(
                    bucket,
                    object_name,
                    BytesIO(img.image_bytes),
                    len(img.image_bytes),
                    content_type=img.content_type,
                )
                result[chunk_key] = f"/{bucket}/{object_name}"
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("MinIO upload failed: %s", exc)
        return result

    async def retrieve_chunks(self, kb_id: str, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        kb_uuid = maybe_uuid(kb_id)
        if not kb_uuid:
            return []
        query_embedding = await get_embedding_service().embed_text(query)
        async with AsyncSessionLocal() as session:
            stmt = (
                select(
                    DocumentChunk,
                    DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
                )
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(Document.knowledge_base_id == kb_uuid)
                .order_by(text("distance ASC"))
            )
            rows = await session.execute(stmt)
            chunks: list[RetrievedChunk] = []
            seen_contents: set[str] = set()
            for row, distance in rows.all():
                vector_score = round(1.0 - distance, 6)
                lexical_score = lexical_relevance(query, row.content)
                score = max(vector_score, lexical_score)
                if row.content_type == "text":
                    if (
                        vector_score < settings.retrieval_min_score
                        and lexical_score < settings.retrieval_min_lexical_score
                    ) or not is_readable_text(row.content):
                        continue
                else:
                    if vector_score < settings.retrieval_min_score:
                        continue
                normalized_content = " ".join(row.content.split())
                if normalized_content in seen_contents:
                    continue
                seen_contents.add(normalized_content)
                chunks.append(
                    self._chunk_to_retrieved(
                        row,
                        score=score,
                        vector_score=vector_score,
                        lexical_score=lexical_score,
                    )
                )
            chunks.sort(key=lambda item: item.score, reverse=True)
            return chunks[:top_k]

    async def retrieve_by_image(self, kb_id: str, image_bytes: bytes, top_k: int = 5) -> list[RetrievedChunk]:
        """跨模态检索：用图片查询知识库中的文本块和图片块。"""
        kb_uuid = maybe_uuid(kb_id)
        if not kb_uuid:
            return []
        query_embedding = await get_embedding_service().embed_image(image_bytes)
        async with AsyncSessionLocal() as session:
            stmt = (
                select(
                    DocumentChunk,
                    DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
                )
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(Document.knowledge_base_id == kb_uuid)
                .order_by(text("distance ASC"))
            )
            rows = await session.execute(stmt)
            chunks: list[RetrievedChunk] = []
            seen_contents: set[str] = set()
            for row, distance in rows.all():
                vector_score = round(1.0 - distance, 6)
                if vector_score < settings.retrieval_min_score:
                    continue
                if row.content_type == "text" and not is_readable_text(row.content):
                    continue
                normalized_content = " ".join(row.content.split())
                if normalized_content in seen_contents:
                    continue
                seen_contents.add(normalized_content)
                chunks.append(
                    self._chunk_to_retrieved(
                        row,
                        score=vector_score,
                        vector_score=vector_score,
                    )
                )
            chunks.sort(key=lambda item: item.score, reverse=True)
            return chunks[:top_k]

    async def retrieve_chunks_multi_kb(self, kb_ids: list[str], query: str, top_k: int = 5) -> list[RetrievedChunk]:
        """Retrieve chunks across multiple knowledge bases in a single query."""
        if not kb_ids:
            return []
        kb_uuids = [uid for uid in (maybe_uuid(kb_id) for kb_id in kb_ids) if uid]
        if not kb_uuids:
            return []
        query_embedding = await get_embedding_service().embed_text(query)
        async with AsyncSessionLocal() as session:
            # Get document IDs for all knowledge bases
            doc_result = await session.execute(
                select(Document.id).where(Document.knowledge_base_id.in_(kb_uuids))
            )
            doc_ids = [row[0] for row in doc_result.all()]
            if not doc_ids:
                return []
            # Single vector search across all documents
            stmt = (
                select(
                    DocumentChunk,
                    DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
                )
                .where(DocumentChunk.document_id.in_(doc_ids))
                .order_by(text("distance ASC"))
            )
            rows = await session.execute(stmt)
            chunks: list[RetrievedChunk] = []
            seen_contents: set[str] = set()
            for row, distance in rows.all():
                vector_score = round(1.0 - distance, 6)
                lexical_score = lexical_relevance(query, row.content)
                score = max(vector_score, lexical_score)
                if row.content_type == "text":
                    if (
                        vector_score < settings.retrieval_min_score
                        and lexical_score < settings.retrieval_min_lexical_score
                    ) or not is_readable_text(row.content):
                        continue
                else:
                    if vector_score < settings.retrieval_min_score:
                        continue
                normalized_content = " ".join(row.content.split())
                if normalized_content in seen_contents:
                    continue
                seen_contents.add(normalized_content)
                chunks.append(
                    self._chunk_to_retrieved(
                        row,
                        score=score,
                        vector_score=vector_score,
                        lexical_score=lexical_score,
                    )
                )
            chunks.sort(key=lambda item: item.score, reverse=True)
            return chunks[:top_k]

    async def retrieve_for_agent(self, agent_id: str, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        agent = await self.get_agent(agent_id)
        if not agent:
            return []

        async with AsyncSessionLocal() as session:
            agent_uuid = maybe_uuid(agent_id)
            if not agent_uuid:
                return []
            agent_row = await session.get(Agent, agent_uuid)
            if not agent_row:
                return []

            kb_ids = agent_row.config.get("knowledge_base_ids", [])
            all_chunks = await self.retrieve_chunks_multi_kb(kb_ids, query, top_k=top_k)

        return all_chunks

    async def create_run(
        self,
        agent_id: str,
        user_input: str,
        answer: str,
        citations: Iterable[RetrievedChunk],
        steps: list[dict[str, str]],
        model: str,
        status: str = "completed",
        duration_ms: int | None = None,
        tool_results: list[dict] | None = None,
        error: str | None = None,
    ) -> dict:
        citation_list = list(citations)
        tool_result_list = tool_results or []
        usage: dict = {
            "model": model,
            "duration_ms": duration_ms,
            "citation_count": len(citation_list),
            "citations": [chunk.model_dump() for chunk in citation_list],
            "tool_results": tool_result_list,
        }
        if error:
            usage["error"] = error
        async with AsyncSessionLocal() as session:
            run = AgentRun(
                agent_id=to_uuid(agent_id),
                status=status,
                input=user_input,
                output=answer,
                trace_id=str(uuid4()),
                usage=usage,
            )
            session.add(run)
            await session.flush()

            for step in steps:
                session.add(
                    RunStep(
                        run_id=run.id,
                        name=step["name"],
                        status=step["status"],
                        detail={"detail": step["detail"]},
                    )
                )

            await session.commit()
            await session.refresh(run)
            return {
                "run_id": str(run.id),
                "agent_id": agent_id,
                "status": run.status,
                "model": model,
                "duration_ms": duration_ms,
                "answer": answer,
                "citations": [chunk.model_dump() for chunk in citation_list],
                "steps": steps,
                "tool_results": tool_result_list,
                "usage": usage,
            }

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[AgentRunSummary]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AgentRun, Agent.name)
                .outerjoin(Agent, Agent.id == AgentRun.agent_id)
                .order_by(AgentRun.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            rows = await session.execute(stmt)
            return [self._run_to_summary(run, agent_name) for run, agent_name in rows.all()]

    async def get_stats(self) -> dict:
        """总览统计数据：各资源数量与鉴权状态。"""
        from app.models import EvalDataset, EvalResult, Workflow, WorkflowRun

        async with AsyncSessionLocal() as session:
            agents_total = await session.scalar(
                select(func.count()).select_from(Agent).where(Agent.status != "deleted")
            )
            agents_published = await session.scalar(
                select(func.count()).select_from(Agent).where(Agent.status == "published")
            )
            runs_total = await session.scalar(select(func.count()).select_from(AgentRun))
            knowledge_bases = await session.scalar(select(func.count()).select_from(KnowledgeBase))
            documents = await session.scalar(select(func.count()).select_from(Document))
            tools = await session.scalar(select(func.count()).select_from(Tool))
            tool_calls = await session.scalar(select(func.count()).select_from(ToolCall))
            conversations = await session.scalar(select(func.count()).select_from(Conversation))
            feedback_likes = await session.scalar(
                select(func.count()).select_from(Feedback).where(Feedback.rating == "like")
            )
            feedback_dislikes = await session.scalar(
                select(func.count()).select_from(Feedback).where(Feedback.rating == "dislike")
            )
            eval_datasets = await session.scalar(select(func.count()).select_from(EvalDataset))
            eval_results = await session.scalar(select(func.count()).select_from(EvalResult))
            workflows = await session.scalar(select(func.count()).select_from(Workflow))
            workflow_runs = await session.scalar(select(func.count()).select_from(WorkflowRun))
            return {
                "agents_total": int(agents_total or 0),
                "agents_published": int(agents_published or 0),
                "runs_total": int(runs_total or 0),
                "knowledge_bases": int(knowledge_bases or 0),
                "documents": int(documents or 0),
                "tools": int(tools or 0),
                "tool_calls": int(tool_calls or 0),
                "conversations": int(conversations or 0),
                "feedback_likes": int(feedback_likes or 0),
                "feedback_dislikes": int(feedback_dislikes or 0),
                "eval_datasets": int(eval_datasets or 0),
                "eval_results": int(eval_results or 0),
                "workflows": int(workflows or 0),
                "workflow_runs": int(workflow_runs or 0),
            }

    async def get_run(self, run_id: str) -> AgentRunDetail | None:
        run_uuid = maybe_uuid(run_id)
        if not run_uuid:
            return None
        async with AsyncSessionLocal() as session:
            stmt = select(AgentRun, Agent.name).outerjoin(Agent, Agent.id == AgentRun.agent_id).where(AgentRun.id == run_uuid)
            row = (await session.execute(stmt)).first()
            if not row:
                return None
            run, agent_name = row
            step_rows = (
                await session.execute(select(RunStep).where(RunStep.run_id == run.id).order_by(RunStep.created_at.asc()))
            ).scalars().all()
            return self._run_to_detail(run, agent_name, step_rows)

    async def _seed_defaults(self, session: AsyncSession) -> None:
        kb_count = await session.scalar(select(func.count()).select_from(KnowledgeBase))
        agent_count = await session.scalar(select(func.count()).select_from(Agent))
        tool_count = await session.scalar(select(func.count()).select_from(Tool))
        if kb_count and agent_count and tool_count:
            return

        await get_llm_gateway().ensure_defaults()
        model_configs = await get_llm_gateway().list_configs()
        default_model_config = next((config for config in model_configs if config.is_default), None)
        default_model_config_id = default_model_config.id if default_model_config else None

        if not kb_count:
            redis_kb = KnowledgeBase(
                name="Redis 示例知识库",
                description="内置示例，帮助快速体验知识库检索。",
            )
            session.add(redis_kb)
            await session.flush()

            for content in (
                "Redis 是一个高性能的内存数据结构数据库，常用于缓存、计数器、排行榜、会话存储、分布式锁和消息队列。",
                "Redis 创建缓存的常见方式是先查缓存，未命中再查数据库，然后回写缓存并设置过期时间。例如使用 SET key value EX seconds。",
                "Redis 分布式锁通常使用 SET lockKey value NX EX seconds，NX 表示只有 key 不存在时才写入，EX 表示设置过期时间，避免锁长时间不释放。",
            ):
                document = Document(
                    knowledge_base_id=redis_kb.id,
                    filename="Redis示例.md",
                    status="indexed",
                )
                session.add(document)
                await session.flush()
                for chunk in rag_pipeline.build_chunks(document.filename, content):
                    embedding = await get_embedding_service().embed_text(chunk.content)
                    session.add(
                        DocumentChunk(
                            document_id=document.id,
                            content=chunk.content,
                            content_type="text",
                            source=document.filename,
                            embedding=embedding,
                        )
                    )

        tool_ids: list[str] = []
        if not tool_count:
            api_base = f"http://agentpilot-backend:8000/api/mock" if "agentpilot" in settings.database_url else f"http://localhost:8000/api/mock"

            seed_tools = [
                Tool(
                    name="订单查询",
                    type="http",
                    description="查询订单状态、物流信息和发货进度，适合处理用户关于订单的咨询。",
                    config={
                        "url": f"{api_base}/order",
                        "method": "GET",
                        "trigger_keywords": ["订单", "物流", "发货", "快递", "配送", "order"],
                        "headers": {},
                        "query": {},
                        "body": {},
                        "timeout_seconds": 10,
                    },
                    enabled=True,
                ),
                Tool(
                    name="库存查询",
                    type="http",
                    description="查询商品库存数量和仓库状态，适合处理用户关于商品是否有货的咨询。",
                    config={
                        "url": f"{api_base}/inventory",
                        "method": "GET",
                        "trigger_keywords": ["库存", "有货", "缺货", "现货", "补货", "stock"],
                        "headers": {},
                        "query": {},
                        "body": {},
                        "timeout_seconds": 10,
                    },
                    enabled=True,
                ),
                Tool(
                    name="天气查询",
                    type="http",
                    description="查询城市天气信息，包括温度、湿度、风力和空气质量，适合处理天气相关咨询。",
                    config={
                        "url": f"{api_base}/weather",
                        "method": "GET",
                        "trigger_keywords": ["天气", "气温", "下雨", "温度", "湿度", "weather"],
                        "headers": {},
                        "query": {},
                        "body": {},
                        "timeout_seconds": 10,
                    },
                    enabled=True,
                ),
            ]
            for tool in seed_tools:
                session.add(tool)
            await session.flush()
            tool_ids = [str(tool.id) for tool in seed_tools]

        if not agent_count:
            default_kb = (
                await session.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.asc()))
            ).scalars().first()
            if default_kb:
                session.add(
                    Agent(
                        name="Redis 助手",
                        description="内置示例智能体",
                        system_prompt="你是一个简洁、准确的 Redis 助手。",
                        model=None,
                        status="draft",
                        config={
                            "model_config_id": default_model_config_id,
                            "knowledge_base_ids": [str(default_kb.id)],
                            "tool_ids": [],
                        },
                    )
                )

            if tool_ids:
                session.add(
                    Agent(
                        name="全能客服助手",
                        description="可以查询订单、库存和天气信息的智能客服",
                        system_prompt="你是一个专业的客服助手。回答问题时：1. 优先使用工具返回的实时数据；2. 使用知识库内容时说明来源；3. 如果没有可靠依据，明确说明无法确认。回答要简洁、准确、友好。",
                        model=None,
                        status="published",
                        config={
                            "model_config_id": default_model_config_id,
                            "knowledge_base_ids": [],
                            "tool_ids": tool_ids,
                        },
                    )
                )

        await session.commit()

    async def _backfill_agent_model_configs(self, session: AsyncSession) -> None:
        default_config = await get_llm_gateway().get_config()
        agents = (await session.execute(select(Agent).where(Agent.status != "deleted"))).scalars().all()
        changed = False
        for agent in agents:
            config = dict(agent.config or {})
            if not config.get("model_config_id"):
                config["model_config_id"] = default_config.id
                agent.config = config
                changed = True
        if changed:
            await session.commit()

    async def _cleanup_unreadable_chunks(self, session: AsyncSession) -> None:
        rows = (
            await session.execute(
                select(DocumentChunk.id, DocumentChunk.content, DocumentChunk.content_type)
            )
        ).all()
        unreadable_ids = [
            chunk_id
            for chunk_id, content, content_type in rows
            if content_type == "text" and not is_readable_text(content)
        ]
        if unreadable_ids:
            await session.execute(delete(DocumentChunk).where(DocumentChunk.id.in_(unreadable_ids)))
            await session.commit()

    async def _ensure_rag_standard_columns(self, session: AsyncSession) -> None:
        statements = [
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS source_uri VARCHAR(500) NOT NULL DEFAULT ''",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS section_path VARCHAR(500) NOT NULL DEFAULT ''",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS page_number INTEGER",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS token_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS chunk_metadata JSON NOT NULL DEFAULT '{}'",
        ]
        for statement in statements:
            await session.execute(text(statement))
        await session.commit()

    async def _ensure_default_user(self, session: AsyncSession) -> None:
        user_count = await session.scalar(select(func.count()).select_from(User))
        if user_count:
            return
        admin = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            role="admin",
            status="active",
        )
        session.add(admin)
        await session.commit()

    async def _resolve_model_config_id(self, model_config_id: str | None) -> str:
        if not model_config_id:
            default_config = await get_llm_gateway().get_config()
            return default_config.id
        if not await get_llm_gateway().get_config_by_id(model_config_id):
            default_config = await get_llm_gateway().get_config()
            return default_config.id
        return model_config_id

    def _agent_to_read(self, agent: Agent) -> AgentRead:
        config = agent.config or {}
        return AgentRead(
            id=str(agent.id),
            name=agent.name,
            description=agent.description,
            system_prompt=agent.system_prompt,
            model=agent.model,
            model_config_id=config.get("model_config_id"),
            knowledge_base_ids=list(config.get("knowledge_base_ids", [])),
            tool_ids=list(config.get("tool_ids", [])),
            sub_agent_ids=list(config.get("sub_agent_ids", [])),
            tool_chain=list(config.get("tool_chain", [])),
            status=agent.status,
        )

    def _kb_to_read(self, kb: KnowledgeBase, document_count: int | None) -> KnowledgeBaseRead:
        return KnowledgeBaseRead(
            id=str(kb.id),
            name=kb.name,
            description=kb.description,
            document_count=int(document_count or 0),
        )

    def _chunk_to_retrieved(
        self,
        row: DocumentChunk,
        score: float,
        vector_score: float = 0.0,
        lexical_score: float = 0.0,
    ) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=str(row.id),
            document_id=str(row.document_id),
            content=row.content,
            score=score,
            source=row.source,
            source_uri=row.source_uri or row.source,
            section_path=row.section_path or "",
            page_number=row.page_number,
            token_count=row.token_count or 0,
            metadata=dict(row.chunk_metadata or {}),
            content_type=row.content_type,
            image_url=row.image_url or "",
            vector_score=vector_score,
            lexical_score=lexical_score,
        )

    def _run_to_summary(self, run: AgentRun, agent_name: str | None) -> AgentRunSummary:
        usage = run.usage or {}
        return AgentRunSummary(
            run_id=str(run.id),
            agent_id=str(run.agent_id),
            agent_name=agent_name or "未知智能体",
            status=run.status,
            input=run.input,
            model=str(usage.get("model", "")),
            duration_ms=usage.get("duration_ms"),
            trace_id=run.trace_id,
            created_at=run.created_at.isoformat(),
        )

    def _run_to_detail(self, run: AgentRun, agent_name: str | None, steps: list[RunStep]) -> AgentRunDetail:
        usage = run.usage or {}
        summary = self._run_to_summary(run, agent_name)
        return AgentRunDetail(
            **summary.model_dump(),
            answer=run.output or "",
            citations=list(usage.get("citations", [])),
            steps=[
                {
                    "name": step.name,
                    "status": step.status,
                    "detail": str((step.detail or {}).get("detail", "")),
                }
                for step in steps
            ],
            usage=usage,
            tool_results=list(usage.get("tool_results", [])),
        )



_store = None


def get_store() -> "DatabaseStore":
    """Lazy-initialized database store singleton."""
    global _store
    if _store is None:
        _store = DatabaseStore()
    return _store
