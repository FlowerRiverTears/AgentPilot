from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.core.deps import get_current_user
from app.repositories.memory import store
from app.schemas.agents import AgentCreate, AgentRead, AgentUpdate

router = APIRouter()


@router.get("", response_model=list[AgentRead])
async def list_agents(_user=Depends(get_current_user)) -> list[AgentRead]:
    return await store.list_agents()


@router.get("/published", response_model=list[AgentRead])
async def list_published_agents() -> list[AgentRead]:
    return await store.list_published_agents()


@router.post("", response_model=AgentRead, status_code=201)
async def create_agent(payload: AgentCreate, _user=Depends(get_current_user)) -> AgentRead:
    return await store.create_agent(payload)


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(agent_id: str, _user=Depends(get_current_user)) -> AgentRead:
    agent = await store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}", response_model=AgentRead)
async def update_agent(agent_id: str, payload: AgentUpdate, _user=Depends(get_current_user)) -> AgentRead:
    agent = await store.update_agent(agent_id, payload)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/publish", response_model=AgentRead)
async def publish_agent(agent_id: str, _user=Depends(get_current_user)) -> AgentRead:
    agent = await store.set_agent_status(agent_id, "published")
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/unpublish", response_model=AgentRead)
async def unpublish_agent(agent_id: str, _user=Depends(get_current_user)) -> AgentRead:
    agent = await store.set_agent_status(agent_id, "draft")
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/duplicate", response_model=AgentRead, status_code=201)
async def duplicate_agent(agent_id: str, _user=Depends(get_current_user)) -> AgentRead:
    agent = await store.duplicate_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, _user=Depends(get_current_user)) -> None:
    deleted = await store.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/import", response_model=AgentRead, status_code=201)
async def import_agent(payload: AgentCreate, _user=Depends(get_current_user)) -> AgentRead:
    """导入智能体配置，创建新智能体（名称加 (导入) 后缀）。"""
    imported_payload = AgentCreate(
        name=f"{payload.name} (导入)",
        description=payload.description,
        system_prompt=payload.system_prompt,
        model=payload.model,
        model_config_id=payload.model_config_id,
        knowledge_base_ids=payload.knowledge_base_ids,
        tool_ids=payload.tool_ids,
    )
    return await store.create_agent(imported_payload)


@router.get("/{agent_id}/export")
async def export_agent(agent_id: str, _user=Depends(get_current_user)) -> JSONResponse:
    """导出智能体配置为 JSON 文件。"""
    agent = await store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    export_data = {
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "model": agent.model,
        "model_config_id": agent.model_config_id,
        "knowledge_base_ids": list(agent.knowledge_base_ids),
        "tool_ids": list(agent.tool_ids),
        "exported_at": datetime.now().isoformat(),
    }
    return JSONResponse(content=export_data)
