# AgentPilot

AgentPilot 是一个开源 AI Agent 工作台，用于创建智能体、接入知识库、调用工具、运行 RAG 问答，并记录每次执行轨迹。

## 核心能力

- LLM：OpenAI-compatible API / Ollama，多模型网关，预留流式输出、重试、fallback、成本统计。
- RAG：文档上传、文本切块、检索、引用来源。
- 切面：通过中间件统一处理 trace_id、耗时、审计信息，后续扩展鉴权、限流、日志。
- 向量：当前 MVP 使用本地 deterministic embedding stub，数据库模型已预留 pgvector 字段。

## 技术栈

- 后端：Python、FastAPI、Pydantic、SQLAlchemy
- 前端：Vue 3、TypeScript、Vite、Pinia、Naive UI
- 数据层：PostgreSQL + pgvector、Redis、MinIO
- 部署：Docker Compose

## Docker 部署

Redis、PostgreSQL、MinIO 都已经配置在 Docker Compose 中，不需要本机单独安装。容器命名统一使用 `agentpilot-服务名`：

- `agentpilot-redis`
- `agentpilot-postgres`
- `agentpilot-minio`
- `agentpilot-backend`
- `agentpilot-frontend`

```bash
cd deploy
docker compose up --build
```

启动后访问：

- 前端：http://localhost:5173
- 后端接口文档：http://localhost:8000/docs
- PostgreSQL：localhost:15432
- Redis：localhost:16379
- MinIO 控制台：http://localhost:19001

MinIO 默认账号：

```text
agentpilot
agentpilot123
```

## 本地开发

### 后端

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -e .
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 当前已实现

- FastAPI 应用入口
- Vue 3 前端入口
- Agent 创建和列表
- 智能体运行页面：选择智能体、输入任务、执行并展示回答
- 知识库创建
- 文档上传、切块、检索测试接口
- 检索结果展示：来源、命中文档片段、相似度分数
- Agent Run 接口
- Agent Run 执行过程：接收任务、知识库检索、大模型生成
- LLM 网关和开发模式 fallback
- RAG pipeline
- vector embedding stub
- trace / audit / elapsed-ms 切面中间件
- PostgreSQL + pgvector 数据模型草案
- Docker Compose：backend、frontend、postgres、redis、minio

## 当前目录

```text
backend/   Python FastAPI 后端
frontend/  Vue 3 前端
deploy/    Docker Compose 和数据库初始化
docs/      开发文档
```

## 下一步

1. 接入真实数据库持久化。
2. 接入真实 embedding provider。
3. 完善文件上传页面。
4. 增加用户登录和权限。
5. 增加 Agent Studio 工作流画布。
6. 增加受控的自我发展能力。

## 第一版验收

第一版需要能演示：

```text
创建知识库 -> 上传文档 -> 检索测试 -> 展示检索结果 -> 创建 Agent -> 绑定知识库 -> 执行任务 -> 展示回答和引用
```
