from __future__ import annotations

from time import perf_counter
from uuid import UUID

from sqlalchemy import select

from app.agents.runtime import get_agent_runtime
from app.db.session import AsyncSessionLocal
from app.models.workflow import Workflow, WorkflowRun
from app.repositories.base import maybe_uuid
from app.repositories.memory import get_store
from app.repositories.tools import tool_store
from app.schemas.tools import ToolTestRequest
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowRead,
    WorkflowRunRead,
    WorkflowUpdate,
)


class WorkflowStore:
    """工作流仓储：管理工作流定义与执行记录。"""

    async def create_workflow(self, payload: WorkflowCreate) -> WorkflowRead:
        async with AsyncSessionLocal() as session:
            workflow = Workflow(
                name=payload.name,
                description=payload.description,
                nodes=[node.model_dump() for node in payload.nodes],
                edges=[edge.model_dump() for edge in payload.edges],
                status="draft",
            )
            session.add(workflow)
            await session.commit()
            await session.refresh(workflow)
            return self._workflow_to_read(workflow)

    async def list_workflows(self) -> list[WorkflowRead]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Workflow).order_by(Workflow.created_at.desc())
            )
            return [self._workflow_to_read(w) for w in result.scalars().all()]

    async def get_workflow(self, workflow_id: str) -> WorkflowRead | None:
        workflow_uuid = maybe_uuid(workflow_id)
        if not workflow_uuid:
            return None
        async with AsyncSessionLocal() as session:
            workflow = await session.get(Workflow, workflow_uuid)
            if not workflow:
                return None
            return self._workflow_to_read(workflow)

    async def update_workflow(
        self, workflow_id: str, payload: WorkflowUpdate
    ) -> WorkflowRead | None:
        workflow_uuid = maybe_uuid(workflow_id)
        if not workflow_uuid:
            return None
        async with AsyncSessionLocal() as session:
            workflow = await session.get(Workflow, workflow_uuid)
            if not workflow:
                return None
            if payload.name is not None:
                workflow.name = payload.name
            if payload.description is not None:
                workflow.description = payload.description
            if payload.nodes is not None:
                workflow.nodes = [node.model_dump() for node in payload.nodes]
            if payload.edges is not None:
                workflow.edges = [edge.model_dump() for edge in payload.edges]
            if payload.status is not None:
                workflow.status = payload.status
            await session.commit()
            await session.refresh(workflow)
            return self._workflow_to_read(workflow)

    async def delete_workflow(self, workflow_id: str) -> bool:
        workflow_uuid = maybe_uuid(workflow_id)
        if not workflow_uuid:
            return False
        async with AsyncSessionLocal() as session:
            workflow = await session.get(Workflow, workflow_uuid)
            if not workflow:
                return False
            await session.delete(workflow)
            await session.commit()
            return True

    async def publish_workflow(self, workflow_id: str) -> WorkflowRead | None:
        """发布工作流，将状态置为 published。"""
        workflow_uuid = maybe_uuid(workflow_id)
        if not workflow_uuid:
            return None
        async with AsyncSessionLocal() as session:
            workflow = await session.get(Workflow, workflow_uuid)
            if not workflow:
                return None
            workflow.status = "published"
            await session.commit()
            await session.refresh(workflow)
            return self._workflow_to_read(workflow)

    async def list_runs(self, limit: int = 50) -> list[WorkflowRunRead]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WorkflowRun)
                .order_by(WorkflowRun.created_at.desc())
                .limit(limit)
            )
            return [self._run_to_read(r) for r in result.scalars().all()]

    async def get_run(self, run_id: str) -> WorkflowRunRead | None:
        run_uuid = maybe_uuid(run_id)
        if not run_uuid:
            return None
        async with AsyncSessionLocal() as session:
            run = await session.get(WorkflowRun, run_uuid)
            if not run:
                return None
            return self._run_to_read(run)

    async def run_workflow(
        self, workflow_id: str, user_input: str
    ) -> WorkflowRunRead | None:
        """执行工作流：从 start 节点开始，按拓扑顺序依次执行节点。

        节点执行规则：
        - start：直接传递用户输入
        - agent：调用指定智能体处理输入
        - tool：调用指定工具获取结果
        - knowledge：检索指定知识库
        - condition：根据关键词匹配决定下一个节点
        - end：输出最终结果
        """
        workflow_uuid = maybe_uuid(workflow_id)
        if not workflow_uuid:
            return None

        # 获取工作流定义
        async with AsyncSessionLocal() as session:
            workflow = await session.get(Workflow, workflow_uuid)
            if not workflow:
                return None
            nodes_def = list(workflow.nodes or [])
            edges_def = list(workflow.edges or [])

        # 创建执行记录（status=running）
        started_at = perf_counter()
        async with AsyncSessionLocal() as session:
            run = WorkflowRun(
                workflow_id=workflow_uuid,
                status="running",
                input=user_input,
                node_results=[],
                duration_ms=0,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.id

        # 执行工作流
        node_results, final_output, error = await self._execute_workflow(
            nodes_def, edges_def, user_input
        )

        total_duration_ms = int((perf_counter() - started_at) * 1000)

        # 更新执行记录
        async with AsyncSessionLocal() as session:
            run = await session.get(WorkflowRun, run_id)
            if run:
                run.status = "failed" if error else "completed"
                run.output = final_output
                run.node_results = node_results
                run.duration_ms = total_duration_ms
                run.error = error
                await session.commit()
                await session.refresh(run)
                return self._run_to_read(run)
        return None

    async def _execute_workflow(
        self,
        nodes_def: list[dict],
        edges_def: list[dict],
        user_input: str,
    ) -> tuple[list[dict], str | None, str | None]:
        """执行工作流节点，返回 (节点结果列表, 最终输出, 错误信息)。"""
        nodes_map: dict[str, dict] = {n["id"]: n for n in nodes_def}
        node_results: list[dict] = []
        max_iterations = 100

        # 找到 start 节点
        start_node = next(
            (n for n in nodes_def if n.get("type") == "start"), None
        )
        if not start_node:
            return node_results, None, "工作流缺少 start 节点"

        current_node = start_node
        node_input = user_input
        final_output: str | None = None
        error: str | None = None

        for _ in range(max_iterations):
            if not current_node:
                break

            node_type = current_node.get("type", "")
            node_config = current_node.get("config", {}) or {}
            node_start = perf_counter()
            node_output = ""
            node_status = "completed"

            try:
                if node_type == "start":
                    # 开始节点：直接传递用户输入
                    node_output = user_input

                elif node_type == "agent":
                    # 智能体节点：调用指定智能体
                    agent_id = node_config.get("agent_id", "")
                    agent = await get_store().get_agent(agent_id)
                    if not agent:
                        raise ValueError(f"未找到智能体: {agent_id}")
                    result = await get_agent_runtime().run(agent, node_input)
                    node_output = result.get("answer", "")

                elif node_type == "tool":
                    # 工具节点：调用指定工具
                    tool_id = node_config.get("tool_id", "")
                    test_result = await tool_store.test_tool(
                        tool_id, ToolTestRequest(input={"query": node_input})
                    )
                    if test_result.ok:
                        node_output = str(test_result.output)
                    else:
                        node_output = str(test_result.error)
                        node_status = "failed"

                elif node_type == "knowledge":
                    # 知识库节点：检索指定知识库
                    kb_id = node_config.get("knowledge_base_id", "")
                    top_k = int(node_config.get("top_k", 3))
                    chunks = await get_store().retrieve_chunks(kb_id, node_input, top_k=top_k)
                    if chunks:
                        node_output = "\n\n".join(chunk.content for chunk in chunks)
                    else:
                        node_output = "未检索到相关内容"

                elif node_type == "condition":
                    # 条件分支节点：根据关键词匹配决定下一个节点
                    rules = node_config.get("rules", [])
                    default_target = node_config.get("default_target", "")
                    next_node_id = default_target
                    for rule in rules:
                        keyword = rule.get("keyword", "")
                        target = rule.get("target_node", "")
                        if keyword and keyword in node_input:
                            next_node_id = target
                            break
                    node_output = node_input  # 条件节点透传输入
                    duration_ms = int((perf_counter() - node_start) * 1000)
                    node_results.append({
                        "node_id": current_node["id"],
                        "node_type": node_type,
                        "status": node_status,
                        "output": node_output,
                        "duration_ms": duration_ms,
                        "next_node": next_node_id,
                    })
                    # 跳转到条件判断决定的目标节点
                    current_node = nodes_map.get(next_node_id)
                    if current_node:
                        node_input = node_output
                    continue

                elif node_type == "end":
                    # 结束节点：输出最终结果
                    node_output = node_input
                    final_output = node_output
                    duration_ms = int((perf_counter() - node_start) * 1000)
                    node_results.append({
                        "node_id": current_node["id"],
                        "node_type": node_type,
                        "status": node_status,
                        "output": node_output,
                        "duration_ms": duration_ms,
                    })
                    break

                else:
                    raise ValueError(f"未知节点类型: {node_type}")

            except Exception as exc:
                node_status = "failed"
                node_output = f"节点执行失败: {exc}"
                error = str(exc)

            duration_ms = int((perf_counter() - node_start) * 1000)
            node_results.append({
                "node_id": current_node["id"],
                "node_type": node_type,
                "status": node_status,
                "output": node_output,
                "duration_ms": duration_ms,
            })

            # 节点失败则终止执行
            if node_status == "failed":
                break

            # end 节点已处理，退出循环
            if node_type == "end":
                final_output = node_output
                break

            # 查找下一个节点（按 edges 拓扑顺序）
            next_node_id = None
            for edge in edges_def:
                if edge.get("source") == current_node["id"]:
                    next_node_id = edge.get("target")
                    break

            if not next_node_id:
                # 没有后续节点，以当前输出作为最终结果
                final_output = node_output
                break

            current_node = nodes_map.get(next_node_id)
            if current_node:
                node_input = node_output
        else:
            # 超过最大迭代次数，可能存在循环
            error = "工作流执行超过最大迭代次数，可能存在循环"

        return node_results, final_output, error

    def _workflow_to_read(self, workflow: Workflow) -> WorkflowRead:
        return WorkflowRead(
            id=str(workflow.id),
            name=workflow.name,
            description=workflow.description,
            nodes=list(workflow.nodes or []),
            edges=list(workflow.edges or []),
            status=workflow.status,
            created_at=workflow.created_at.isoformat() if workflow.created_at else "",
        )

    def _run_to_read(self, run: WorkflowRun) -> WorkflowRunRead:
        return WorkflowRunRead(
            id=str(run.id),
            workflow_id=str(run.workflow_id),
            status=run.status,
            input=run.input,
            output=run.output,
            node_results=list(run.node_results or []),
            duration_ms=run.duration_ms,
            error=run.error,
            created_at=run.created_at.isoformat() if run.created_at else "",
        )


workflow_store = WorkflowStore()
