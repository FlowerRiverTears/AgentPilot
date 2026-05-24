from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.runtime import agent_runtime
from app.repositories.memory import store
from app.schemas.agents import AgentRunCreate, AgentRunDetail, AgentRunSummary

router = APIRouter()


@router.get("", response_model=list[AgentRunSummary])
async def list_runs() -> list[AgentRunSummary]:
    return await store.list_runs()


@router.post("")
async def create_run(payload: AgentRunCreate) -> dict:
    agent = await store.get_agent(payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    messages = [{"role": m.role, "content": m.content} for m in payload.messages] if payload.messages else None
    return await agent_runtime.run(agent, payload.input, messages=messages)


@router.get("/{run_id}", response_model=AgentRunDetail)
async def get_run(run_id: str) -> AgentRunDetail:
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/stream")
async def stream_run(payload: AgentRunCreate) -> StreamingResponse:
    agent = await store.get_agent(payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    messages = [{"role": m.role, "content": m.content} for m in payload.messages] if payload.messages else None
    return StreamingResponse(
        agent_runtime.stream(agent, payload.input, messages=messages),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
