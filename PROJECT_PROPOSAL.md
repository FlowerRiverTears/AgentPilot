> 最后更新：2026-06-20 | 本文档定位：项目愿景与远期规划，与 PROJECT_SPEC.md（当前实现状态）互补

# AgentPilot 项目内容方案

## 1. 项目定位

AgentPilot 是一个面向开发者和团队的开源 Agent 工作台：用户可以在 Vue 前端中创建 Agent、配置工具、接入知识库、编排多步骤任务，并在后台看到 Agent 的执行轨迹、工具调用、检索证据、成本和评估结果。

目标不是做一个简单聊天机器人，而是做一个“可运行、可观测、可扩展、可部署”的生产级 Agent 平台。这个方向适合 GitHub 开源，也适合面试展示，因为它覆盖后端架构、前端工程、数据库设计、LLM 工程、RAG、任务队列、权限、可观测性和部署。

### 核心需求

- LLM：多模型接入、流式输出、重试、fallback、token 统计
- RAG：文档导入、解析、多模态提取、切块、检索、引用回传、重排
- 切面：鉴权、日志、审计、限流、追踪、成本统计等横切能力
- 向量：多模态 embedding 生成（文本 + 图片）、向量存储、跨模态相似度检索，默认落在 PostgreSQL + pgvector

## 2. 项目亮点

1. 可视化 Agent 编排
   - 支持创建单 Agent、多 Agent 协作、审批节点、条件分支、循环重试。
   - 工作流节点包括 LLM、工具调用、RAG 检索、代码执行、HTTP 请求、人工确认、结果评分。

2. 生产级 RAG 知识库
   - 支持 PDF、Markdown、网页、代码仓库、Notion/飞书文档等数据源。
   - 支持多模态提取：文本、图片、表格独立解析。
   - 支持多模态 Embedding：文本和图片在同一向量空间中向量化，支持跨模态检索。
   - 支持分块、向量化、关键词检索、混合检索、跨模态检索、重排、引用溯源。
   - 支持每次回答展示证据片段（含图片引用），避免"看起来很强但无法验证"。

3. 多 LLM Provider 网关
   - 支持 OpenAI-compatible API、本地 Ollama、Anthropic、Gemini、DeepSeek、通义千问、智谱等模型适配。
   - 统一模型调用、流式输出、token 统计、成本估算、限流、重试、fallback。

4. Tool / MCP 工具系统
   - 内置 Web Search、HTTP Client、SQL 查询、文件解析、代码执行沙箱、GitHub Issue 分析等工具。
   - 预留 MCP Server 接入能力，让外部工具以标准协议接入 Agent。

5. Agent 记忆与长期任务
   - 短期记忆：当前会话上下文、工具调用历史。
   - 长期记忆：用户偏好、项目资料、历史任务摘要。
   - 支持后台长任务、断点恢复、失败重试。

6. 可观测性和评测
   - 每个任务有 trace：模型输入输出、工具参数、RAG 命中文档、耗时、token、错误。
   - 内置评测集：准确性、引用覆盖率、幻觉率、工具成功率、端到端耗时。
   - 支持对比不同模型、prompt、chunk 策略和 reranker。

7. 后续自我发展
   - 基于历史运行轨迹自动生成复盘报告。
   - 给出 prompt、检索和模型配置优化建议。
   - 将高成功率流程沉淀为模板和最佳实践。
   - 以受控方式演进，不允许未经确认的自动修改。

## 3. 推荐技术栈

### 后端

- Python 3.11+
- FastAPI：REST API、WebSocket 流式输出、OpenAPI 文档。
- Pydantic：请求响应模型和配置校验。
- SQLAlchemy 2.x + Alembic：数据库 ORM 和迁移。
- LangGraph 风格的状态图编排：用于复杂 Agent 流程、条件边、持久化执行。
- Celery / Dramatiq / Arq：后台任务队列，处理文档入库、向量化、长任务运行。
- Redis：缓存、限流、任务状态、WebSocket pub/sub。
- MinIO / S3：原始文件、附件、导出报告存储。

