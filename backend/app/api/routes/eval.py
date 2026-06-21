from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_admin, get_current_user
from app.repositories.eval import eval_store
from app.schemas.eval import (
    EvalDatasetCreate,
    EvalDatasetRead,
    EvalResultRead,
    EvalResultSummary,
)

router = APIRouter()


@router.get("/datasets", response_model=list[EvalDatasetRead])
async def list_datasets(_user=Depends(get_current_user)) -> list[EvalDatasetRead]:
    """列出所有评测数据集。"""
    return await eval_store.list_datasets()


@router.post("/datasets", response_model=EvalDatasetRead, status_code=201)
async def create_dataset(
    payload: EvalDatasetCreate, _user=Depends(get_current_admin)
) -> EvalDatasetRead:
    """创建评测数据集。"""
    return await eval_store.create_dataset(payload)


@router.get("/datasets/{dataset_id}", response_model=EvalDatasetRead)
async def get_dataset(
    dataset_id: str, _user=Depends(get_current_user)
) -> EvalDatasetRead:
    """获取评测数据集详情。"""
    dataset = await eval_store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="评测数据集不存在")
    return dataset


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: str, _user=Depends(get_current_admin)
) -> None:
    """删除评测数据集。"""
    deleted = await eval_store.delete_dataset(dataset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="评测数据集不存在")


@router.post("/datasets/{dataset_id}/run", response_model=EvalResultRead)
async def run_eval(
    dataset_id: str, _user=Depends(get_current_admin)
) -> EvalResultRead:
    """触发评测，批量运行智能体并计算指标。"""
    result = await eval_store.run_eval(dataset_id)
    if not result:
        raise HTTPException(status_code=404, detail="评测数据集不存在")
    return result


@router.get("/results", response_model=list[EvalResultSummary])
async def list_results(
    dataset_id: str | None = Query(default=None, description="按数据集 ID 过滤"),
    limit: int = Query(default=50, ge=1, le=200),
    _user=Depends(get_current_user),
) -> list[EvalResultSummary]:
    """列出评测结果，可选按数据集过滤。"""
    return await eval_store.list_results(dataset_id=dataset_id, limit=limit)


@router.get("/results/{result_id}", response_model=EvalResultRead)
async def get_result(
    result_id: str, _user=Depends(get_current_user)
) -> EvalResultRead:
    """获取评测结果详情。"""
    result = await eval_store.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="评测结果不存在")
    return result
