from collections.abc import AsyncIterator

import httpx
from sqlalchemy import select, update

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import ModelConfig
from app.schemas.settings import ModelConfigCreate, ModelConfigRead, ModelConfigTestResult, ModelConfigUpdate


class LLMGateway:
    """OpenAI-compatible gateway with a local fallback for first-run development."""

    def __init__(self) -> None:
        self.base_url = settings.llm_base_url
        self.api_key = settings.llm_api_key
        self.default_model = settings.llm_default_model
        self.config_name = "ollama"

    async def ensure_defaults(self) -> None:
        async with AsyncSessionLocal() as session:
            existing = (
                await session.execute(select(ModelConfig).where(ModelConfig.is_default.is_(True)))
            ).scalars().first()
            if existing:
                self._apply_row(existing)
                return

            row = ModelConfig(
                name=self.config_name,
                base_url=self.base_url,
                api_key=self.api_key,
                default_model=self.default_model,
                is_default=True,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            self._apply_row(row)

    async def list_configs(self) -> list[ModelConfigRead]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ModelConfig).order_by(ModelConfig.is_default.desc(), ModelConfig.name.asc()))
            return [self._row_to_read(row) for row in result.scalars().all()]

    async def get_config_by_id(self, config_id: str) -> ModelConfigRead | None:
        async with AsyncSessionLocal() as session:
            row = await session.get(ModelConfig, config_id)
            if not row:
                return None
            return self._row_to_read(row)

    async def get_config(self) -> ModelConfigRead:
        await self.ensure_defaults()
        return ModelConfigRead(
            id="runtime",
            name=self.config_name,
            base_url=self.base_url,
            api_key_set=bool(self.api_key),
            default_model=self.default_model,
            is_default=True,
        )

    async def create_config(self, payload: ModelConfigCreate) -> ModelConfigRead:
        async with AsyncSessionLocal() as session:
            if payload.is_default:
                await self._clear_default(session)

            row = ModelConfig(
                name=payload.name,
                base_url=payload.base_url,
                api_key=payload.api_key,
                default_model=payload.default_model,
                is_default=payload.is_default,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            if row.is_default:
                self._apply_row(row)
            return self._row_to_read(row)

    async def update_config(self, config_id: str, payload: ModelConfigUpdate) -> ModelConfigRead:
        async with AsyncSessionLocal() as session:
            row = await session.get(ModelConfig, config_id)
            if not row:
                raise KeyError("Model config not found")

            if payload.is_default:
                await self._clear_default(session)

            row.name = payload.name
            row.base_url = payload.base_url
            if payload.api_key:
                row.api_key = payload.api_key
            row.default_model = payload.default_model
            row.is_default = payload.is_default
            await session.commit()
            await session.refresh(row)
            if row.is_default:
                self._apply_row(row)
            return self._row_to_read(row)

    async def set_default(self, config_id: str) -> ModelConfigRead:
        async with AsyncSessionLocal() as session:
            row = await session.get(ModelConfig, config_id)
            if not row:
                raise KeyError("Model config not found")
            await self._clear_default(session)
            row.is_default = True
            await session.commit()
            await session.refresh(row)
            self._apply_row(row)
            return self._row_to_read(row)

    async def delete_config(self, config_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            row = await session.get(ModelConfig, config_id)
            if not row:
                return False
            was_default = row.is_default
            await session.delete(row)
            await session.commit()
            if was_default:
                await self.ensure_defaults()
            return True

    async def test_config(self, config_id: str) -> ModelConfigTestResult:
        config = await self._get_config_row(config_id)
        if not config:
            raise KeyError("Model config not found")

        try:
            content = await self._chat_completion(
                config.base_url,
                config.api_key,
                config.default_model,
                [{"role": "user", "content": "请只回复 OK，用于连通性测试。"}],
                timeout=20,
            )
            return ModelConfigTestResult(ok=True, message=content.strip() or "OK")
        except Exception as exc:
            return ModelConfigTestResult(ok=False, message=self._format_error(exc))

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        config_id: str | None = None,
        fallback: bool = True,
    ) -> str:
        target_model = model
        base_url = self.base_url
        api_key = self.api_key
        default_model = self.default_model

        if config_id:
            config = await self._get_config_row(config_id)
            if config:
                base_url = config.base_url
                api_key = config.api_key
                default_model = config.default_model
                target_model = target_model or config.default_model

        target_model = target_model or default_model
        try:
            return await self._chat_completion(
                base_url,
                api_key,
                target_model,
                messages,
                timeout=settings.llm_request_timeout_seconds,
            )
        except Exception as exc:
            if not fallback:
                raise RuntimeError(self._format_error(exc)) from exc
            return self._fallback_answer(messages)

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        config_id: str | None = None,
    ) -> AsyncIterator[str]:
        content = await self.chat(messages, model=model, config_id=config_id)
        for token in content.split(" "):
            yield token + " "

    def _fallback_answer(self, messages: list[dict[str, str]]) -> str:
        user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        question = self._extract_section(user_text, "用户问题：", "\n\n知识库上下文：") or user_text
        context = self._extract_section(user_text, "知识库上下文：", "\n\n请给出清晰回答")

        if context and context != "无":
            return (
                "当前未连接真实大模型，以下是基于知识库检索结果生成的开发模式回答：\n\n"
                f"问题：{question.strip()}\n\n"
                "回答：\n"
                f"{self._summarize_context(context)}\n\n"
                "来源：知识库检索片段。"
            )

        return (
            "当前未连接真实大模型，且没有命中知识库内容。"
            f"收到的问题是：{question.strip()}。"
            "请在“模型配置”页面填写可用的接口地址、Token 和模型名，或先为智能体绑定知识库。"
        )

    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> str:
        if start_marker not in text:
            return ""
        start = text.index(start_marker) + len(start_marker)
        end = text.find(end_marker, start)
        if end == -1:
            return text[start:].strip()
        return text[start:end].strip()

    def _summarize_context(self, context: str) -> str:
        clean_lines = [line.strip() for line in context.splitlines() if line.strip()]
        clean_text = " ".join(clean_lines)
        if len(clean_text) <= 500:
            return clean_text
        return f"{clean_text[:500]}..."

    async def _clear_default(self, session) -> None:
        await session.execute(update(ModelConfig).values(is_default=False))

    def _apply_row(self, row: ModelConfig) -> None:
        self.config_name = row.name
        self.base_url = row.base_url
        self.api_key = row.api_key
        self.default_model = row.default_model

    def _row_to_read(self, row: ModelConfig) -> ModelConfigRead:
        return ModelConfigRead(
            id=str(row.id),
            name=row.name,
            base_url=row.base_url,
            api_key_set=bool(row.api_key),
            default_model=row.default_model,
            is_default=row.is_default,
        )

    async def _get_config_row(self, config_id: str) -> ModelConfig | None:
        async with AsyncSessionLocal() as session:
            return await session.get(ModelConfig, config_id)

    async def _chat_completion(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
        timeout: int,
    ) -> str:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _format_error(self, exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            return f"HTTP {exc.response.status_code}: {exc.response.text[:500]}"
        return str(exc)


llm_gateway = LLMGateway()