### 前端

- Vue 3 + TypeScript + Vite。
- Pinia：状态管理。
- Vue Router：页面路由。
- Element Plus 或 Naive UI：后台系统组件库。推荐 Naive UI，视觉更现代，适合开源项目。
- Vue Flow：可视化 Agent 工作流画布。
- Monaco Editor：Prompt、JSON Schema、工具参数编辑。
- ECharts：token、成本、耗时、命中率等图表。

### 数据库推荐

默认推荐：PostgreSQL + pgvector。

原因：
- PostgreSQL 同时适合业务数据、JSONB 配置、权限、任务记录和审计日志。
- pgvector 可以直接存储 embedding，减少早期部署复杂度。
- 对开源项目更友好：一个数据库就能跑通核心能力。

扩展推荐：
- Redis：缓存和队列状态。
- Qdrant：当向量数据量较大、需要更强向量检索性能和独立扩展时作为可选插件。
- ClickHouse：后期做大规模 trace、成本统计、事件分析时再接入。

### LLM 推荐

采用“模型网关”设计，不把项目绑定在某一家模型上。

第一阶段建议支持：
- OpenAI-compatible API：覆盖 OpenAI、DeepSeek、Qwen、Moonshot 等兼容接口。
- Ollama：本地模型，方便开源用户低成本运行。
- Embedding Provider：OpenAI-compatible embedding、本地 bge-m3、Qwen embedding、CLIP 多模态 embedding。

第二阶段再支持：
- Anthropic Claude。
- Google Gemini。
- Azure OpenAI。
- 自定义 HTTP Provider。

### RAG 说明

本项目中的 RAG 不是只做"向量搜索 + 拼 prompt"，而是做成可配置流水线，并支持多模态：

1. Data Loader：加载 PDF、网页、Markdown、代码仓库。
2. Parser：抽取正文、标题、表格、代码块、元数据、图片。
3. Chunker：按语义标题、token 长度、代码结构切块；图片作为独立块。
4. Multimodal Embedder：文本和图片统一向量化（CLIP 等模型），写入同一向量空间。
5. Indexer：生成多模态 embedding，写入 pgvector / Qdrant。
6. Retriever：向量检索、BM25、metadata filter、hybrid search、跨模态检索。
7. Reranker：对候选片段重排。
8. Citation Builder：把引用片段绑定到回答（含图片引用）。
9. Evaluator：评估召回率、引用质量、答案一致性。

## 4. 核心功能模块

### 4.1 Dashboard

- 最近任务、成功率、平均耗时、token 消耗、模型成本。
- Agent 运行状态：运行中、等待人工确认、失败、完成。
- 知识库文档入库进度。

### 4.2 Agent Studio

- 创建 Agent：名称、系统提示词、模型、工具权限、知识库权限。
- 可视化工作流：拖拽节点、连线、配置条件。
- Prompt 版本管理：每次修改保留版本，可回滚和对比。
- Debug Run：单步运行，查看每个节点输入输出。

### 4.3 Chat / Task Workspace

- 类似 ChatGPT 的对话界面，但右侧显示执行轨迹。
- 支持上传文件、选择知识库、选择 Agent。
- 支持中断、继续、重试某一步。
- 支持导出任务报告。

### 4.4 Knowledge Base

- 创建知识库。
- 上传文件或输入 URL。
- 文档解析、多模态提取（文本/图片/表格）、切块、多模态 embedding、索引状态展示。
- 支持文档级、chunk 级检索测试。
- 支持跨模态检索：文本查图片、图片查文本。
- 支持引用预览和命中分析（含图片引用）。

### 4.5 Tool Center

- 内置工具列表。
- 工具权限控制。
- 工具 Schema 编辑。
- 工具调用日志。
- 自定义工具：HTTP API、Python Function、MCP Tool。

