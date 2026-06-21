import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.runtime import get_agent_runtime
from app.repositories.memory import get_store

router = APIRouter()


def parse_sse_to_ws(sse_chunk: str) -> dict | None:
    """将 SSE 格式字符串解析为 WebSocket 消息字典。

    SSE 格式有两种：
    - 带事件名：`event: steps\ndata: [...]\n\n` → {"event": "steps", "data": [...]}
    - 仅数据（默认 token 事件）：`data: {"token": "..."}\n\n` → {"event": "token", "data": {"token": "..."}}

    返回 None 表示无法解析的空块。
    """
    event_name: str | None = None
    data_lines: list[str] = []

    for line in sse_chunk.splitlines():
        if not line:
            continue
        if line.startswith("event:"):
            event_name = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())

    if not data_lines:
        return None

    raw_data = "\n".join(data_lines)
    try:
        parsed_data = json.loads(raw_data)
    except json.JSONDecodeError:
        # JSON 解析失败时，原样作为字符串返回
        parsed_data = raw_data

    # 没有 event 字段时，默认为 token 事件
    if not event_name:
        event_name = "token"

    return {"event": event_name, "data": parsed_data}


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    """WebSocket 聊天端点，支持取消生成和工具调用进度。

    客户端连接后发送 JSON 消息：
    - 聊天请求：{"agent_id": "xxx", "input": "用户问题", "messages": [...], "file_content": ""}
    - 取消请求：{"action": "cancel"}
    - 心跳：{"type": "ping"}

    服务端推送事件：
    - {"event": "tool_progress", "data": {"tool_names": [...], "status": "running|done"}}
    - {"event": "steps", "data": [...]}
    - {"event": "citations", "data": [...]}
    - {"event": "token", "data": {"token": "..."}}
    - {"event": "cancelled", "data": {"message": "..."}}
    - {"event": "error", "data": {"message": "..."}}
    - {"event": "done", "data": {"run_id": "...", "model": "...", "duration_ms": 123}}
    - {"event": "pong", "data": {}}
    """
    await websocket.accept()
    cancel_event: asyncio.Event | None = None
    current_task: asyncio.Task | None = None

    async def handle_chat(payload: dict, cancel_evt: asyncio.Event):
        """处理聊天请求，将 SSE 流转换为 WebSocket 消息。"""
        agent_id = payload.get("agent_id")
        user_input = payload.get("input", "")
        messages = payload.get("messages", [])
        file_content = payload.get("file_content", "")

        agent = await get_store().get_agent(agent_id)
        if not agent:
            await websocket.send_text(
                json.dumps(
                    {"event": "error", "data": {"message": "Agent not found"}},
                    ensure_ascii=False,
                )
            )
            return

        async for sse_chunk in get_agent_runtime().stream(
            agent, user_input, messages=messages, file_content=file_content,
            cancel_event=cancel_evt,
        ):
            ws_message = parse_sse_to_ws(sse_chunk)
            if ws_message:
                await websocket.send_text(json.dumps(ws_message, ensure_ascii=False))

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            # 处理取消请求
            if payload.get("action") == "cancel":
                if cancel_event:
                    cancel_event.set()
                if current_task and not current_task.done():
                    current_task.cancel()
                await websocket.send_text(
                    json.dumps(
                        {"event": "cancelled", "data": {"message": "生成已取消"}},
                        ensure_ascii=False,
                    )
                )
                continue

            # 处理心跳
            if payload.get("type") == "ping":
                await websocket.send_text(
                    json.dumps({"event": "pong", "data": {}}, ensure_ascii=False)
                )
                continue

            # 处理聊天请求
            cancel_event = asyncio.Event()
            current_task = asyncio.create_task(handle_chat(payload, cancel_event))

    except WebSocketDisconnect:
        # 断开时取消正在进行的任务
        if cancel_event:
            cancel_event.set()
        if current_task and not current_task.done():
            current_task.cancel()
    except Exception as exc:
        try:
            await websocket.send_text(
                json.dumps(
                    {"event": "error", "data": {"message": str(exc)}},
                    ensure_ascii=False,
                )
            )
        except Exception:
            pass
