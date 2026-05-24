from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import Agent, AgentRun, Document, DocumentChunk, KnowledgeBase, RunStep, Tool
from app.rag.pipeline import rag_pipeline
from app.schemas.agents import AgentCreate, AgentRead, AgentRunDetail, AgentRunSummary, AgentUpdate
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseRead, RetrievedChunk
from app.vector.embeddings import embedding_service
from app.llm.gateway import llm_gateway


class DatabaseStore:
    async def initialize(self) -> None:
        async with AsyncSessionLocal() as session:
            await self._seed_defaults(session)
            await self._backfill_agent_model_configs(session)

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
                embedding = await embedding_service.embed_text(chunk.content)
                row = DocumentChunk(
                    document_id=document.id,
                    content=chunk.content,
                    source=filename,
                    embedding=embedding,
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
        query_embedding = await embedding_service.embed_text(query)
        async with AsyncSessionLocal() as session:
            stmt = (
                select(
                    DocumentChunk.id,
                    DocumentChunk.content,
                    DocumentChunk.source,
                    DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
                )
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(Document.knowledge_base_id == kb_uuid)
                .order_by(text("distance ASC"))
                .limit(top_k)
            )
            rows = await session.execute(stmt)
            return [
                RetrievedChunk(
                    chunk_id=str(chunk_id),
                    content=content,
                    score=round(1.0 - distance, 6),
                    source=source,
                )
                for chunk_id, content, source, distance in rows.all()
            ]

    async def retrieve_for_agent(self, agent_id: str, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        agent = await self.get_agent(agent_id)
        if not agent:
            return []

        all_chunks: list[RetrievedChunk] = []
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
                all_chunks.extend(kb_chunks)

        all_chunks.sort(key=lambda item: item.score, reverse=True)
        return all_chunks[:top_k]

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
    ) -> dict:
        citation_list = list(citations)
        tool_result_list = tool_results or []
        async with AsyncSessionLocal() as session:
            run = AgentRun(
                agent_id=self._uuid(agent_id),
                status=status,
                input=user_input,
                output=answer,
                trace_id=str(uuid4()),
                usage={
                    "model": model,
                    "duration_ms": duration_ms,
                    "citation_count": len(citation_list),
                    "citations": [chunk.model_dump() for chunk in citation_list],
                    "tool_results": tool_result_list,
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
                "duration_ms": duration_ms,
                "answer": answer,
                "citations": [chunk.model_dump() for chunk in citation_list],
                "steps": steps,
                "tool_results": tool_result_list,
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
        tool_count = await session.scalar(select(func.count()).select_from(Tool))
        if kb_count and agent_count and tool_count:
            return

        await llm_gateway.ensure_defaults()
        model_configs = await llm_gateway.list_configs()
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
                    embedding = await embedding_service.embed_text(chunk.content)
                    session.add(
                        DocumentChunk(
                            document_id=document.id,
                            content=chunk.content,
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
        default_config = await llm_gateway.get_config()
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
        )

    def _uuid(self, value: str) -> UUID:
        return UUID(value)

    def _maybe_uuid(self, value: str) -> UUID | None:
        try:
            return UUID(value)
        except ValueError:
            return None


store = DatabaseStore()
