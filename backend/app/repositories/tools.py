from __future__ import annotations

from time import perf_counter
from uuid import UUID

import httpx
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Tool
from app.schemas.tools import ToolCreate, ToolRead, ToolTestRequest, ToolTestResult, ToolUpdate


class ToolStore:
    async def list_tools(self) -> list[ToolRead]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Tool).order_by(Tool.created_at.desc()))
            return [self._to_read(tool) for tool in result.scalars().all()]

    async def get_tool(self, tool_id: str) -> ToolRead | None:
        tool_uuid = self._maybe_uuid(tool_id)
        if not tool_uuid:
            return None
        async with AsyncSessionLocal() as session:
            tool = await session.get(Tool, tool_uuid)
            if not tool:
                return None
            return self._to_read(tool)

    async def create_tool(self, payload: ToolCreate) -> ToolRead:
        async with AsyncSessionLocal() as session:
            tool = Tool(
                name=payload.name,
                type=payload.type,
                description=payload.description,
                config=payload.config.model_dump(),
                enabled=payload.enabled,
            )
            session.add(tool)
            await session.commit()
            await session.refresh(tool)
            return self._to_read(tool)

    async def update_tool(self, tool_id: str, payload: ToolUpdate) -> ToolRead | None:
        tool_uuid = self._maybe_uuid(tool_id)
        if not tool_uuid:
            return None
        async with AsyncSessionLocal() as session:
            tool = await session.get(Tool, tool_uuid)
            if not tool:
                return None
            tool.name = payload.name
            tool.type = payload.type
            tool.description = payload.description
            tool.config = payload.config.model_dump()
            tool.enabled = payload.enabled
            await session.commit()
            await session.refresh(tool)
            return self._to_read(tool)

    async def delete_tool(self, tool_id: str) -> bool:
        tool_uuid = self._maybe_uuid(tool_id)
        if not tool_uuid:
            return False
        async with AsyncSessionLocal() as session:
            tool = await session.get(Tool, tool_uuid)
            if not tool:
                return False
            await session.delete(tool)
            await session.commit()
            return True

    async def test_tool(self, tool_id: str, payload: ToolTestRequest) -> ToolTestResult:
        tool = await self.get_tool(tool_id)
        if not tool:
            raise KeyError("Tool not found")
        if tool.type != "http":
            return ToolTestResult(ok=False, error="Unsupported tool type")

        config = tool.config
        start = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=config.get("timeout_seconds", 20)) as client:
                response = await client.request(
                    method=config.get("method", "GET"),
                    url=config["url"],
                    headers=config.get("headers", {}),
                    params=config.get("query", {}),
                    json={**config.get("body", {}), **payload.input},
                )
                elapsed_ms = int((perf_counter() - start) * 1000)
                try:
                    output = response.json()
                except Exception:
                    output = response.text
                return ToolTestResult(
                    ok=response.is_success,
                    status_code=response.status_code,
                    elapsed_ms=elapsed_ms,
                    output=output,
                    error="" if response.is_success else response.text[:500],
                )
        except Exception as exc:
            elapsed_ms = int((perf_counter() - start) * 1000)
            return ToolTestResult(ok=False, elapsed_ms=elapsed_ms, error=str(exc))

    async def run_for_input(self, enabled_tool_ids: list[str], user_input: str) -> list[dict[str, str]]:
        enabled = {self._maybe_uuid(tool_id) for tool_id in enabled_tool_ids}
        enabled.discard(None)
        if not enabled:
            return []

        text = user_input.lower()
        results: list[dict[str, str]] = []
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(Tool).where(Tool.id.in_(enabled), Tool.enabled.is_(True))
                )
            ).scalars().all()

        for tool in rows:
            config = tool.config or {}
            keywords = [str(item).lower() for item in config.get("trigger_keywords", [])]
            if keywords and not any(keyword in text for keyword in keywords):
                continue
            test_result = await self.test_tool(str(tool.id), ToolTestRequest(input={"query": user_input}))
            content = test_result.output if test_result.ok else test_result.error
            results.append(
                {
                    "tool_id": str(tool.id),
                    "name": tool.name,
                    "content": str(content),
                }
            )

        return results

    def _to_read(self, tool: Tool) -> ToolRead:
        return ToolRead(
            id=str(tool.id),
            name=tool.name,
            type=tool.type,
            description=tool.description,
            config=tool.config or {},
            enabled=tool.enabled,
        )

    def _maybe_uuid(self, value: str) -> UUID | None:
        try:
            return UUID(value)
        except ValueError:
            return None


tool_store = ToolStore()
