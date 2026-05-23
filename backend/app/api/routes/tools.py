from fastapi import APIRouter
from pydantic import BaseModel

from app.tools import tool_registry

router = APIRouter()


class ToolRead(BaseModel):
    id: str
    name: str
    description: str


@router.get("", response_model=list[ToolRead])
async def list_tools() -> list[ToolRead]:
    return [ToolRead(**tool.__dict__) for tool in tool_registry.list_tools()]
