from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.runtime import get_agent_runtime
from app.core.deps import get_current_user, get_optional_user
from app.repositories.memory import get_store
from app.schemas.agents import AgentRunCreate, AgentRunDetail, AgentRunSummary

router = APIRouter()


@router.get("", response_model=list[AgentRunSummary])
async def list_runs(limit: int = 50, offset: int = 0, _user=Depends(get_current_user)) -> list[AgentRunSummary]:
    return await get_store().list_runs(limit=limit, offset=offset)


@router.post("")
async def create_run(payload: AgentRunCreate, _user=Depends(get_optional_user)) -> dict:
    agent = await get_store().get_agent(payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    messages = [{"role": m.role, "content": m.content} for m in payload.messages] if payload.messages else None
    return await get_agent_runtime().run(
        agent, payload.input, messages=messages, file_content=payload.file_content
    )


@router.get("/{run_id}", response_model=AgentRunDetail)
async def get_run(run_id: str, _user=Depends(get_current_user)) -> AgentRunDetail:
    run = await get_store().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/retry")
async def retry_run(run_id: str, _user=Depends(get_current_user)) -> dict:
    """根据历史 run 重新执行一次。"""
    run = await get_store().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    agent = await get_store().get_agent(run.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await get_agent_runtime().run(agent, run.input)


@router.post("/stream")
async def stream_run(payload: AgentRunCreate, _user=Depends(get_optional_user)) -> StreamingResponse:
    agent = await get_store().get_agent(payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    messages = [{"role": m.role, "content": m.content} for m in payload.messages] if payload.messages else None
    return StreamingResponse(
        get_agent_runtime().stream(
            agent, payload.input, messages=messages, file_content=payload.file_content
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
