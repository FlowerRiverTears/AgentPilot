from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models import Agent, AgentRun, Document, DocumentChunk, KnowledgeBase, RunStep
from app.rag.pipeline import rag_pipeline
from app.schemas.agents import AgentCreate, AgentRead, AgentRunDetail, AgentRunSummary, AgentUpdate
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseRead, RetrievedChunk
from app.vector.embeddings import embedding_service
from app.llm.gateway import llm_gateway


class DatabaseStore:
    async def initialize(self) -> None:
        async with AsyncSessionLocal() as session:
            await self._seed_defaults(session)

    async def list_agents(self) -> list[AgentRead]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Agent).where(Agent.status != "deleted").order_by(Agent.created_at.desc())
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
        agent_uuid = self._maybe_uuid(agent_id)
        if not agent_uuid:
            return None
        async with AsyncSessionLocal() as session:
            agent = await session.get(Agent, agent_uuid)
            if not agent or agent.status == "deleted":
                return None

            model_config_id = await self._resolve_model_config_id(payload.model_config_id)
            agent.name = payload.name
            agent.description = payload.description
            agent.system_prompt = payload.system_prompt
            agent.model = payload.model
            agent.config = {
                "model_config_id": model_config_id,
                "knowledge_base_ids": payload.knowledge_base_ids,
                "tool_ids": payload.tool_ids,
            }
            await session.commit()
            await session.refresh(agent)
            return self._agent_to_read(agent)

    async def set_agent_status(self, agent_id: str, status: str) -> AgentRead | None:
        agent_uuid = self._maybe_uuid(agent_id)
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
        agent_uuid = self._maybe_uuid(agent_id)
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
        agent_uuid = self._maybe_uuid(agent_id)
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
        agent_uuid = self._maybe_uuid(agent_id)
        if not agent_uuid:
            return None
        async with AsyncSessionLocal() as session:
            agent = await session.get(Agent, agent_uuid)
            if not agent or agent.status == "deleted":
                return None
            return self._agent_to_read(agent)

    async def list_knowledge_bases(self) -> list[KnowledgeBaseRead]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(KnowledgeBase, func.count(Document.id))
                .outerjoin(Document, Document.knowledge_base_id == KnowledgeBase.id)
                .group_by(KnowledgeBase.id)
                .order_by(KnowledgeBase.created_at.desc())
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
        kb_uuid = self._maybe_uuid(kb_id)
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

    async def add_document(self, kb_id: str, filename: str, text: str) -> list[RetrievedChunk]:
        kb_uuid = self._maybe_uuid(kb_id)
        if not kb_uuid:
            return []
        chunks = rag_pipeline.build_chunks(filename, text)
        async with AsyncSessionLocal() as session:
            kb = await session.get(KnowledgeBase, kb_uuid)
            if not kb:
                return []

            document = Document(knowledge_base_id=kb_uuid, filename=filename, status="indexed")
            session.add(document)
            await session.flush()

            stored_chunks: list[RetrievedChunk] = []
            for chunk in chunks:
                row = DocumentChunk(
                    document_id=document.id,
                    content=chunk.content,
                    source=filename,
                    embedding=embedding_service.embed_text(chunk.content),
                )
                session.add(row)
                await session.flush()
                stored_chunks.append(
                    RetrievedChunk(
                        chunk_id=str(row.id),
                        content=row.content,
                        score=0.0,
                        source=row.source,
                    )
                )

            await session.commit()
            return stored_chunks

    async def retrieve_chunks(self, kb_id: str, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        kb_uuid = self._maybe_uuid(kb_id)
        if not kb_uuid:
            return []
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(DocumentChunk.id, DocumentChunk.content, DocumentChunk.source, DocumentChunk.embedding).join(
                    Document, Document.id == DocumentChunk.document_id
                ).where(Document.knowledge_base_id == kb_uuid)
            )
            chunks = [
                RetrievedChunk(
                    chunk_id=str(chunk_id),
                    content=content,
                    score=0.0,
                    source=source,
                )
                for chunk_id, content, source, _embedding in result.all()
            ]
            return rag_pipeline.retrieve(query, chunks, top_k=top_k)

    async def retrieve_for_agent(self, agent_id: str, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        agent = await self.get_agent(agent_id)
        if not agent:
            return []

        chunks: list[RetrievedChunk] = []
        async with AsyncSessionLocal() as session:
            agent_uuid = self._maybe_uuid(agent_id)
            if not agent_uuid:
                return []
            agent_row = await session.get(Agent, agent_uuid)
            if not agent_row:
                return []

            kb_ids = agent_row.config.get("knowledge_base_ids", [])
            for kb_id in kb_ids:
                kb_chunks = await self.retrieve_chunks(kb_id, query, top_k=top_k)
                chunks.extend(kb_chunks)

        ranked = rag_pipeline.retrieve(query, chunks, top_k=top_k)
        return ranked

    async def create_run(
        self,
        agent_id: str,
        user_input: str,
        answer: str,
        citations: Iterable[RetrievedChunk],
        steps: list[dict[str, str]],
        model: str,
        status: str = "completed",
    ) -> dict:
        citation_list = list(citations)
        async with AsyncSessionLocal() as session:
            run = AgentRun(
                agent_id=self._uuid(agent_id),
                status=status,
                input=user_input,
                output=answer,
                trace_id=str(uuid4()),
                usage={
                    "model": model,
                    "citation_count": len(citation_list),
                    "citations": [chunk.model_dump() for chunk in citation_list],
                },
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
                "answer": answer,
                "citations": [chunk.model_dump() for chunk in citation_list],
                "steps": steps,
            }

    async def list_runs(self, limit: int = 50) -> list[AgentRunSummary]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AgentRun, Agent.name)
                .outerjoin(Agent, Agent.id == AgentRun.agent_id)
                .order_by(AgentRun.created_at.desc())
                .limit(limit)
            )
            rows = await session.execute(stmt)
            return [self._run_to_summary(run, agent_name) for run, agent_name in rows.all()]

    async def get_run(self, run_id: str) -> AgentRunDetail | None:
        run_uuid = self._maybe_uuid(run_id)
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
        if kb_count and agent_count:
            return

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
                    session.add(
                        DocumentChunk(
                            document_id=document.id,
                            content=chunk.content,
                            source=document.filename,
                            embedding=embedding_service.embed_text(chunk.content),
                        )
                    )

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
                            "knowledge_base_ids": [str(default_kb.id)],
                            "tool_ids": [],
                        },
                    )
                )

        await session.commit()

    async def _resolve_model_config_id(self, model_config_id: str | None) -> str:
        if not model_config_id:
            default_config = await llm_gateway.get_config()
            return default_config.id
        if not await llm_gateway.get_config_by_id(model_config_id):
            default_config = await llm_gateway.get_config()
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
            status=agent.status,
        )

    def _kb_to_read(self, kb: KnowledgeBase, document_count: int | None) -> KnowledgeBaseRead:
        return KnowledgeBaseRead(
            id=str(kb.id),
            name=kb.name,
            description=kb.description,
            document_count=int(document_count or 0),
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
        )

    def _uuid(self, value: str) -> UUID:
        return UUID(value)

    def _maybe_uuid(self, value: str) -> UUID | None:
        try:
            return UUID(value)
        except ValueError:
            return None


store = DatabaseStore()
