import json
from collections.abc import AsyncIterator
from time import perf_counter

from app.llm.gateway import llm_gateway
from app.repositories.memory import store
from app.repositories.tools import tool_store
from app.schemas.agents import AgentRead
from app.schemas.knowledge import RetrievedChunk
from app.tools import tool_registry

# 上下文压缩相关常量（后续可移到 config.py）
CONTEXT_TOKEN_THRESHOLD = 6000  # 触发压缩的 Token 阈值（约 10K 上下文窗口的 60%）
RECENT_TURNS = 6  # 压缩时保留的最近轮数（一轮 = user + assistant，对应 12 条消息）


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

    def _estimate_messages_tokens(self, messages: list[dict]) -> int:
        """粗估消息列表的 Token 数。中文约 1 字 ≈ 1.5 Token，英文约 4 字符 ≈ 1 Token。"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            chinese_chars = sum(1 for c in content if "\u4e00" <= c <= "\u9fff")
            other_chars = len(content) - chinese_chars
            total += int(chinese_chars * 1.5 + other_chars / 4)
        return total

    async def _build_messages(
        self,
        agent: AgentRead,
        user_input: str,
        context: str,
        tool_context: str,
        messages: list[dict[str, str]] | None = None,
    ) -> tuple[list[dict[str, str]], bool]:
        """构建发送给 LLM 的消息列表，并在 Token 超阈值时进行上下文压缩。

        返回 (chat_messages, compressed)，compressed 表示是否触发了压缩。
        """
        system_prompt = (
            f"{agent.system_prompt}\n\n"
            "RAG 回答要求：优先依据工具结果和知识库上下文回答；"
            "使用知识库内容时必须标注来源或 chunk_id；"
            "上下文不足时明确说明无法从当前资料确认，不要编造。"
        )
        chat_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # 过滤出有效的历史消息
        history: list[dict[str, str]] = []
        if messages:
            history = [
                {"role": message["role"], "content": message["content"]}
                for message in messages
                if message.get("role") in {"user", "assistant"} and message.get("content")
            ]

        compressed = False
        # 上下文压缩：当历史消息 Token 估算超过阈值时，保留最近 RECENT_TURNS 轮原文，
        # 对早期消息生成摘要并替换。
        if history and self._estimate_messages_tokens(history) > CONTEXT_TOKEN_THRESHOLD:
            keep_count = RECENT_TURNS * 2  # 每轮 2 条消息
            if len(history) > keep_count:
                early_messages = history[:-keep_count]
                recent_messages = history[-keep_count:]
                summary = await llm_gateway.summarize_messages(early_messages)
                if summary:
                    # 用摘要替换早期消息，作为 system 角色注入
                    chat_messages.append(
                        {
                            "role": "system",
                            "content": f"以下是之前对话的摘要，供你参考：\n{summary}",
                        }
                    )
                    chat_messages.extend(recent_messages)
                    compressed = True
                else:
                    # 摘要失败，回退到只保留最近消息
                    chat_messages.extend(recent_messages)
                    compressed = True
            else:
                chat_messages.extend(history)
        else:
            chat_messages.extend(history)

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
        return chat_messages, compressed

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
        chat_messages, _compressed = await self._build_messages(agent, user_input, context, tool_context, messages)
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

        chat_messages, compressed = await self._build_messages(agent, user_input, context, tool_context, messages)

        full_answer = ""
        generation_status = "完成"
        error_message = ""
        try:
            async for token in llm_gateway.stream_chat(
                chat_messages,
                model=agent.model,
                config_id=model_config_id,
            ):
                full_answer += token
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            generation_status = "失败"
            error_message = str(exc)
            yield f"event: error\ndata: {json.dumps({'message': error_message, 'type': 'generation_failed'}, ensure_ascii=False)}\n\n"

        steps.append(
            {"name": "大模型生成", "status": generation_status, "detail": f"使用模型：{model_name}"}
        )

        run_status = "failed" if generation_status == "失败" else "completed"
        run_data = await store.create_run(
            agent_id=agent.id,
            user_input=user_input,
            answer=full_answer,
            citations=retrieved,
            steps=steps,
            model=model_name,
            status=run_status,
            duration_ms=int((perf_counter() - started_at) * 1000),
            tool_results=database_tool_results
            + [
                {"tool_id": r.tool_id, "name": r.name, "content": r.content}
                for r in fallback_tool_results
            ],
            error=error_message or None,
        )

        done_payload = {
            "run_id": run_data["run_id"],
            "model": model_name,
            "duration_ms": run_data["duration_ms"],
        }
        if compressed:
            done_payload["compressed"] = True
        yield (
            "event: done\n"
            f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
        )


agent_runtime = AgentRuntime()
