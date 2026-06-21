import asyncio
import json
import re
from collections.abc import AsyncIterator
from time import perf_counter

from app.llm.gateway import get_llm_gateway
from app.repositories.memory import get_store
from app.repositories.tools import tool_store
from app.schemas.agents import AgentRead
from app.schemas.knowledge import RetrievedChunk
from app.schemas.tools import ToolTestRequest
from app.tools import tool_registry
from app.core.config import settings

# Use settings values instead of hardcoded constants
CONTEXT_TOKEN_THRESHOLD = settings.context_token_threshold
RECENT_TURNS = settings.recent_turns


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
        _depth: int = 0,
        file_content: str = "",
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

        # 多 Agent 协作：注入子智能体调用说明（递归深度限制内）
        if _depth < 3 and getattr(agent, "sub_agent_ids", None):
            sub_agent_lines: list[str] = []
            for sub_id in agent.sub_agent_ids:
                sub_agent = await get_store().get_agent(sub_id)
                if sub_agent:
                    sub_agent_lines.append(
                        f"- 子智能体「{sub_agent.name}」(ID: {sub_id})：{sub_agent.description}"
                    )
            if sub_agent_lines:
                system_prompt += (
                    "\n\n你可以调用以下子智能体来协助回答：\n"
                    + "\n".join(sub_agent_lines)
                    + "\n调用方式：在回答中输出 <call_agent:子agent_id>你的问题</call_agent>"
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
                summary = await get_llm_gateway().summarize_messages(early_messages)
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
                    f"{'用户上传文件内容：' + chr(10) + file_content + chr(10) if file_content else ''}"
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
            config = await get_llm_gateway().get_config_by_id(config_id)
            if config:
                return config.default_model

        runtime_config = await get_llm_gateway().get_config()
        return runtime_config.default_model

    async def _run_tool_chain(
        self,
        tool_chain: list[dict],
        user_input: str,
        steps: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """按链式顺序调用工具，前序工具的输出可作为后序工具的输入。

        input_mapping 中：
        - $user_input 映射到用户原始输入
        - $prev_output 映射到前一个工具的输出
        """
        results: list[dict[str, str]] = []
        prev_output = ""
        for index, step in enumerate(tool_chain):
            tool_id = step.get("tool_id", "")
            input_mapping = step.get("input_mapping", {})
            tool_input: dict[str, str] = {}
            for key, value in input_mapping.items():
                if value == "$user_input":
                    tool_input[key] = user_input
                elif value == "$prev_output":
                    tool_input[key] = prev_output
                else:
                    tool_input[key] = str(value)

            tool = await tool_store.get_tool(tool_id)
            tool_name = tool.name if tool else tool_id
            try:
                test_result = await tool_store.test_tool(
                    tool_id, ToolTestRequest(input=tool_input)
                )
                content = str(test_result.output) if test_result.ok else str(test_result.error)
                status = "完成" if test_result.ok else "失败"
            except Exception as exc:
                content = f"工具调用失败：{exc}"
                status = "失败"

            results.append({"tool_id": tool_id, "name": tool_name, "content": content})
            prev_output = content
            steps.append(
                {
                    "name": f"工具链调用-{index + 1}",
                    "status": status,
                    "detail": f"调用工具「{tool_name}」(ID: {tool_id})",
                }
            )
        return results

    async def _call_single_sub_agent(
        self,
        sub_id: str,
        question: str,
        original_tag: str,
        steps: list[dict[str, str]],
        depth: int = 0,
    ) -> tuple[str, str]:
        """调用单个子智能体，返回 (替换文本, 追加内容)。"""
        sub_agent = await get_store().get_agent(sub_id)
        if not sub_agent:
            steps.append(
                {"name": "子智能体调用", "status": "失败", "detail": f"未找到子智能体 {sub_id}"}
            )
            appended = f"\n[子智能体调用失败：未找到 ID 为 {sub_id} 的智能体]"
            return original_tag + appended, appended
        try:
            sub_result = await self.run(sub_agent, question, _depth=depth + 1)
            sub_answer = sub_result.get("answer", "")
            steps.append(
                {
                    "name": "子智能体调用",
                    "status": "完成",
                    "detail": f"调用子智能体「{sub_agent.name}」(ID: {sub_id})，问题：{question}",
                }
            )
            appended = f"\n[子智能体「{sub_agent.name}」的回答]\n{sub_answer}"
            return original_tag + appended, appended
        except Exception as exc:
            steps.append(
                {
                    "name": "子智能体调用",
                    "status": "失败",
                    "detail": f"调用子智能体「{sub_agent.name}」失败：{exc}",
                }
            )
            appended = f"\n[子智能体「{sub_agent.name}」调用失败：{exc}]"
            return original_tag + appended, appended

    async def _resolve_sub_agent_calls(
        self,
        answer: str,
        steps: list[dict[str, str]],
        depth: int = 0,
    ) -> tuple[str, list[str]]:
        """解析回答中的 <call_agent:xxx>...</call_agent> 标签，调用子智能体并整合结果。

        返回 (新回答, 追加内容列表)，追加内容列表用于流式输出。
        """
        pattern = re.compile(r"<call_agent:([^>]+)>(.*?)</call_agent>", re.DOTALL)
        matches = list(pattern.finditer(answer))
        if not matches:
            return answer, []

        result_parts: list[str] = []
        appended_texts: list[str] = []
        last_end = 0
        for match in matches:
            result_parts.append(answer[last_end : match.start()])
            sub_id = match.group(1).strip()
            question = match.group(2).strip()
            original_tag = match.group(0)
            replacement, appended = await self._call_single_sub_agent(
                sub_id, question, original_tag, steps, depth
            )
            result_parts.append(replacement)
            if appended:
                appended_texts.append(appended)
            last_end = match.end()
        result_parts.append(answer[last_end:])
        return "".join(result_parts), appended_texts

    async def _build_context(
        self,
        agent: AgentRead,
        user_input: str,
        messages: list[dict[str, str]] | None = None,
        _depth: int = 0,
        file_content: str = "",
    ) -> dict:
        """Build execution context shared by run() and stream().

        Returns dict with keys: retrieved, database_tool_results,
        fallback_tool_results, tool_chain_steps, tool_chain_results,
        context, tool_context, model_name, model_config_id,
        chat_messages, compressed, initial_steps, merged_tool_results
        """
        retrieved = await get_store().retrieve_for_agent(agent.id, user_input, top_k=3)
        database_tool_results = await tool_store.run_for_input(agent.tool_ids, user_input)
        fallback_tool_results = await tool_registry.run_for_input(agent.tool_ids, user_input)
        model_config_id = agent.model_config_id

        # 工具调用链编排：按链式顺序调用工具
        tool_chain_steps: list[dict[str, str]] = []
        tool_chain_results: list[dict[str, str]] = []
        if getattr(agent, "tool_chain", None):
            tool_chain_results = await self._run_tool_chain(
                agent.tool_chain, user_input, tool_chain_steps
            )

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
        if tool_chain_results:
            chain_context = "\n\n".join(
                f"工具链：{result['name']}\n结果：\n{result['content']}"
                for result in tool_chain_results
            )
            tool_context = f"{tool_context}\n\n{chain_context}" if tool_context else chain_context
        model_name = await self._resolve_model_name(agent)
        chat_messages, compressed = await self._build_messages(
            agent, user_input, context, tool_context, messages, _depth=_depth, file_content=file_content
        )

        initial_steps = [
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
        ] + tool_chain_steps

        merged_tool_results = database_tool_results + [
            {"tool_id": r.tool_id, "name": r.name, "content": r.content}
            for r in fallback_tool_results
        ] + tool_chain_results

        return {
            "retrieved": retrieved,
            "database_tool_results": database_tool_results,
            "fallback_tool_results": fallback_tool_results,
            "tool_chain_steps": tool_chain_steps,
            "tool_chain_results": tool_chain_results,
            "context": context,
            "tool_context": tool_context,
            "model_name": model_name,
            "model_config_id": model_config_id,
            "chat_messages": chat_messages,
            "compressed": compressed,
            "initial_steps": initial_steps,
            "merged_tool_results": merged_tool_results,
        }

    async def _create_run_record(
        self,
        agent: AgentRead,
        user_input: str,
        answer: str,
        retrieved: list,
        initial_steps: list,
        merged_tool_results: list,
        model_name: str,
        generation_status: str,
        error_message: str,
        started_at: float,
        sub_agent_steps: list[dict[str, str]],
    ) -> dict:
        """Create a run record with the given execution results (shared by run and stream)."""
        steps = initial_steps + [
            {"name": "大模型生成", "status": generation_status, "detail": f"使用模型：{model_name}"}
        ] + sub_agent_steps
        run_status = "failed" if generation_status == "失败" else "completed"
        return await get_store().create_run(
            agent_id=agent.id,
            user_input=user_input,
            answer=answer,
            citations=retrieved,
            steps=steps,
            model=model_name,
            status=run_status,
            duration_ms=int((perf_counter() - started_at) * 1000),
            tool_results=merged_tool_results,
            error=error_message or None,
        )

    async def run(
        self,
        agent: AgentRead,
        user_input: str,
        messages: list[dict[str, str]] | None = None,
        _depth: int = 0,
        file_content: str = "",
    ) -> dict:
        started_at = perf_counter()
        ctx = await self._build_context(agent, user_input, messages, _depth=_depth, file_content=file_content)

        generation_status = "完成"
        error_message = ""
        try:
            answer = await get_llm_gateway().chat(
                ctx["chat_messages"],
                model=agent.model,
                config_id=ctx["model_config_id"],
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

        # 多 Agent 协作：解析子智能体调用标签并执行（递归深度限制内）
        sub_agent_steps: list[dict[str, str]] = []
        if _depth < 3 and generation_status == "完成":
            answer, _appended = await self._resolve_sub_agent_calls(
                answer, sub_agent_steps, _depth
            )

        return await self._create_run_record(
            agent=agent,
            user_input=user_input,
            answer=answer,
            retrieved=ctx["retrieved"],
            initial_steps=ctx["initial_steps"],
            merged_tool_results=ctx["merged_tool_results"],
            model_name=ctx["model_name"],
            generation_status=generation_status,
            error_message=error_message,
            started_at=started_at,
            sub_agent_steps=sub_agent_steps,
        )

    async def stream(
        self,
        agent: AgentRead,
        user_input: str,
        messages: list[dict[str, str]] | None = None,
        _depth: int = 0,
        file_content: str = "",
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[str]:
        started_at = perf_counter()

        # 工具调用进度：推送工具调用开始事件
        tool_ids = getattr(agent, "tool_ids", None) or []
        if tool_ids:
            yield (
                "event: tool_progress\n"
                f"data: {json.dumps({'tool_names': tool_ids, 'status': 'running'}, ensure_ascii=False)}\n\n"
            )

        ctx = await self._build_context(agent, user_input, messages, _depth=_depth, file_content=file_content)

        # 工具调用完成
        if tool_ids:
            yield (
                "event: tool_progress\n"
                f"data: {json.dumps({'tool_names': tool_ids, 'status': 'done'}, ensure_ascii=False)}\n\n"
            )

        yield f"event: steps\ndata: {json.dumps(ctx['initial_steps'], ensure_ascii=False)}\n\n"

        citations_data = [chunk.model_dump() for chunk in ctx["retrieved"]]
        yield f"event: citations\ndata: {json.dumps(citations_data, ensure_ascii=False)}\n\n"

        full_answer = ""
        generation_status = "完成"
        error_message = ""
        try:
            async for token in get_llm_gateway().stream_chat(
                ctx["chat_messages"],
                model=agent.model,
                config_id=ctx["model_config_id"],
            ):
                # 检查取消信号
                if cancel_event and cancel_event.is_set():
                    generation_status = "已取消"
                    full_answer += "\n\n[生成已被用户取消]"
                    yield (
                        "event: cancelled\n"
                        f"data: {json.dumps({'message': '生成已被取消'}, ensure_ascii=False)}\n\n"
                    )
                    break
                full_answer += token
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            generation_status = "失败"
            error_message = str(exc)
            yield f"event: error\ndata: {json.dumps({'message': error_message, 'type': 'generation_failed'}, ensure_ascii=False)}\n\n"

        # 多 Agent 协作：在 LLM 生成后解析子智能体调用标签并执行（递归深度限制内）
        sub_agent_steps: list[dict[str, str]] = []
        if _depth < 3 and generation_status == "完成":
            new_answer, appended_texts = await self._resolve_sub_agent_calls(
                full_answer, sub_agent_steps, _depth
            )
            if appended_texts:
                for text in appended_texts:
                    yield f"data: {json.dumps({'token': text}, ensure_ascii=False)}\n\n"
                full_answer = new_answer

        run_data = await self._create_run_record(
            agent=agent,
            user_input=user_input,
            answer=full_answer,
            retrieved=ctx["retrieved"],
            initial_steps=ctx["initial_steps"],
            merged_tool_results=ctx["merged_tool_results"],
            model_name=ctx["model_name"],
            generation_status=generation_status,
            error_message=error_message,
            started_at=started_at,
            sub_agent_steps=sub_agent_steps,
        )

        done_payload = {
            "run_id": run_data["run_id"],
            "model": ctx["model_name"],
            "duration_ms": run_data["duration_ms"],
        }
        if ctx["compressed"]:
            done_payload["compressed"] = True
        yield (
            "event: done\n"
            f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
        )


_agent_runtime = None


def get_agent_runtime() -> "AgentRuntime":
    """Lazy-initialized agent runtime singleton."""
    global _agent_runtime
    if _agent_runtime is None:
        _agent_runtime = AgentRuntime()
    return _agent_runtime
