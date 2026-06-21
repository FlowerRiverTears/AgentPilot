from __future__ import annotations

from time import perf_counter

import httpx
from sqlalchemy import select

from app.core.ssrf import is_url_safe
from app.db.session import AsyncSessionLocal
from app.models import Tool, ToolCall
from app.repositories.base import maybe_uuid
from app.schemas.tools import ToolCreate, ToolRead, ToolTestRequest, ToolTestResult, ToolUpdate


class ToolStore:
    async def list_tools(self) -> list[ToolRead]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Tool).order_by(Tool.created_at.desc()))
            return [self._to_read(tool) for tool in result.scalars().all()]

    async def get_tool(self, tool_id: str) -> ToolRead | None:
        tool_uuid = maybe_uuid(tool_id)
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
        tool_uuid = maybe_uuid(tool_id)
        if not tool_uuid:
            return None
        async with AsyncSessionLocal() as session:
            tool = await session.get(Tool, tool_uuid)
            if not tool:
                return None
            if payload.name is not None:
                tool.name = payload.name
            if payload.type is not None:
                tool.type = payload.type
            if payload.description is not None:
                tool.description = payload.description
            if payload.config is not None:
                tool.config = payload.config.model_dump()
            if payload.enabled is not None:
                tool.enabled = payload.enabled
            await session.commit()
            await session.refresh(tool)
            return self._to_read(tool)

    async def delete_tool(self, tool_id: str) -> bool:
        tool_uuid = maybe_uuid(tool_id)
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
        is_safe, reason = is_url_safe(config["url"])
        if not is_safe:
            return ToolTestResult(ok=False, error=f"URL blocked: {reason}")
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

    async def run_for_input(
        self, enabled_tool_ids: list[str], user_input: str, run_id: str | None = None
    ) -> list[dict[str, str]]:
        enabled = {maybe_uuid(tool_id) for tool_id in enabled_tool_ids}
        enabled.discard(None)
        if not enabled:
            return []

        run_uuid = maybe_uuid(run_id) if run_id else None
        text = user_input.lower()
        results: list[dict[str, str]] = []
        tool_calls: list[ToolCall] = []

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
                is_safe, reason = is_url_safe(config.get("url", ""))
                if not is_safe:
                    results.append(
                        {
                            "tool_id": str(tool.id),
                            "name": tool.name,
                            "content": f"URL blocked: {reason}",
                        }
                    )
                    tool_calls.append(
                        ToolCall(
                            run_id=run_uuid,
                            tool_id=tool.id,
                            tool_name=tool.name,
                            input=user_input,
                            output=f"URL blocked: {reason}",
                            status="failed",
                            error=f"URL blocked: {reason}",
                            detail={"ok": False},
                        )
                    )
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
                tool_calls.append(
                    ToolCall(
                        run_id=run_uuid,
                        tool_id=tool.id,
                        tool_name=tool.name,
                        input=user_input,
                        output=str(content),
                        status="success" if test_result.ok else "failed",
                        status_code=test_result.status_code,
                        elapsed_ms=test_result.elapsed_ms,
                        error=test_result.error or "",
                        detail={"ok": test_result.ok},
                    )
                )

            for tc in tool_calls:
                session.add(tc)
            await session.commit()

        return results

    async def list_tool_calls(self, limit: int = 50) -> list[dict]:
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(select(ToolCall).order_by(ToolCall.created_at.desc()).limit(limit))
            ).scalars().all()
            return [
                {
                    "id": str(row.id),
                    "run_id": str(row.run_id) if row.run_id else None,
                    "tool_id": str(row.tool_id) if row.tool_id else None,
                    "tool_name": row.tool_name,
                    "input": row.input,
                    "output": row.output,
                    "status": row.status,
                    "status_code": row.status_code,
                    "elapsed_ms": row.elapsed_ms,
                    "error": row.error,
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                }
                for row in rows
            ]

    def _to_read(self, tool: Tool) -> ToolRead:
        return ToolRead(
            id=str(tool.id),
            name=tool.name,
            type=tool.type,
            description=tool.description,
            config=tool.config or {},
            enabled=tool.enabled,
        )



tool_store = ToolStore()