### 4.6 Evaluation Lab

- 创建评测集：问题、标准答案、期望引用。
- 批量跑不同 Agent / 模型 / RAG 参数。
- 生成对比报告：准确率、引用命中率、平均成本、平均耗时。

### 4.7 Admin / Team

- 用户、团队、角色权限。
- API Key 管理。
- 模型 Provider 配置。
- 审计日志。

## 5. 系统架构

```text
Vue 3 Frontend
  |
  | REST / WebSocket
  v
FastAPI Backend
  |
  |-- Auth / RBAC
  |-- Agent Runtime
  |-- LLM Gateway
  |-- RAG Pipeline
  |-- Tool Runtime
  |-- Evaluation Engine
  |
  |-- PostgreSQL + pgvector
  |-- Redis
  |-- MinIO / S3
  |-- Optional Qdrant
  |
  v
Worker Pool
  |-- Document Parsing
  |-- Embedding Jobs
  |-- Long-running Agent Tasks
  |-- Evaluation Batch Jobs
```

## 6. 建议目录结构

```text
pyAgent/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      agents/
      rag/
      llm/
      tools/
      evals/
      workers/
      observability/
    migrations/
    tests/
    pyproject.toml
    Dockerfile
  frontend/
    src/
      api/
      assets/
      components/
      layouts/
      pages/
      router/
      stores/
      types/
      utils/
    package.json
    vite.config.ts
    Dockerfile
  deploy/
    docker-compose.yml
    nginx.conf
    init.sql
  docs/
    architecture.md
    api.md
    rag-design.md
    agent-runtime.md
    development.md
  examples/
    customer-support-agent/
    code-review-agent/
    research-agent/
  README.md
  LICENSE
```

## 7. 数据模型草案

核心表（✅ 已实现 / ❌ 未实现 / ⚠️ 部分实现）：

- users ✅
- organizations ❌
- projects ❌
- model_configs ✅
- agents ✅
- agent_versions ❌
- workflows ❌
- workflow_nodes ❌
- workflow_edges ❌
- conversations ✅（摘要内嵌在 conversations 表中）
- messages ❌（消息内嵌在 conversations.messages JSON 字段中）
- runs ✅（表名 agent_runs）
- run_steps ✅
- tool_calls ✅
- knowledge_bases ✅
- documents ✅
- document_chunks ✅（含多模态向量）
- eval_datasets ❌
- eval_cases ❌
- eval_runs ❌
- audit_logs ❌
- feedbacks ✅（v0.2.0 新增）
- tools ✅

## 8. API 设计示例

```text
POST   /api/auth/login
GET    /api/me

GET    /api/agents
POST   /api/agents
GET    /api/agents/{agent_id}
PUT    /api/agents/{agent_id}
POST   /api/agents/{agent_id}/publish

POST   /api/runs
GET    /api/runs/{run_id}
GET    /api/runs/{run_id}/steps
POST   /api/runs/{run_id}/cancel
WS     /api/runs/{run_id}/stream

GET    /api/knowledge-bases
POST   /api/knowledge-bases
POST   /api/knowledge-bases/{kb_id}/documents
POST   /api/knowledge-bases/{kb_id}/retrieve-test

GET    /api/tools
POST   /api/tools/custom-http
GET    /api/tool-calls

POST   /api/evals/run
GET    /api/evals/{eval_run_id}/report
```

## 9. GitHub 开源卖点

README 首页需要突出这些点：

- 一键 docker compose 启动。
- 内置 3 个可直接运行的 Agent 示例：
  - Research Agent：联网搜索、总结、引用来源。
  - Code Review Agent：分析 GitHub PR，输出风险和建议。
  - Customer Support Agent：基于企业文档回答问题并给出引用。
- 有漂亮的工作流画布截图。
- 有完整架构图和数据库 ER 图。
- 有可复现评测报告。
- 有插件开发文档。
- 有 Roadmap 和 Good First Issue。

