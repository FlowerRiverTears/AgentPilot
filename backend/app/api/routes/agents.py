from fastapi import APIRouter, HTTPException

from app.repositories.memory import store
from app.schemas.agents import AgentCreate, AgentRead, AgentUpdate

router = APIRouter()


@router.get("", response_model=list[AgentRead])
async def list_agents() -> list[AgentRead]:
    return await store.list_agents()


@router.get("/published", response_model=list[AgentRead])
async def list_published_agents() -> list[AgentRead]:
    return await store.list_published_agents()


@router.post("", response_model=AgentRead, status_code=201)
async def create_agent(payload: AgentCreate) -> AgentRead:
    return await store.create_agent(payload)


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(agent_id: str) -> AgentRead:
    agent = await store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}", response_model=AgentRead)
async def update_agent(agent_id: str, payload: AgentUpdate) -> AgentRead:
    agent = await store.update_agent(agent_id, payload)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/publish", response_model=AgentRead)
async def publish_agent(agent_id: str) -> AgentRead:
    agent = await store.set_agent_status(agent_id, "published")
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/unpublish", response_model=AgentRead)
async def unpublish_agent(agent_id: str) -> AgentRead:
    agent = await store.set_agent_status(agent_id, "draft")
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/duplicate", response_model=AgentRead, status_code=201)
async def duplicate_agent(agent_id: str) -> AgentRead:
    agent = await store.duplicate_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str) -> None:
    deleted = await store.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
