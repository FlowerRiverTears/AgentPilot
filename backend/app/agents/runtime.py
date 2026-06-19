import json
from collections.abc import AsyncIterator
from time import perf_counter

from app.llm.gateway import llm_gateway
from app.repositories.memory import store
from app.repositories.tools import tool_store
from app.schemas.agents import AgentRead
from app.schemas.knowledge import RetrievedChunk
from app.tools import tool_registry


class AgentRuntime:
    def _format_context(self, retrieved: list[RetrievedChunk]) -> str:
        parts = []
        for chunk in retrieved:
            location = []
            if chunk.page_number:
                location.append(f"第 {chunk.page_number} 页")
            if chunk.section_path:
                location.append(chunk.section_path)
            location_text = "，".join(location) or "未标注位置"
            score_text = (
                f"score={chunk.score:.3f}, vector={chunk.vector_score:.3f}, "
                f"lexical={chunk.lexical_score:.3f}"
            )
            header = (
                f"[chunk_id={chunk.chunk_id}; source={chunk.source}; "
                f"location={location_text}; {score_text}]"
            )
            if chunk.content_type == "image" and chunk.image_url:
                parts.append(f"{header}\n{chunk.content}\n图片地址：{chunk.image_url}")
            else:
                parts.append(f"{header}\n{chunk.content}")
        return "\n\n".join(parts)

    def _build_messages(
        self,
        agent: AgentRead,
        user_input: str,
        context: str,
        tool_context: str,
        messages: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        system_prompt = (
            f"{agent.system_prompt}\n\n"
            "RAG 回答要求：优先依据工具结果和知识库上下文回答；"
            "使用知识库内容时必须标注来源或 chunk_id；"
            "上下文不足时明确说明无法从当前资料确认，不要编造。"
        )
        chat_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if messages:
            chat_messages.extend(
                {"role": message["role"], "content": message["content"]}
                for message in messages
                if message.get("role") in {"user", "assistant"} and message.get("content")
            )
        chat_messages.append(
            {
                "role": "user",
                "content": (
                    f"用户问题：{user_input}\n\n"
                    f"知识库上下文：\n{context or '无'}\n\n"
                    f"应用工具结果：\n{tool_context or '无'}\n\n"
                    "请给出清晰、简洁、可追溯的回答。"
                ),
            }
        )
        return chat_messages

    async def _resolve_model_name(self, agent: AgentRead) -> str:
        if agent.model:
            return agent.model

        config_id = agent.model_config_id
        if config_id:
            config = await llm_gateway.get_config_by_id(config_id)
            if config:
                return config.default_model

        runtime_config = await llm_gateway.get_config()
        return runtime_config.default_model

    async def run(
        self,
        agent: AgentRead,
        user_input: str,
        messages: list[dict[str, str]] | None = None,
    ) -> dict:
        started_at = perf_counter()
        retrieved = await store.retrieve_for_agent(agent.id, user_input, top_k=3)
        database_tool_results = await tool_store.run_for_input(agent.tool_ids, user_input)
        fallback_tool_results = await tool_registry.run_for_input(agent.tool_ids, user_input)
        model_config_id = agent.model_config_id

        context = self._format_context(retrieved)
        tool_context = "\n\n".join(
            f"工具：{result['name']}\n结果：\n{result['content']}"
            for result in database_tool_results
        )
        if not tool_context and fallback_tool_results:
            tool_context = "\n\n".join(
                f"工具：{result.name}\n结果：\n{result.content}"
                for result in fallback_tool_results
            )
        model_name = await self._resolve_model_name(agent)
        chat_messages = self._build_messages(agent, user_input, context, tool_context, messages)
        generation_status = "完成"
        error_message = ""
        try:
            answer = await llm_gateway.chat(
                chat_messages,
                model=agent.model,
                config_id=model_config_id,
                fallback=False,
            )
        except RuntimeError as exc:
            generation_status = "失败"
            error_message = str(exc)
            answer = (
                "真实大模型调用失败，未使用开发模式兜底。\n\n"
                f"错误信息：{exc}\n\n"
                "请到模型配置页面确认接口地址、Token 和模型名是否正确。"
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
                "detail": f"调用 {len(database_tool_results) + len(fallback_tool_results)} 个工具",
            },
            {"name": "大模型生成", "status": generation_status, "detail": f"使用模型：{model_name}"},
        ]
        run_status = "failed" if generation_status == "失败" else "completed"
        return await store.create_run(
            agent_id=agent.id,
            user_input=user_input,
            answer=answer,
            citations=retrieved,
            steps=steps,
            model=model_name,
            status=run_status,
            duration_ms=int((perf_counter() - started_at) * 1000),
            tool_results=database_tool_results
            + [
                {
                    "tool_id": result.tool_id,
                    "name": result.name,
                    "content": result.content,
                }
                for result in fallback_tool_results
            ],
            error=error_message or None,
        )

    async def stream(
        self,
        agent: AgentRead,
        user_input: str,
        messages: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        started_at = perf_counter()
        retrieved = await store.retrieve_for_agent(agent.id, user_input, top_k=3)
        database_tool_results = await tool_store.run_for_input(agent.tool_ids, user_input)
        fallback_tool_results = await tool_registry.run_for_input(agent.tool_ids, user_input)
        model_config_id = agent.model_config_id

        context = self._format_context(retrieved)
        tool_context = "\n\n".join(
            f"工具：{result['name']}\n结果：\n{result['content']}"
            for result in database_tool_results
        )
        if not tool_context and fallback_tool_results:
            tool_context = "\n\n".join(
                f"工具：{result.name}\n结果：\n{result.content}"
                for result in fallback_tool_results
            )
        model_name = await self._resolve_model_name(agent)

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
                "detail": f"调用 {len(database_tool_results) + len(fallback_tool_results)} 个工具",
            },
        ]

        yield f"event: steps\ndata: {json.dumps(steps, ensure_ascii=False)}\n\n"

        citations_data = [chunk.model_dump() for chunk in retrieved]
        yield f"event: citations\ndata: {json.dumps(citations_data, ensure_ascii=False)}\n\n"

        chat_messages = self._build_messages(agent, user_input, context, tool_context, messages)

        full_answer = ""
        generation_status = "完成"
        try:
            async for token in llm_gateway.stream_chat(
                chat_messages,
                model=agent.model,
                config_id=model_config_id,
            ):
                full_answer += token
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except Exception:
            generation_status = "失败"
            full_answer = "流式生成失败，请检查模型配置。"
            yield f"data: {json.dumps({'token': full_answer}, ensure_ascii=False)}\n\n"

        steps.append(
            {"name": "大模型生成", "status": generation_status, "detail": f"使用模型：{model_name}"}
        )

        run_data = await store.create_run(
            agent_id=agent.id,
            user_input=user_input,
            answer=full_answer,
            citations=retrieved,
            steps=steps,
            model=model_name,
            duration_ms=int((perf_counter() - started_at) * 1000),
            tool_results=database_tool_results
            + [
                {"tool_id": r.tool_id, "name": r.name, "content": r.content}
                for r in fallback_tool_results
            ],
        )

        yield (
            "event: done\n"
            f"data: {json.dumps({'run_id': run_data['run_id'], 'model': model_name, 'duration_ms': run_data['duration_ms']}, ensure_ascii=False)}\n\n"
        )


agent_runtime = AgentRuntime()
