from dataclasses import dataclass, field
from uuid import uuid4

from app.schemas.agents import AgentCreate, AgentRead
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseRead, RetrievedChunk


@dataclass
class MemoryStore:
    agents: dict[str, AgentRead] = field(default_factory=dict)
    knowledge_bases: dict[str, KnowledgeBaseRead] = field(default_factory=dict)
    chunks: dict[str, list[RetrievedChunk]] = field(default_factory=dict)

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
