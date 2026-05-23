from fastapi import APIRouter, HTTPException

from app.repositories.tools import tool_store
from app.schemas.tools import ToolCreate, ToolRead, ToolTestRequest, ToolTestResult, ToolUpdate

router = APIRouter()


@router.get("", response_model=list[ToolRead])
async def list_tools() -> list[ToolRead]:
    return await tool_store.list_tools()


@router.post("", response_model=ToolRead, status_code=201)
async def create_tool(payload: ToolCreate) -> ToolRead:
    return await tool_store.create_tool(payload)


@router.get("/{tool_id}", response_model=ToolRead)
async def get_tool(tool_id: str) -> ToolRead:
    tool = await tool_store.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.put("/{tool_id}", response_model=ToolRead)
async def update_tool(tool_id: str, payload: ToolUpdate) -> ToolRead:
    tool = await tool_store.update_tool(tool_id, payload)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.delete("/{tool_id}", status_code=204)
async def delete_tool(tool_id: str) -> None:
    deleted = await tool_store.delete_tool(tool_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tool not found")


@router.post("/{tool_id}/test", response_model=ToolTestResult)
async def test_tool(tool_id: str, payload: ToolTestRequest) -> ToolTestResult:
    try:
        return await tool_store.test_tool(tool_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="Tool not found") from None
