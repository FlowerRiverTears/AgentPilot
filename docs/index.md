# AgentPilot 项目文档

> 开源 AI Agent 工作台 — 创建、编排、知识库问答、工具调用与评测平台

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 核心功能](#2-核心功能)
- [3. 技术架构](#3-技术架构)
- [4. 数据库设计](#4-数据库设计)
- [5. API 接口](#5-api-接口)
- [6. 部署指南](#6-部署指南)
- [7. 使用指南](#7-使用指南)
- [8. 开发指南](#8-开发指南)
- [9. 工具系统](#9-工具系统)
- [10. 智能体运行时](#10-智能体运行时)
- [11. 开发路线与进度](#11-开发路线与进度)
- [12. 常见问题](#12-常见问题)

---

## 1. 项目概述

### 1.1 项目定义

AgentPilot 是一个面向开发者和团队的开源 AI Agent 工作台。用户可以在图形化界面中创建智能体、配置工具、接入知识库、编排多步骤任务，并在后台看到 Agent 的执行轨迹、工具调用、检索证据和成本信息。

目标不是做一个简单聊天机器人，而是做一个**可运行、可观测、可扩展、可部署**的生产级 Agent 平台。

### 1.2 核心价值

| 价值 | 说明 |
|------|------|
| 自主创建 | 用户可以自己创建智能体，配置提示词、模型、知识库和工具 |
| 知识增强 | 智能体接入知识库后，回答附带引用来源，可验证可追溯 |
| 工具联动 | 智能体调用外部工具获取实时数据，连接真实业务系统 |
| 全程可追踪 | 每次执行都有完整日志、步骤记录和引用回传 |
| 前后台分离 | 后台管理智能体，前台面向用户对话，职责清晰 |

### 1.3 适用场景

- 企业客服问答
- 资料研究与总结
- 代码审查和 PR 分析
- 周报、日报、报告生成
- 内部知识库助手

### 1.4 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+、FastAPI、Pydantic、SQLAlchemy 2.x |
| 前端 | Vue 3、TypeScript、Vite、Pinia、Naive UI |
| 数据层 | PostgreSQL + pgvector、Redis、MinIO |
| 部署 | Docker Compose |
| LLM | OpenAI-compatible API、Ollama |

---

## 2. 核心功能

### 2.1 前后台分离

```
后台工作台（/）                    前台体验（/portal）
┌──────────────────────┐          ┌──────────────────────┐
│ 模型配置             │          │                      │
│ 知识库管理           │  发布    │  选择智能体           │
│ 工具管理             │ ──────> │  对话体验             │
│ 智能体管理           │          │  流式输出             │
│ 运行历史             │          │  会话保留             │
└──────────────────────┘          └──────────────────────┘
```

- 后台用于模型配置、知识库、工具和智能体管理。
- 前台 `/portal` 是独立用户体验页，不显示后台菜单。
- 后台可点击"进入前台"，前台可点击"进入后台"。
- 前台只展示已发布智能体。

### 2.2 模型配置

- 支持多个 OpenAI-compatible 模型配置（OpenAI、DeepSeek、Qwen、MiniMax 等）。
- 支持本地 Ollama 模型。
- 支持默认模型和连通性测试。
- 模型网关保持 OpenAI-compatible，便于替换供应商。

### 2.3 知识库与 RAG

- 创建知识库、上传 PDF / Markdown / 文本文件。
- 文档解析 → 切块 → Embedding → pgvector 向量存储。
- 检索测试：输入问题，返回命中文档片段、来源和相似度分数。
- 检索结果过滤乱码、重复片段和低相关上下文。
- 中文关键词匹配兜底，降低本地 fallback embedding 对中文短语不稳定的影响。
- Agent 运行时自动检索绑定知识库，并返回引用来源。

### 2.4 工具系统

- 内置工具：`current_time`（当前时间）、`order_lookup`（订单查询示例）。
- HTTP 工具管理：创建、编辑、删除和测试。
- 配置 URL、Method、Headers、Query、Body、触发关键词和超时时间。
- 智能体绑定数据库持久化工具，运行时优先调用数据库工具，内置工具作为 fallback。
- 运行时根据用户问题匹配触发关键词，自动调用工具。

### 2.5 智能体管理

- 创建智能体：配置名称、描述、系统提示词、模型、知识库和工具。
- 编辑智能体：支持部分更新，未传字段保持原值。
- 复制智能体：复制出的智能体为草稿状态。
- 软删除智能体。
- 发布 / 下线智能体：前台只展示已发布智能体。

### 2.6 运行历史

- Run 列表页：展示智能体名称、状态、输入、模型、耗时和创建时间。
- Run 详情页：展示输入、回答、引用来源、执行步骤、工具调用明细、模型和状态。
- 工具调用明细：工具名称、成功/失败状态标签、返回内容。
- 耗时展示：每步执行和总耗时。

### 2.7 流式输出

- 前台 `/portal` 使用 SSE（Server-Sent Events）流式输出，回答逐字显示。
- 后端端点：`POST /api/runs/stream`，返回 `text/event-stream`。
- 前端使用 `fetch` + `ReadableStream` 逐块读取。
- 后台 `/chat` 仍使用非流式接口 `POST /api/runs`。

### 2.8 回答展示

- `<think>...</think>` 思考过程折叠显示。
- Markdown 代码块灰色代码框显示。
- 清理标题符号和分隔线。
- Markdown 渲染结果经 DOMPurify 消毒，防止 XSS 攻击。

### 2.9 其他

- 深色 / 亮色主题切换，保存浏览器偏好。
- 使用教程页面（`/guide`）。
- 前台会话刷新后保留，继续作为多轮上下文。
- 404 路由兜底，未匹配路径重定向到首页。

---

## 3. 技术架构

### 3.1 系统架构图

```
用户浏览器
  ├─ 后台工作台：模型、知识库、工具、智能体管理
  └─ 前台体验：选择已创建智能体并对话

Vue 3 前端
  └─ /api 请求

FastAPI 后端
  ├─ 模型配置（llm/gateway.py）
  ├─ 知识库检索（rag/pipeline.py）
  ├─ 应用工具调用（repositories/tools.py + tools/registry.py）
  ├─ 智能体运行时（agents/runtime.py）
  └─ 运行记录（repositories/memory.py）

PostgreSQL + pgvector / Redis / MinIO
```

### 3.2 前端模块

| 模块 | 文件 | 说明 |
|------|------|------|
| 应用入口 | `App.vue` | 后台布局、主题切换、前后台入口 |
| 总览 | `DashboardPage.vue` | 首页总览 |
| 使用教程 | `GuidePage.vue` | 使用教程页面 |
| 智能体管理 | `AgentsPage.vue` | 智能体后台 |
| 知识库 | `KnowledgePage.vue` | 知识库管理和检索测试 |
| 工具管理 | `ToolsPage.vue` | 工具管理 |
| 模型配置 | `ModelSettingsPage.vue` | 模型配置 |
| 运行历史 | `RunsPage.vue` | 运行历史列表和详情 |
| 运行测试 | `ChatPage.vue` | 后台运行测试 |
| 前台体验 | `PortalPage.vue` | 独立前台体验页 |
| 状态管理 | `stores/workspace.ts` | 业务状态和 API 调用 |
| 主题状态 | `stores/ui.ts` | 深色 / 亮色主题状态 |
| 回答格式化 | `utils/answerFormat.ts` | Markdown 渲染 + DOMPurify 消毒 |

### 3.3 后端模块

| 模块 | 文件 | 说明 |
|------|------|------|
| 智能体接口 | `api/routes/agents.py` | 智能体 CRUD、发布、下线、复制 |
| 知识库接口 | `api/routes/knowledge.py` | 知识库和文档管理 |
| 运行接口 | `api/routes/runs.py` | 运行和流式输出 |
| 模型配置接口 | `api/routes/settings.py` | 模型配置 CRUD 和测试 |
| 工具接口 | `api/routes/tools.py` | 工具 CRUD 和测试 |
| Mock 接口 | `api/routes/mock.py` | 模拟数据（订单/库存/天气） |
| 智能体运行时 | `agents/runtime.py` | 智能体运行核心逻辑 |
| 模型网关 | `llm/gateway.py` | OpenAI-compatible 模型网关 |
| 数据访问层 | `repositories/memory.py` | Agent、Run、KnowledgeBase 数据访问 |
| 工具数据层 | `repositories/tools.py` | 数据库持久化工具访问层 |
| 内置工具 | `tools/registry.py` | 内置工具注册和调用（fallback） |
| RAG 流水线 | `rag/pipeline.py` | 切块和检索逻辑 |
| 文档解析 | `rag/document_loader.py` | 文档解析，支持文本和图片提取 |
| Embedding 服务 | `vector/embeddings.py` | 多模态 Embedding 服务 |

### 3.4 数据流

#### 运行时链路

```
1. 后台创建模型配置
2. 后台创建知识库并上传文档
3. 系统解析文档 → 切块 → Embedding → pgvector
4. 后台创建智能体，绑定模型、知识库和工具
5. 前台读取已发布智能体列表
6. 用户发送问题
7. 后端检索知识库 + 调用工具
8. 后端调用大模型生成回答
9. 前端展示回答、引用来源和执行过程
```

前台 `/portal` 使用 SSE 流式输出，回答逐字显示；后台 `/chat` 使用非流式接口，等待完整回答后展示。

#### 管理链路

```
1. 后台创建 HTTP 工具，配置 URL 和触发关键词
2. 创建智能体时绑定工具
3. 运行时根据用户问题匹配触发关键词，自动调用工具
```

### 3.5 部署结构

Docker Compose 包含 5 个服务：

| 服务 | 镜像 | 端口映射 | 说明 |
|------|------|----------|------|
| `agentpilot-frontend` | 自建（Nginx） | 5173:80 | 前端 |
| `agentpilot-backend` | 自建（Python） | 8000:8000 | 后端 |
| `agentpilot-postgres` | pgvector/pgvector:pg16 | 15432:5432 | 数据库 |
| `agentpilot-redis` | redis:7-alpine | 16379:6379 | 缓存 |
| `agentpilot-minio` | minio/minio | 19000:9000, 19001:9001 | 对象存储 |

### 3.6 设计原则

- 前台和后台职责分离。
- 知识库负责稳定资料，工具负责实时业务数据。
- 智能体运行必须可追踪。
- 模型网关保持 OpenAI-compatible，便于替换供应商。
- 先做可运行，再做完整；先做主流程，再补增强功能。

---

## 4. 数据库设计

当前使用 PostgreSQL + pgvector，向量字段支持多模态 Embedding。

### 4.1 已实现的表

#### agents — 智能体表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `name` | VARCHAR | 名称 |
| `description` | TEXT | 描述 |
| `system_prompt` | TEXT | 系统提示词 |
| `model` | VARCHAR | 模型名，可为空 |
| `status` | VARCHAR | 状态（draft / published / archived） |
| `config` | JSONB | 配置（model_config_id、knowledge_base_ids、tool_ids） |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

#### agent_runs — 运行记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `agent_id` | UUID | 智能体 ID（外键） |
| `status` | VARCHAR | 运行状态 |
| `input` | TEXT | 用户输入 |
| `output` | TEXT | 模型输出 |
| `trace_id` | VARCHAR | 追踪 ID |
| `usage` | JSONB | 使用信息（token、耗时、工具结果等） |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

#### run_steps — 运行步骤表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `run_id` | UUID | 运行 ID（外键） |
| `name` | VARCHAR | 步骤名 |
| `status` | VARCHAR | 步骤状态 |
| `detail` | JSONB | 步骤详情 |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

#### knowledge_bases — 知识库表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `name` | VARCHAR | 名称 |
| `description` | TEXT | 描述 |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

#### documents — 文档表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `knowledge_base_id` | UUID | 知识库 ID（外键） |
| `filename` | VARCHAR | 文件名 |
| `status` | VARCHAR | 状态 |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

#### document_chunks — 文档切片表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `document_id` | UUID | 文档 ID（外键） |
| `content` | TEXT | 切片内容 |
| `content_type` | VARCHAR | 内容类型（text / image） |
| `source` | VARCHAR | 来源文件 |
| `image_url` | VARCHAR | 图片存储路径（MinIO） |
| `embedding` | VECTOR | 多模态向量数据 |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

#### model_configs — 模型配置表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `name` | VARCHAR | 配置名 |
| `base_url` | VARCHAR | OpenAI-compatible Base URL |
| `api_key` | VARCHAR | API Key |
| `default_model` | VARCHAR | 默认模型名 |
| `is_default` | BOOLEAN | 是否默认 |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

#### tools — 工具表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `name` | VARCHAR | 名称（唯一） |
| `type` | VARCHAR | 类型（当前支持 http） |
| `description` | TEXT | 描述 |
| `config` | JSONB | 配置（URL、Method、Headers、触发关键词等） |
| `enabled` | BOOLEAN | 是否启用 |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

### 4.2 计划新增的表

| 表名 | 说明 |
|------|------|
| `users` | 用户表（username、password_hash、role、status） |
| `tool_calls` | 工具调用日志（run_id、tool_id、input、output、status、elapsed_ms） |
| `agent_versions` | Agent 版本管理（agent_id、version、snapshot、published） |

---

## 5. API 接口

后端默认地址：`http://localhost:8000/api`

### 5.1 Health

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/health` | 检查服务状态 |

### 5.2 智能体

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/agents` | 获取智能体列表 |
| GET | `/agents/published` | 获取已发布智能体列表 |
| POST | `/agents` | 创建智能体 |
| GET | `/agents/{agent_id}` | 获取单个智能体详情 |
| PUT | `/agents/{agent_id}` | 更新智能体配置（支持部分更新） |
| DELETE | `/agents/{agent_id}` | 软删除智能体 |
| POST | `/agents/{agent_id}/publish` | 发布智能体 |
| POST | `/agents/{agent_id}/unpublish` | 下线智能体 |
| POST | `/agents/{agent_id}/duplicate` | 复制智能体 |

创建智能体请求示例：

```json
{
  "name": "客服助手",
  "description": "回答客户问题",
  "system_prompt": "你是一个企业 AI 智能体。",
  "model_config_id": "...",
  "knowledge_base_ids": ["..."],
  "tool_ids": ["current_time"]
}
```

### 5.3 知识库

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/knowledge-bases` | 获取知识库列表 |
| POST | `/knowledge-bases` | 创建知识库 |
| DELETE | `/knowledge-bases/{kb_id}` | 删除知识库 |
| POST | `/knowledge-bases/{kb_id}/documents` | 上传文档（multipart/form-data） |
| GET | `/knowledge-bases/sample-documents` | 获取示例文档列表 |
| POST | `/knowledge-bases/{kb_id}/sample-documents/{document_id}` | 导入示例文档 |
| POST | `/knowledge-bases/{kb_id}/retrieve-test` | 检索测试 |

检索测试请求示例：

```json
{
  "query": "如何申请售后？",
  "top_k": 5
}
```

### 5.4 工具

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/tools` | 获取工具列表 |
| POST | `/tools` | 创建工具 |
| GET | `/tools/{tool_id}` | 获取工具详情 |
| PUT | `/tools/{tool_id}` | 更新工具（支持部分更新） |
| DELETE | `/tools/{tool_id}` | 删除工具 |
| POST | `/tools/{tool_id}/test` | 测试工具 |

创建工具请求示例：

```json
{
  "name": "订单查询",
  "type": "http",
  "description": "查询订单状态和物流信息",
  "config": {
    "url": "http://host.docker.internal:8000/api/mock/order",
    "method": "GET",
    "trigger_keywords": ["订单", "物流", "发货", "快递"],
    "headers": {},
    "query": {},
    "body": {},
    "timeout_seconds": 20
  },
  "enabled": true
}
```

工具测试返回示例：

```json
{
  "ok": true,
  "status_code": 200,
  "elapsed_ms": 128,
  "output": {},
  "error": ""
}
```

### 5.5 模型配置

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/settings/model` | 获取默认模型配置 |
| PUT | `/settings/model` | 更新默认模型配置（无则自动创建） |
| GET | `/settings/models` | 获取模型配置列表 |
| POST | `/settings/models` | 创建模型配置 |
| PUT | `/settings/models/{config_id}` | 更新模型配置 |
| POST | `/settings/models/{config_id}/default` | 设为默认 |
| POST | `/settings/models/{config_id}/test` | 测试连通性 |
| DELETE | `/settings/models/{config_id}` | 删除模型配置 |

### 5.6 运行

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/runs` | 执行智能体（非流式） |
| POST | `/runs/stream` | 流式执行智能体（SSE） |
| GET | `/runs` | 获取运行历史列表 |
| GET | `/runs/{run_id}` | 获取单次运行详情 |

运行请求示例：

```json
{
  "agent_id": "...",
  "input": "我的订单 10086 发货了吗？"
}
```

### 5.7 Mock 接口

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/mock/order` | 模拟订单数据 |
| GET | `/mock/inventory` | 模拟库存数据 |
| GET | `/mock/weather` | 模拟天气数据 |

### 5.8 计划接口

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/auth/login` | 管理员登录 |
| POST | `/auth/logout` | 退出登录 |
| GET | `/auth/me` | 获取当前用户信息 |

---

## 6. 部署指南

### 6.1 Docker Compose 部署（推荐）

```bash
cd deploy
docker compose up --build
```

启动后访问：

| 服务 | 地址 |
|------|------|
| 前台体验 | http://localhost:5173/portal |
| 后台工作台 | http://localhost:5173 |
| 使用教程 | http://localhost:5173/guide |
| 后端接口文档 | http://localhost:8000/docs |
| PostgreSQL | localhost:15432 |
| Redis | localhost:16379 |
| MinIO API | http://localhost:19000 |
| MinIO 控制台 | http://localhost:19001 |

MinIO 默认账号：`agentpilot` / `agentpilot123`

### 6.2 常用 Docker 命令

```bash
cd deploy

# 重新构建并启动
docker compose build agentpilot-backend agentpilot-frontend
docker compose up -d agentpilot-backend agentpilot-frontend

# 查看日志
docker logs --tail 120 agentpilot-backend
docker logs --tail 120 agentpilot-frontend
```

### 6.3 本地开发

#### 后端

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate    # Windows
pip install -e .
uvicorn app.main:app --reload
```

环境变量参考 `.env.example`。Docker 环境中默认使用 Compose 内部服务名：

```text
DATABASE_URL=postgresql+asyncpg://agentpilot:agentpilot@agentpilot-postgres:5432/agentpilot
REDIS_URL=redis://agentpilot-redis:6379/0
MINIO_ENDPOINT=agentpilot-minio:9000
```

#### 前端

```bash
cd frontend
npm install
npm run dev
```

PowerShell 如果阻止 `npm.ps1`，可以使用 `npm.cmd run dev`。

### 6.4 项目目录结构

```text
pyAgent/
  backend/        Python FastAPI 后端
    app/
      agents/       智能体运行时
      api/          路由和接口
      core/         配置和中间件
      db/           数据库连接
      llm/          模型网关
      models/       数据模型
      rag/          RAG 流水线
      repositories/ 数据访问层
      schemas/      请求响应模型
      tools/        内置工具
      vector/       Embedding 服务
  frontend/       Vue 3 前端
    src/
      api/          API 客户端和类型
      pages/        页面组件
      router/       路由配置
      stores/       状态管理
      utils/        工具函数
  deploy/         Docker Compose 和数据库初始化
  docs/           项目文档
```

---

## 7. 使用指南

### 第一步：配置模型

进入后台"模型配置"页面，填写：

- 配置名称
- Base URL（如 `https://api.minimaxi.com/anthropic` 或 `http://host.docker.internal:11434/v1`）
- API Key
- 默认模型名

填写完成后点击"测试"，测试通过后再创建智能体。

### 第二步：创建知识库

进入"知识库"页面：

1. 创建知识库。
2. 选择知识库。
3. 上传 PDF、Markdown 或文本文件。
4. 输入问题做检索测试。

> 知识库适合放稳定资料（产品手册、FAQ、制度文档）。PDF 会提取可读文本后切块；扫描件或图片型 PDF 可能无法提取文字。

### 第三步：配置工具（可选）

如果智能体需要查询实时业务数据（如订单、库存、天气），进入"工具管理"页面：

1. 点击"新增工具"。
2. 填写工具名称和描述。
3. 配置 URL、Method（GET / POST）、触发关键词。
4. 按需配置 Headers、Query 参数、Body 模板和超时时间。
5. 点击"测试"验证工具是否可用。

创建工具后，在创建智能体时绑定该工具即可。运行时如果用户问题匹配触发关键词，系统会自动调用工具。

### 第四步：创建智能体

进入"智能体后台"页面，填写：

- 名称
- 描述
- 模型配置
- 系统提示词
- 知识库
- 应用工具

创建后点击"发布"，智能体会出现在前台。

### 第五步：前台体验

点击后台右上角"进入前台"，或访问 http://localhost:5173/portal。

- 前台使用流式输出，回答逐字显示，体验更自然。
- 刷新前台页面后，最近会话会保留在浏览器本地，继续作为多轮上下文参与回答。

### 第六步：查看运行过程

后台"运行测试"页面可以选择智能体并执行任务。运行后会看到回答、执行过程和引用来源。

也可以进入"运行历史"页面，查看最近的运行记录和单次运行详情（含工具调用明细和耗时）。

### 知识库和工具的分工

| 场景 | 适合知识库 | 适合工具 |
|------|-----------|---------|
| 数据特征 | 稳定或半稳定 | 实时变化 |
| 典型内容 | 产品手册、FAQ、售后政策、内部制度 | 订单查询、物流查询、库存查询、工单创建 |
| 回答策略 | 检索后回答，展示引用 | 调用工具后回答 |

回答策略优先级：

1. 通用问题 → 大模型直接回答
2. 文档问题 → 检索知识库后回答，展示引用
3. 实时业务问题 → 调用工具后回答
4. 没有可靠依据 → 明确说明无法确认

---

## 8. 开发指南

### 8.1 运行时链路

一次智能体运行经过以下步骤：

1. 接收用户问题。
2. 根据智能体绑定的知识库执行检索。
3. 根据智能体绑定的工具和用户问题调用应用工具。
4. 将知识库上下文、工具结果和用户问题交给大模型。
5. 保存运行记录、执行步骤、引用来源和回答。

### 8.2 检索增强细节

- 上传 PDF 时使用 PDF 文本提取，不再把二进制内容直接切块。
- 文档入库前会过滤不可读文本，避免 PDF 对象流或压缩流进入知识库。
- 检索结果会过滤乱码、重复片段和低相关内容。
- 真实 Embedding 服务不可用时会退回本地向量，同时使用中文关键词匹配兜底。

### 8.3 回答展示

前端回答展示位于：

- 前台：`frontend/src/pages/PortalPage.vue`
- 运行测试：`frontend/src/pages/ChatPage.vue`
- 格式化工具：`frontend/src/utils/answerFormat.ts`

当前支持：

` 折叠为"思考过程"。
- Markdown 代码块显示为灰色代码框。
- 清理标题符号和分隔线。
- Markdown 渲染结果经 DOMPurify 消毒，防止 XSS 攻击。

### 8.4 流式输出

前台 `/portal` 使用 SSE 流式输出：

- 后端端点：`POST /api/runs/stream`，返回 `text/event-stream`。
- 前端使用 `fetch` + `ReadableStream` 逐块读取。
- 后台 `/chat` 仍使用非流式接口 `POST /api/runs`。

### 8.5 路由

前端路由定义在 `frontend/src/router/index.ts`。

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | DashboardPage | 总览 |
| `/guide` | GuidePage | 使用教程 |
| `/agents` | AgentsPage | 智能体后台 |
| `/knowledge` | KnowledgePage | 知识库 |
| `/tools` | ToolsPage | 工具管理 |
| `/settings/model` | ModelSettingsPage | 模型配置 |
| `/runs` | RunsPage | 运行历史 |
| `/chat` | ChatPage | 运行测试 |
| `/portal` | PortalPage | 独立前台体验页 |
| `/:pathMatch(.*)*` | — | 404 兜底，重定向到首页 |

### 8.6 主题

深色 / 亮色主题状态在 `frontend/src/stores/ui.ts`。

主题会写入 `localStorage`，并同步到 `body[data-theme]`，用于控制自定义 CSS 变量。

---

## 9. 工具系统

### 9.1 定位

工具用于连接实时业务系统，不应该替代知识库。

| 适合工具 | 适合知识库 |
|---------|-----------|
| 订单查询 | FAQ |
| 物流查询 | 产品手册 |
| 库存查询 | 售后政策 |
| 用户信息查询 | 内部制度 |
| 工单创建 | 培训资料 |
| 当前时间 | |

### 9.2 当前实现

**内置工具**（`backend/app/tools/registry.py`）：

- `current_time`：当前时间
- `order_lookup`：订单查询示例

**数据库持久化工具**（`backend/app/repositories/tools.py`）：

- 工具表 `tools` 持久化存储
- HTTP 工具配置（URL、Method、Headers、Query、Body、触发关键词、超时）
- 工具 CRUD（创建、读取、更新、删除）
- 工具测试接口（发送实际 HTTP 请求，返回状态码、耗时和输出）
- Agent 绑定数据库工具
- 运行时按关键词触发工具调用
- 内置工具作为 fallback，数据库工具优先

### 9.3 工具调用流程

```
1. Agent 绑定工具
2. 用户提问
3. 运行时判断是否需要工具（关键词匹配）
4. 生成工具参数
5. 调用工具
6. 保存工具调用记录
7. 将工具结果交给大模型生成回答
```

### 9.4 当前限制

- 工具管理页面已具备基础 CRUD 和测试能力，后续需要优化交互体验。
- 还没有工具调用日志表（`tool_calls`）。
- 还没有 SQL 工具。
- 还没有鉴权配置页。

### 9.5 安全原则

- SQL 工具默认只允许只读查询。
- HTTP 工具不应明文展示敏感 Header。
- 工具测试和调用应记录日志。
- 后台工具管理需要管理员权限。

---

## 10. 智能体运行时

### 10.1 运行流程

入口：`POST /api/runs`

1. 根据 `agent_id` 读取智能体配置。
2. 根据用户输入检索智能体绑定的知识库，并过滤低质量和低相关片段。
3. 根据用户输入和工具绑定情况调用应用工具。
4. 拼接系统提示词、多轮历史、用户问题、知识库上下文、工具结果。
5. 调用模型网关生成回答。
6. 保存运行记录和执行步骤。
7. 返回回答、引用来源、执行过程和模型信息。

### 10.2 上下文结构

```
用户问题：
...

知识库上下文：
...

应用工具结果：
...

请给出清晰回答。优先使用应用工具结果回答实时业务数据；
使用知识库内容时说明来源；如果没有可靠依据，请明确说明无法确认。
```

### 10.3 执行步骤

当前返回的步骤包括：

- 接收任务
- 知识库检索
- 应用工具调用
- 大模型生成

### 10.4 错误处理

当真实大模型调用失败时，后端会返回错误说明，提示用户检查：

- 模型接口地址
- API Token
- 模型名
- 后端服务

### 10.5 前台上下文

`/portal` 会把最近会话和多轮上下文保存到浏览器 `localStorage`。刷新页面后会恢复消息列表和上下文，继续发送给后端用于多轮回答。

### 10.6 已实现的增强

- Run 列表和 Run 详情页。
- 引用来源和执行步骤可在运行历史中回看。
- 流式输出已接入。
- 工具调用参数由模型或规则生成。
- Run 详情页展示每一步耗时。
- 工具调用结果在运行详情中展示。

### 10.7 待实现的增强

- 支持失败重试。
- 支持运行中断和取消。

---

## 11. 开发路线与进度

### 11.1 第二版目标

把第一版可演示工作台升级为可长期使用的智能体管理平台。

### 11.2 进度总览

| 优先级 | 模块 | 完成 | 总计 | 完成率 |
|--------|------|------|------|--------|
| P0 | 智能体管理补齐 | 6 | 6 | 100% |
| P1 | 工具系统产品化 | 5 | 6 | 83% |
| P2 | 运行历史 | 5 | 6 | 83% |
| P3 | 基础权限 | 1 | 4 | 25% |
| P4 | 前台体验增强 | 2 | 4 | 50% |
| P5 | 检索增强 | 4 | 10 | 40% |
| **合计** | | **23** | **36** | **64%** |

### 11.3 P0 智能体管理补齐 — 已完成

- [x] 编辑智能体名称、描述、系统提示词
- [x] 修改模型配置、知识库、应用工具绑定
- [x] 删除智能体
- [x] 复制智能体
- [x] 发布 / 下线智能体
- [x] 前台只显示已发布智能体

### 11.4 P1 工具系统产品化 — 83%

- [x] 工具系统建模
- [x] 工具管理基础页面
- [x] 新增 HTTP 工具
- [x] 配置 URL、Method、Headers、Query、Body
- [x] 工具测试接口
- [ ] 工具调用日志
- [x] 智能体绑定真实工具

### 11.5 P2 运行历史 — 83%

- [x] Run 列表页
- [x] Run 详情页
- [x] 展示输入、回答、引用、模型、状态和执行步骤
- [x] 展示工具调用明细
- [x] 展示耗时
- [ ] 失败原因和重试入口

### 11.6 P3 基础权限 — 25%

- [ ] 管理员登录
- [ ] 后台鉴权
- [x] 前台匿名访问（无鉴权体系下天然满足）
- [ ] Token 过期和退出登录

### 11.7 P4 前台体验增强 — 50%

- [x] 流式输出
- [x] 会话保留
- [ ] 回答重试
- [ ] 更清晰的错误提示

### 11.8 P5 检索增强 — 40%

- [x] PDF 文本提取后切块
- [x] 过滤乱码、二进制残留和重复片段
- [x] 过滤低相关上下文
- [x] 中文关键词匹配兜底
- [ ] 文档级管理和单文档删除
- [ ] OCR 支持扫描件 PDF
- [ ] 多模态 Embedding（CLIP 等统一向量空间模型）
- [ ] 图片提取（PDF 中的图片独立提取、切块和向量化）
- [ ] 跨模态检索（文本查图片、图片查文本）
- [ ] document_chunks 表增加 content_type 和 image_url 字段
- [ ] Embedding 服务增加 embed_image 方法

### 11.9 第二版验收流程

第二版完成后，应能够跑通：

1. 管理员登录后台。
2. 创建并发布智能体。
3. 绑定知识库和真实 HTTP 工具。
4. 前台选择已发布智能体。
5. 用户提问。
6. 系统按需调用知识库和工具。
7. 前台实时显示回答。
8. 后台查看运行历史和详情。

### 11.10 不进入第二版范围

- 多租户计费
- 复杂审批流
- Agent Studio 工作流画布
- 大规模分布式调度
- 自动优化和评测闭环

---

## 12. 常见问题

### 模型测试 401

通常是 API Key 无效、过期或填错。请检查 Key 是否正确，是否已过期。

### 回答慢或复杂问题失败

后端和前端超时时间已经调长，但复杂模型仍可能需要等待。可以检查后端日志和模型服务状态。

### 前台没有智能体

先到后台创建并发布智能体。前台只展示已发布智能体。

### 知识库检索没有结果

如果问题过于宽泛，系统会避免返回低相关片段。可以换成更具体的问题，例如包含产品名、药品名、条款名或业务关键词。

### 扫描件 PDF 无法提取文字

当前仅支持文本型 PDF。扫描件或图片型 PDF 需要 OCR 能力，计划在后续版本支持。

### 工具调用没有触发

检查工具的触发关键词是否与用户问题匹配。关键词匹配是运行时决定是否调用工具的主要依据。
