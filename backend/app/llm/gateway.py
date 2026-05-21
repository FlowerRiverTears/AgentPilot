from collections.abc import AsyncIterator

import httpx

from app.core.config import settings
from app.schemas.settings import ModelConfigRead, ModelConfigUpdate


class LLMGateway:
    """OpenAI-compatible gateway with a local fallback for first-run development."""

    def __init__(self) -> None:
        self.base_url = settings.llm_base_url
        self.api_key = settings.llm_api_key
        self.default_model = settings.llm_default_model

    def get_config(self) -> ModelConfigRead:
        return ModelConfigRead(
            base_url=self.base_url,
            api_key_set=bool(self.api_key),
            default_model=self.default_model,
        )

    def update_config(self, payload: ModelConfigUpdate) -> ModelConfigRead:
        self.base_url = payload.base_url
        if payload.api_key:
            self.api_key = payload.api_key
        self.default_model = payload.default_model
        return self.get_config()

    async def chat(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        target_model = model or self.default_model
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": target_model,
                        "messages": messages,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception:
            return self._fallback_answer(messages)

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        content = await self.chat(messages, model=model)
        for token in content.split(" "):
            yield token + " "

    def _fallback_answer(self, messages: list[dict[str, str]]) -> str:
        user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return (
            "本地 LLM 尚未连接，当前返回开发模式回答。"
            f"收到的问题是：{user_text}。"
            "后续接入 OpenAI-compatible API 或 Ollama 后会返回真实模型结果。"
        )


llm_gateway = LLMGateway()
