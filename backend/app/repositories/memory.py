from dataclasses import dataclass, field
from uuid import uuid4

from app.schemas.agents import AgentCreate, AgentRead
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseRead, RetrievedChunk


@dataclass
class MemoryStore:
    agents: dict[str, AgentRead] = field(default_factory=dict)
    knowledge_bases: dict[str, KnowledgeBaseRead] = field(default_factory=dict)
    chunks: dict[str, list[RetrievedChunk]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.seed_defaults()

    def seed_defaults(self) -> None:
        if self.knowledge_bases:
            return

        redis_kb = self._create_seed_knowledge_base(
            name="Redis 示例知识库",
            description="内置示例，可直接选择并检索 Redis 基础、缓存和分布式锁内容。",
            chunks=[
                (
                    "Redis 是一个高性能的内存数据结构数据库，常用作缓存、计数器、排行榜、"
                    "会话存储、分布式锁和消息队列。常见数据结构包括 String、Hash、List、Set、"
                    "Sorted Set、Stream。"
                ),
                (
                    "Redis 创建缓存的常见方式是先查询缓存，如果缓存不存在再查询数据库，"
                    "然后写入缓存并设置过期时间。例如可以使用 SET key value EX seconds "
                    "写入带过期时间的数据。"
                ),
                (
                    "Redis 分布式锁通常使用 SET lockKey value NX EX seconds。NX 表示只有 key "
                    "不存在时才写入，EX 表示设置过期时间，避免业务异常导致锁一直不释放。"
                ),
            ],
        )
        self._create_seed_knowledge_base(
            name="AgentPilot 项目知识库",
            description="内置示例，可直接了解本项目的 LLM、RAG、切面和向量能力。",
            chunks=[
                (
                    "AgentPilot 是一个 AI 智能体工作台，支持创建智能体、绑定知识库、"
                    "执行任务、查看回答、引用来源和执行过程。"
                ),
                (
                    "项目核心能力包括 LLM 模型网关、RAG 知识库检索、切面追踪和向量相似度检索。"
                    "第一版使用 FastAPI、Vue、PostgreSQL、Redis、MinIO 和 Docker Compose。"
                ),
            ],
        )

        self.create_agent(
            AgentCreate(
                name="Redis 助手",
                description="内置示例智能体，可直接询问 Redis 相关问题。",
                system_prompt="你是 Redis 助手。回答要清晰、简洁，并优先基于知识库内容。",
                model=None,
                knowledge_base_ids=[redis_kb.id],
                tool_ids=[],
            )
        )

    def _create_seed_knowledge_base(
        self,
        name: str,
        description: str,
        chunks: list[str],
    ) -> KnowledgeBaseRead:
        kb = self.create_knowledge_base(KnowledgeBaseCreate(name=name, description=description))
        self.chunks[kb.id] = [
            RetrievedChunk(
                chunk_id=str(uuid4()),
                content=content,
                score=0.0,
                source=f"{name}.md",
            )
            for content in chunks
        ]
        self.knowledge_bases[kb.id] = kb.model_copy(update={"document_count": 1})
        return self.knowledge_bases[kb.id]

    def create_agent(self, payload: AgentCreate) -> AgentRead:
        agent = AgentRead(id=str(uuid4()), **payload.model_dump())
        self.agents[agent.id] = agent
        return agent

    def list_agents(self) -> list[AgentRead]:
        return list(self.agents.values())

    def get_agent(self, agent_id: str) -> AgentRead | None:
        return self.agents.get(agent_id)

    def create_knowledge_base(self, payload: KnowledgeBaseCreate) -> KnowledgeBaseRead:
        kb = KnowledgeBaseRead(id=str(uuid4()), **payload.model_dump())
        self.knowledge_bases[kb.id] = kb
        self.chunks[kb.id] = []
        return kb

    def list_knowledge_bases(self) -> list[KnowledgeBaseRead]:
        return list(self.knowledge_bases.values())

    def delete_knowledge_base(self, kb_id: str) -> bool:
        if kb_id not in self.knowledge_bases:
            return False

        del self.knowledge_bases[kb_id]
        self.chunks.pop(kb_id, None)

        for agent_id, agent in list(self.agents.items()):
            if kb_id in agent.knowledge_base_ids:
                self.agents[agent_id] = agent.model_copy(
                    update={
                        "knowledge_base_ids": [
                            item for item in agent.knowledge_base_ids if item != kb_id
                        ]
                    }
                )
        return True


store = MemoryStore()
