from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.runtime import agent_runtime
from app.repositories.memory import store
from app.schemas.agents import AgentRunCreate

router = APIRouter()


@router.post("")
async def create_run(payload: AgentRunCreate) -> dict:
    agent = await store.get_agent(payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await agent_runtime.run(agent, payload.input)


@router.post("/stream")
async def stream_run(payload: AgentRunCreate) -> StreamingResponse:
    agent = await store.get_agent(payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return StreamingResponse(agent_runtime.stream(agent, payload.input), media_type="text/event-stream")
