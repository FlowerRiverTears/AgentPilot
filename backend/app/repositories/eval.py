from __future__ import annotations

from time import perf_counter

from sqlalchemy import delete, func, select

from app.agents.runtime import get_agent_runtime
from app.db.session import AsyncSessionLocal
from app.models.eval import EvalDataset, EvalResult
from app.repositories.base import maybe_uuid, to_uuid
from app.repositories.memory import get_store
from app.schemas.eval import (
    EvalDatasetCreate,
    EvalDatasetRead,
    EvalResultRead,
    EvalResultSummary,
)


class EvalStore:
    """评测数据集与评测结果存储类。"""

    async def create_dataset(self, payload: EvalDatasetCreate) -> EvalDatasetRead:
        """创建评测数据集。"""
        async with AsyncSessionLocal() as session:
            dataset = EvalDataset(
                name=payload.name,
                description=payload.description,
                agent_id=to_uuid(payload.agent_id),
                cases=[case.model_dump() for case in payload.cases],
            )
            session.add(dataset)
            await session.commit()
            await session.refresh(dataset)
            return self._dataset_to_read(dataset)

    async def list_datasets(self) -> list[EvalDatasetRead]:
        """列出所有评测数据集。"""
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(EvalDataset).order_by(EvalDataset.created_at.desc())
                )
            ).scalars().all()
            return [self._dataset_to_read(row) for row in rows]

    async def get_dataset(self, dataset_id: str) -> EvalDatasetRead | None:
        """获取评测数据集详情。"""
        dataset_uuid = maybe_uuid(dataset_id)
        if not dataset_uuid:
            return None
        async with AsyncSessionLocal() as session:
            dataset = await session.get(EvalDataset, dataset_uuid)
            if not dataset:
                return None
            return self._dataset_to_read(dataset)

    async def delete_dataset(self, dataset_id: str) -> bool:
        """删除评测数据集，同时清理关联的评测结果。"""
        dataset_uuid = maybe_uuid(dataset_id)
        if not dataset_uuid:
            return False
        async with AsyncSessionLocal() as session:
            dataset = await session.get(EvalDataset, dataset_uuid)
            if not dataset:
                return False
            # 先删除关联的评测结果
            await session.execute(
                delete(EvalResult).where(EvalResult.dataset_id == dataset_uuid)
            )
            await session.delete(dataset)
            await session.commit()
            return True

    async def list_results(
        self, dataset_id: str | None = None, limit: int = 50
    ) -> list[EvalResultSummary]:
        """列出评测结果，可选按数据集过滤。"""
        async with AsyncSessionLocal() as session:
            stmt = select(EvalResult).order_by(EvalResult.created_at.desc()).limit(limit)
            if dataset_id:
                dataset_uuid = maybe_uuid(dataset_id)
                if dataset_uuid:
                    stmt = stmt.where(EvalResult.dataset_id == dataset_uuid)
            rows = (await session.execute(stmt)).scalars().all()
            return [self._result_to_summary(row) for row in rows]

    async def get_result(self, result_id: str) -> EvalResultRead | None:
        """获取评测结果详情。"""
        result_uuid = maybe_uuid(result_id)
        if not result_uuid:
            return None
        async with AsyncSessionLocal() as session:
            result = await session.get(EvalResult, result_uuid)
            if not result:
                return None
            return self._result_to_read(result)

    async def run_eval(self, dataset_id: str) -> EvalResultRead | None:
        """执行评测：批量运行智能体并计算指标。

        步骤：
        1. 获取数据集和关联的 agent
        2. 创建 EvalResult 记录（status=running）
        3. 遍历每个 case，调用 agent_runtime.run 获取回答
        4. 检查回答中是否包含所有 expected_keywords（不区分大小写）
        5. 记录每条结果到 details
        6. 计算准确率和平均耗时
        7. 更新 EvalResult 记录（status=completed）
        8. 返回 EvalResultRead
        """
        dataset_uuid = maybe_uuid(dataset_id)
        if not dataset_uuid:
            return None

        async with AsyncSessionLocal() as session:
            dataset = await session.get(EvalDataset, dataset_uuid)
            if not dataset:
                return None
            cases = list(dataset.cases or [])
            agent_id_str = str(dataset.agent_id)

        # 获取关联的 agent
        agent = await get_store().get_agent(agent_id_str)
        if not agent:
            # agent 不存在，直接创建一个 failed 结果
            async with AsyncSessionLocal() as session:
                result = EvalResult(
                    dataset_id=dataset_uuid,
                    agent_id=dataset.agent_id,
                    status="failed",
                    total_cases=len(cases),
                    passed_cases=0,
                    accuracy=0.0,
                    avg_duration_ms=0,
                    details=[
                        {
                            "question": case.get("question", ""),
                            "answer": "",
                            "expected_keywords": case.get("expected_keywords", []),
                            "matched_keywords": [],
                            "passed": False,
                            "duration_ms": 0,
                            "error": "关联的智能体不存在或已被删除",
                        }
                        for case in cases
                    ],
                )
                session.add(result)
                await session.commit()
                await session.refresh(result)
                return self._result_to_read(result)

        # 创建 running 状态的评测结果
        async with AsyncSessionLocal() as session:
            result = EvalResult(
                dataset_id=dataset_uuid,
                agent_id=dataset.agent_id,
                status="running",
                total_cases=len(cases),
                passed_cases=0,
                accuracy=0.0,
                avg_duration_ms=0,
                details=[],
            )
            session.add(result)
            await session.commit()
            await session.refresh(result)
            result_id = result.id

        # 逐条执行评测用例
        details: list[dict] = []
        passed_cases = 0
        total_duration_ms = 0
        has_failure = False

        for case in cases:
            question = case.get("question", "")
            expected_keywords = list(case.get("expected_keywords", []))
            started_at = perf_counter()
            answer = ""
            error_message = ""
            try:
                run_data = await get_agent_runtime().run(agent, question)
                answer = run_data.get("answer", "")
            except Exception as exc:
                error_message = str(exc)
                has_failure = True

            duration_ms = int((perf_counter() - started_at) * 1000)
            total_duration_ms += duration_ms

            # 关键词匹配（不区分大小写）
            answer_lower = answer.lower()
            matched_keywords = [
                keyword
                for keyword in expected_keywords
                if keyword and keyword.lower() in answer_lower
            ]
            passed = (
                len(matched_keywords) == len(expected_keywords)
                and not error_message
            )
            if passed:
                passed_cases += 1

            details.append(
                {
                    "question": question,
                    "answer": answer,
                    "expected_keywords": expected_keywords,
                    "matched_keywords": matched_keywords,
                    "passed": passed,
                    "duration_ms": duration_ms,
                    "error": error_message,
                }
            )

        total_cases = len(cases)
        accuracy = (passed_cases / total_cases) if total_cases else 0.0
        avg_duration_ms = int(total_duration_ms / total_cases) if total_cases else 0
        final_status = "failed" if has_failure and passed_cases == 0 else "completed"

        # 更新评测结果
        async with AsyncSessionLocal() as session:
            result = await session.get(EvalResult, result_id)
            if result is None:
                return None
            result.status = final_status
            result.passed_cases = passed_cases
            result.accuracy = round(accuracy, 4)
            result.avg_duration_ms = avg_duration_ms
            result.details = details
            await session.commit()
            await session.refresh(result)
            return self._result_to_read(result)

    def _dataset_to_read(self, dataset: EvalDataset) -> EvalDatasetRead:
        return EvalDatasetRead(
            id=str(dataset.id),
            name=dataset.name,
            description=dataset.description,
            agent_id=str(dataset.agent_id),
            cases=list(dataset.cases or []),
            created_at=dataset.created_at.isoformat() if dataset.created_at else "",
        )

    def _result_to_read(self, result: EvalResult) -> EvalResultRead:
        return EvalResultRead(
            id=str(result.id),
            dataset_id=str(result.dataset_id),
            agent_id=str(result.agent_id),
            status=result.status,
            total_cases=result.total_cases,
            passed_cases=result.passed_cases,
            accuracy=result.accuracy,
            avg_duration_ms=result.avg_duration_ms,
            details=list(result.details or []),
            created_at=result.created_at.isoformat() if result.created_at else "",
        )

    def _result_to_summary(self, result: EvalResult) -> EvalResultSummary:
        return EvalResultSummary(
            id=str(result.id),
            dataset_id=str(result.dataset_id),
            agent_id=str(result.agent_id),
            status=result.status,
            total_cases=result.total_cases,
            passed_cases=result.passed_cases,
            accuracy=result.accuracy,
            avg_duration_ms=result.avg_duration_ms,
            created_at=result.created_at.isoformat() if result.created_at else "",
        )



eval_store = EvalStore()