## 10. 面试加分点

> 注：本节内容适合面试准备参考，不属于项目规格。

这个项目能在面试中讲清楚以下能力：

- 如何设计一个可扩展的 Agent Runtime。
- 如何把非确定性的 LLM 调用变成可观测、可重试、可评估的系统。
- RAG 的工程细节：切块、多模态提取、多模态 embedding、跨模态检索、重排、引用、评估。
- PostgreSQL + pgvector 的数据建模和索引设计。
- WebSocket 流式输出和长任务状态同步。
- 工具调用安全：权限、参数校验、超时、沙箱。
- 多模型网关：重试、fallback、限流、成本统计。
- 前后端分离大型项目结构。
- Docker Compose 本地部署和生产部署思路。

## 11. MVP 开发顺序

### 阶段 1：基础可运行

- FastAPI 项目骨架。
- Vue 3 项目骨架。
- Docker Compose：backend、frontend、postgres、redis、minio。
- 用户登录和基础页面布局。
- 模型 Provider 配置。
- 简单 Chat Agent，支持流式输出。

### 阶段 2：知识库 RAG

- 文件上传。
- PDF / Markdown 解析。
- 文档切块。
- 多模态 embedding 写入 pgvector（文本 + 图片统一向量空间）。
- 检索测试页面。
- Chat Agent 支持引用知识库回答。

### 阶段 3：Agent Studio

- Agent 配置页面。
- 工具权限配置。
- Vue Flow 工作流画布。
- 后端 Agent Runtime 执行节点图。
- run_steps 执行轨迹。

### 阶段 4：工具系统

- HTTP 工具。
- SQL 查询工具。
- Python 沙箱工具。
- Web Search 工具。
- MCP 工具接入预留。

### 阶段 5：评测和观测

- 评测集管理。
- 批量运行评测。
- trace 面板。
- token / 成本 / 耗时统计。
- 模型和 prompt 对比报告。

### 阶段 6：开源包装

- README、截图、演示数据。
- 示例 Agent。
- 文档站。
- GitHub Actions。
- Issue 模板和贡献指南。

### 阶段 7：自我发展能力

- 运行复盘报告
- 优化建议面板
- 配置对比实验
- 模板沉淀与版本演化

## 12. 项目名决策（已确定：AgentPilot）

可选名称：

1. AgentPilot：清晰，适合 Agent 工作台。
2. AgentForge：强调构建和编排。
3. TaskWeaverX：强调任务编织，但名字略复杂。
4. OpenAgentOps：强调生产运维和观测。
5. AgentHub：易懂，但可能重名较多。

推荐使用 AgentPilot。

## 13. 当前建议结论

建议做：AgentPilot - Open-source AgentOps and RAG Workflow Platform。

技术主线：
- Python + FastAPI 做后端。
- Vue 3 + TypeScript + Vite 做前端。
- PostgreSQL + pgvector 做主数据库和向量库。
- Redis 做缓存和任务状态。
- MinIO 做文件存储。
- LLM 采用 OpenAI-compatible + Ollama 起步。
- Agent Runtime 采用 LangGraph 风格状态图。
- RAG 做成可视化、可评测、可追踪的核心亮点。

这个方向足够大，但可以分阶段落地。第一版只要做到“登录、模型配置、知识库、Chat Agent、执行轨迹、Docker 一键启动”，就已经比普通简历项目强很多。

## 14. 参考资料

- FastAPI 官方文档：https://fastapi.tiangolo.com/
- Vue 官方文档：https://vuejs.org/guide/
- PostgreSQL JSONB 官方文档：https://www.postgresql.org/docs/current/datatype-json.html
- pgvector 官方仓库：https://github.com/pgvector/pgvector
- Qdrant 官方文档：https://qdrant.tech/documentation/
- LangGraph 官方说明：https://www.langchain.com/langgraph
