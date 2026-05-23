from fastapi import APIRouter, HTTPException

from app.repositories.memory import store
from app.schemas.agents import AgentCreate, AgentRead

router = APIRouter()


@router.get("", response_model=list[AgentRead])
async def list_agents() -> list[AgentRead]:
    return await store.list_agents()


@router.post("", response_model=AgentRead, status_code=201)
async def create_agent(payload: AgentCreate) -> AgentRead:
    return await store.create_agent(payload)


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(agent_id: str) -> AgentRead:
    agent = await store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
