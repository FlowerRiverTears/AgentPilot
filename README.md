# AgentPilot

AgentPilot 是一个 AI Agent 工作台，用于在后台创建智能体、接入模型、绑定知识库和应用工具，并在独立前台提供用户体验。

## 核心能力

- 前后台分离：后台制造和管理智能体，前台只面向用户对话体验。
- 模型配置：支持 OpenAI-compatible API / Ollama，多模型配置、默认模型、连通性测试。
- 智能体：创建智能体，配置系统提示词，绑定模型、知识库和应用工具。
- 知识库：创建知识库、上传 PDF / Markdown / 文本，多模态提取（文本/图片/表格）、切块、多模态 Embedding、跨模态检索、引用来源展示。
- 应用工具：支持工具列表和智能体绑定，运行时按用户问题调用工具，适合订单、时间、库存等实时业务数据。
- 运行记录：展示接收任务、知识库检索、应用工具调用、大模型生成等执行过程。
- 前台体验：独立 `/portal` 页面，用户选择后台创建出的智能体并对话，刷新后保留会话上下文。
- 回答展示：支持 `<think>` 思考过程折叠、代码块灰色展示、清理常见 Markdown 装饰符。
- 主题切换：支持深色 / 亮色主题，并保存浏览器偏好。

## 技术栈

- 后端：Python、FastAPI、Pydantic、SQLAlchemy
- 前端：Vue 3、TypeScript、Vite、Pinia、Naive UI
- 数据层：PostgreSQL + pgvector、Redis、MinIO
- 部署：Docker Compose

## 文档索引

- [项目文档（整合版）](docs/index.md) — 项目概述、核心功能、技术架构、数据库设计、API 接口、部署指南、使用指南、开发指南、工具系统、运行时、路线图、FAQ
- [开发说明](docs/development.md)
- [使用教程](docs/user-guide.md)
- [系统架构](docs/architecture.md)
- [API 说明](docs/api.md)
- [数据库设计](docs/database.md)
- [工具系统设计](docs/tool-system.md)
- [智能体运行时](docs/agent-runtime.md)
- [第二版路线](docs/roadmap-v2.md)

## Docker 部署

Redis、PostgreSQL、MinIO、后端和前端都已经配置在 Docker Compose 中。

```bash
cd deploy
docker compose up --build
```

容器：

- `agentpilot-backend`
- `agentpilot-frontend`
- `agentpilot-postgres`
- `agentpilot-redis`
- `agentpilot-minio`

启动后访问：

- 前台体验：http://localhost:5173/portal
- 后台工作台：http://localhost:5173
- 使用教程：http://localhost:5173/guide
- 后端接口文档：http://localhost:8000/docs
- PostgreSQL：localhost:15432
- Redis：localhost:16379
- MinIO API：http://localhost:19000
- MinIO 控制台：http://localhost:19001

MinIO 默认账号：

```text
agentpilot
agentpilot123
```

## 基本使用流程

1. 进入后台：`http://localhost:5173`
2. 打开“模型配置”，新增或确认一个可用模型。
3. 打开“知识库”，创建知识库并上传稳定文档。
4. 打开“智能体后台”，创建智能体，选择模型、知识库和应用工具。
5. 点击后台右上角“进入前台”，或访问 `http://localhost:5173/portal`。
6. 在前台选择智能体并开始对话。

## 知识库和工具怎么分工

知识库适合放稳定或半稳定资料：

- 产品手册
- FAQ
- 售后政策
- 内部制度
- 培训资料

应用工具适合连接实时业务系统：

- 订单查询
- 物流查询
- 库存查询
- 用户资料
- 工单创建
- 当前时间

回答策略：

- 通用问题：大模型直接回答。
- 文档问题：检索知识库后回答，并展示引用。
- 实时业务问题：调用应用工具后回答。
- 没有可靠依据：明确说明无法确认。

## 当前内置工具

- 当前时间：问题涉及“今天、现在、时间、日期”等时调用。
- 订单查询示例：问题涉及“订单、物流、发货、快递”等时调用。

后续可以把示例工具替换为真实 HTTP API、数据库查询或企业系统接口。

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

## 当前目录

```text
backend/   Python FastAPI 后端
frontend/  Vue 3 前端
deploy/    Docker Compose 和数据库初始化
docs/      开发文档
```

## 当前已实现

- Docker Compose 一键启动
- FastAPI 后端
- Vue 3 前端
- PostgreSQL 持久化智能体、知识库、模型配置、运行记录
- 多模型配置和连通性测试
- 知识库上传、PDF 解析、多模态提取、切块、多模态检索测试
- 检索结果过滤乱码、重复片段和低相关上下文
- 智能体创建、列表、模型绑定、知识库绑定、工具绑定
- 智能体编辑、复制、软删除、发布和下线
- 前台只展示已发布智能体
- 前台独立体验页
- 前台会话刷新后保留，继续作为多轮上下文
- 后台进入前台、前台进入后台
- 应用工具列表接口和运行时工具调用
- HTTP 工具管理（创建、编辑、删除、测试）
- 智能体绑定数据库持久化工具
- Agent Run 执行轨迹展示
- 运行历史列表和单次运行详情
- 流式输出
- XSS 防护（DOMPurify 消毒 Markdown 渲染结果）
- 404 路由兜底（未匹配路径重定向到首页）
- 深色 / 亮色主题切换
- 使用教程页面

## 下一步

待推进：

1. 工具系统产品化，支持 HTTP / SQL / 鉴权配置。
2. 基础登录和后台权限控制。
3. Agent 版本管理和发布流程。
4. 更完整的工具调用日志和失败重试。
