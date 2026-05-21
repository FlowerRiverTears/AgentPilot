from collections.abc import AsyncIterator
from uuid import uuid4

from app.llm.gateway import llm_gateway
from app.rag.pipeline import rag_pipeline
from app.repositories.memory import store
from app.schemas.agents import AgentRead


class AgentRuntime:
    async def run(self, agent: AgentRead, user_input: str) -> dict:
        retrieved = []
        for kb_id in agent.knowledge_base_ids:
            retrieved.extend(rag_pipeline.retrieve(user_input, store.chunks.get(kb_id, []), top_k=3))

        context = "\n\n".join(chunk.content for chunk in retrieved)
        messages = [
            {"role": "system", "content": agent.system_prompt},
            {
                "role": "user",
                "content": (
                    f"用户问题：{user_input}\n\n"
                    f"知识库上下文：\n{context or '无'}\n\n"
                    "请给出清晰回答，如果使用了知识库内容，需要说明来源。"
                ),
            },
        ]
        answer = await llm_gateway.chat(messages, model=agent.model)
        return {
            "run_id": str(uuid4()),
            "agent_id": agent.id,
            "answer": answer,
            "citations": [chunk.model_dump() for chunk in retrieved],
            "steps": [
                {"name": "input", "status": "completed", "detail": user_input},
                {"name": "rag.retrieve", "status": "completed", "detail": f"{len(retrieved)} chunks"},
                {"name": "llm.chat", "status": "completed", "detail": agent.model or "default"},
            ],
        }

    async def stream(self, agent: AgentRead, user_input: str) -> AsyncIterator[str]:
        result = await self.run(agent, user_input)
        for token in result["answer"].split(" "):
            yield f"data: {token} \n\n"
        yield "event: done\ndata: {}\n\n"


agent_runtime = AgentRuntime()
