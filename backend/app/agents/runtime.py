from collections.abc import AsyncIterator

from app.llm.gateway import llm_gateway
from app.repositories.memory import store
from app.schemas.agents import AgentRead
from app.tools import tool_registry


class AgentRuntime:
    async def run(self, agent: AgentRead, user_input: str) -> dict:
        retrieved = await store.retrieve_for_agent(agent.id, user_input, top_k=3)
        tool_results = await tool_registry.run_for_input(agent.tool_ids, user_input)
        model_config_id = agent.model_config_id

        context = "\n\n".join(chunk.content for chunk in retrieved)
        tool_context = "\n\n".join(
            f"工具：{result.name}\n结果：\n{result.content}" for result in tool_results
        )
        model_name = agent.model or llm_gateway.default_model
        messages = [
            {"role": "system", "content": agent.system_prompt},
            {
                "role": "user",
                "content": (
                    f"用户问题：{user_input}\n\n"
                    f"知识库上下文：\n{context or '无'}\n\n"
                    f"应用工具结果：\n{tool_context or '无'}\n\n"
                    "请给出清晰回答。优先使用应用工具结果回答实时业务数据；"
                    "使用知识库内容时说明来源；如果没有可靠依据，请明确说明无法确认。"
                ),
            },
        ]
        generation_status = "完成"
        try:
            answer = await llm_gateway.chat(
                messages,
                model=agent.model,
                config_id=model_config_id,
                fallback=False,
            )
        except RuntimeError as exc:
            generation_status = "失败"
            answer = (
                "真实大模型调用失败，未使用开发模式兜底。\n\n"
                f"错误信息：{exc}\n\n"
                "请到模型配置页面点击“测试”，确认接口地址、Token 和模型名是否正确。"
            )
        steps = [
            {"name": "接收任务", "status": "完成", "detail": user_input},
            {
                "name": "知识库检索",
                "status": "完成",
                "detail": f"命中 {len(retrieved)} 个文档切片",
            },
            {
                "name": "应用工具调用",
                "status": "完成",
                "detail": f"调用 {len(tool_results)} 个工具",
            },
            {"name": "大模型生成", "status": generation_status, "detail": f"使用模型：{model_name}"},
        ]
        return await store.create_run(
            agent_id=agent.id,
            user_input=user_input,
            answer=answer,
            citations=retrieved,
            steps=steps,
            model=model_name,
        )

    async def stream(self, agent: AgentRead, user_input: str) -> AsyncIterator[str]:
        result = await self.run(agent, user_input)
        for token in result["answer"].split(" "):
            yield f"data: {token} \n\n"
        yield "event: done\ndata: {}\n\n"


agent_runtime = AgentRuntime()
