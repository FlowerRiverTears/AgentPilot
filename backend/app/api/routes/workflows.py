from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.repositories.workflow import workflow_store
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowRead,
    WorkflowRunCreate,
    WorkflowRunRead,
    WorkflowUpdate,
)

router = APIRouter()


@router.get("", response_model=list[WorkflowRead])
async def list_workflows(_user=Depends(get_current_user)) -> list[WorkflowRead]:
    """列出所有工作流。"""
    return await workflow_store.list_workflows()


@router.post("", response_model=WorkflowRead, status_code=201)
async def create_workflow(
    payload: WorkflowCreate, _user=Depends(get_current_user)
) -> WorkflowRead:
    """创建工作流。"""
    return await workflow_store.create_workflow(payload)


@router.post("/run", response_model=WorkflowRunRead, status_code=201)
async def run_workflow(
    payload: WorkflowRunCreate, _user=Depends(get_current_user)
) -> WorkflowRunRead:
    """执行工作流。"""
    run = await workflow_store.run_workflow(payload.workflow_id, payload.input)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return run


@router.get("/runs", response_model=list[WorkflowRunRead])
async def list_runs(
    _user=Depends(get_current_user), limit: int = 50
) -> list[WorkflowRunRead]:
    """列出工作流执行记录。"""
    return await workflow_store.list_runs(limit=limit)


@router.get("/runs/{run_id}", response_model=WorkflowRunRead)
async def get_run(run_id: str, _user=Depends(get_current_user)) -> WorkflowRunRead:
    """获取工作流执行记录详情。"""
    run = await workflow_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: str, _user=Depends(get_current_user)
) -> WorkflowRead:
    """获取工作流详情。"""
    workflow = await workflow_store.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    _user=Depends(get_current_user),
) -> WorkflowRead:
    """更新工作流。"""
    workflow = await workflow_store.update_workflow(workflow_id, payload)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: str, _user=Depends(get_current_user)
) -> None:
    """删除工作流。"""
    deleted = await workflow_store.delete_workflow(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")


@router.post("/{workflow_id}/publish", response_model=WorkflowRead)
async def publish_workflow(
    workflow_id: str, _user=Depends(get_current_user)
) -> WorkflowRead:
    """发布工作流。"""
    workflow = await workflow_store.publish_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow
