<div align="center">

# AgentPilot

**AI Agent Workbench · AI 智能体工作台**

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com)
[![Python](https://img.shields.io/badge/Python-3.11-green.svg)](https://python.org)
[![Vue](https://img.shields.io/badge/Vue-3-brightgreen.svg)](https://vuejs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docker.com)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

</div>

---

> **[English](#english)** · **[中文](#中文)**

---

<a id="english"></a>

## English

AgentPilot is an AI Agent workbench for building, managing, and experiencing intelligent agents. Create agents in the admin workspace with model binding, knowledge base integration, and tool orchestration — then let users interact with them in a dedicated portal.

### Highlights

- **Admin / Portal Separation** — Build agents in the admin workspace; users interact in a standalone portal.
- **Multimodal RAG** — PDF text & image extraction, chunking, multimodal embedding (CLIP), cross-modal retrieval (text↔image), citation display with image thumbnails.
- **Tool Orchestration** — HTTP tool creation, testing, and runtime invocation for real-time business data.
- **Streaming Output** — SSE-based real-time response with process folding and code block rendering.
- **Run History** — Full execution trace: task received → knowledge retrieval → tool calls → LLM generation.
- **Auth & Access Control** — JWT authentication, role-based access control (admin/user), backend API auth protection, portal anonymous access.

### Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.11 · FastAPI · Pydantic · SQLAlchemy |
| Frontend | Vue 3 · TypeScript · Vite · Pinia · Naive UI |
| Data | PostgreSQL + pgvector · Redis · MinIO |
| AI | OpenAI-compatible API / Ollama · bge-m3 · CLIP |
| Deploy | Docker Compose |

### Architecture

```
┌─────────────┐     ┌─────────────┐
│  Admin UI   │     │  Portal UI  │
│  (Backend)  │     │  (Frontend) │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └───────┬───────────┘
               │
        ┌──────┴──────┐
        │   FastAPI    │
        │   Backend    │
        └──────┬──────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───┴───┐ ┌───┴───┐ ┌───┴───┐
│PgVector│ │ Redis │ │ MinIO │
└───────┘ └───────┘ └───────┘
```

### Quick Start

```bash
cd deploy
docker compose up --build
```

| Service | URL |
|---------|-----|
| Admin Workspace | http://localhost:5173 |
| Portal | http://localhost:5173/portal |
| API Docs | http://localhost:8000/docs |
| MinIO Console | http://localhost:19001 |

MinIO default credentials (please change after first launch): see `deploy/docker-compose.yml`

### Usage Flow

1. Open the admin workspace at `http://localhost:5173`
2. Configure a model in **Model Settings**
3. Create a knowledge base in **Knowledge** and upload documents
4. Create an agent in **Agents**, bind model, knowledge base, and tools
5. Click **Enter Portal** or visit `http://localhost:5173/portal`
6. Select an agent and start chatting

### Features

- [x] Docker Compose one-click deployment
- [x] FastAPI backend with async support
- [x] Vue 3 + TypeScript frontend
- [x] PostgreSQL persistence (agents, knowledge, runs)
- [x] Multi-model configuration with connectivity test
- [x] PDF parsing with text & image extraction
- [x] Multimodal embedding (CLIP) — text & image in unified vector space
- [x] Cross-modal retrieval — text↔image search
- [x] MinIO image storage
- [x] Chunk filtering (junk, duplicates, low-relevance)
- [x] Agent CRUD, publish/unpublish, copy, soft delete
- [x] Portal shows only published agents
- [x] Session persistence across page refresh
- [x] HTTP tool management (create, edit, test, delete)
- [x] Runtime tool invocation
- [x] Agent Run execution trace
- [x] Run history list and detail view
- [x] SSE streaming output
- [x] JWT admin login & backend auth protection
- [x] Tool call logging
- [x] Run failure reason display and retry
- [x] Document-level management and single document deletion
- [x] XSS protection (DOMPurify)
- [x] Dark / light theme

### Roadmap

Completed (v2.0):
- [x] OCR support for scanned PDFs
- [x] Context compression (sliding window + summary)
- [x] Multi-knowledge-base binding per agent
- [x] Agent import/export (JSON)
- [x] Answer feedback (thumbs up/down)
- [x] Mermaid.js chart rendering in agent answers

Completed (v3.0):
- [x] Evaluation system
- [x] Multi-agent collaboration
- [x] RBAC with API Key management

Planned (v4.0):
- [ ] Visual workflow editor
- [ ] Multi-tenant isolation
- [ ] Plugin marketplace
- [ ] WebSocket support

### Documentation

- [Project Docs](docs/index.md)
- [Architecture](docs/architecture.md)
- [Database Design](docs/database.md)
- [API Reference](docs/api.md)
- [Tool System](docs/tool-system.md)
- [Agent Runtime](docs/agent-runtime.md)
- [Roadmap v2](docs/roadmap-v2.md)
- [Development Guide](docs/development.md)
- [User Guide](docs/user-guide.md)

### Local Development

**Backend:**

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -e .
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### Project Structure

```
backend/    Python FastAPI backend
frontend/   Vue 3 frontend
deploy/     Docker Compose & DB init
docs/       Documentation
```

---

<a id="中文"></a>

## 中文

AgentPilot 是一个 AI 智能体工作台，用于在后台创建和管理智能体、接入模型、绑定知识库和应用工具，并在独立前台提供用户体验。

### 核心亮点

- **前后台分离** — 后台制造和管理智能体，前台只面向用户对话体验。
- **多模态 RAG** — PDF 文本和图片提取、切块、多模态 Embedding（CLIP）、跨模态检索（文本↔图片）、引用来源展示图片缩略图。
- **工具编排** — HTTP 工具创建、测试和运行时调用，适合订单、库存等实时业务数据。
- **流式输出** — SSE 实时响应，思考过程折叠、代码块渲染。
- **运行历史** — 完整执行轨迹：接收任务 → 知识库检索 → 工具调用 → 大模型生成。
- **鉴权与权限** — JWT 认证、角色权限控制（admin/user）、后台 API 鉴权保护、前台匿名访问。

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11 · FastAPI · Pydantic · SQLAlchemy |
| 前端 | Vue 3 · TypeScript · Vite · Pinia · Naive UI |
| 数据层 | PostgreSQL + pgvector · Redis · MinIO |
| AI | OpenAI 兼容 API / Ollama · bge-m3 · CLIP |
| 部署 | Docker Compose |

### 系统架构

```
┌─────────────┐     ┌─────────────┐
│  后台工作台   │     │  前台体验页   │
│  (Admin UI) │     │  (Portal)   │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └───────┬───────────┘
               │
        ┌──────┴──────┐
        │   FastAPI    │
        │   后端服务    │
        └──────┬──────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───┴───┐ ┌───┴───┐ ┌───┴───┐
│PgVector│ │ Redis │ │ MinIO │
└───────┘ └───────┘ └───────┘
```

### 快速开始

```bash
cd deploy
docker compose up --build
```

| 服务 | 地址 |
|------|------|
| 后台工作台 | http://localhost:5173 |
| 前台体验 | http://localhost:5173/portal |
| 接口文档 | http://localhost:8000/docs |
| MinIO 控制台 | http://localhost:19001 |

MinIO 默认账号（首次启动后请立即修改）：参见 `deploy/docker-compose.yml`

### 使用流程

1. 进入后台：`http://localhost:5173`
2. 打开"模型配置"，新增或确认一个可用模型
3. 打开"知识库"，创建知识库并上传文档
4. 打开"智能体"，创建智能体，选择模型、知识库和应用工具
5. 点击右上角"进入前台"，或访问 `http://localhost:5173/portal`
6. 在前台选择智能体并开始对话

### 已实现功能

- [x] Docker Compose 一键部署
- [x] FastAPI 异步后端
- [x] Vue 3 + TypeScript 前端
- [x] PostgreSQL 持久化（智能体、知识库、运行记录）
- [x] 多模型配置和连通性测试
- [x] PDF 解析，文本和图片提取
- [x] 多模态 Embedding（CLIP）— 文本和图片统一向量空间
- [x] 跨模态检索 — 文本↔图片搜索
- [x] MinIO 图片对象存储
- [x] 检索结果过滤乱码、重复片段和低相关上下文
- [x] 智能体 CRUD、发布/下线、复制、软删除
- [x] 前台只展示已发布智能体
- [x] 刷新后保留会话上下文
- [x] HTTP 工具管理（创建、编辑、测试、删除）
- [x] 运行时工具调用
- [x] Agent Run 执行轨迹展示
- [x] 运行历史列表和详情
- [x] SSE 流式输出
- [x] JWT 管理员登录和后台鉴权保护
- [x] 工具调用日志记录和查询
- [x] 运行失败原因展示和重试入口
- [x] 知识库文档级管理和单文档删除
- [x] XSS 防护（DOMPurify）
- [x] 深色/亮色主题切换

### 路线图

已完成（v2.0）：
- [x] OCR 支持扫描件 PDF
- [x] 上下文压缩（滑动窗口 + 摘要）
- [x] 一个智能体绑定多个知识库
- [x] 智能体导入/导出（JSON）
- [x] 回答反馈（点赞/点踩）
- [x] Mermaid.js 图表渲染

已完成（v3.0）：
- [x] 评测系统
- [x] 多智能体协作
- [x] RBAC 与 API Key 管理

计划中（v4.0）：
- [ ] 可视化工作流编辑器
- [ ] 多租户隔离
- [ ] 插件市场
- [ ] WebSocket 支持

### 文档索引

- [项目文档（整合版）](docs/index.md)
- [系统架构](docs/architecture.md)
- [数据库设计](docs/database.md)
- [API 说明](docs/api.md)
- [工具系统设计](docs/tool-system.md)
- [智能体运行时](docs/agent-runtime.md)
- [第二版路线](docs/roadmap-v2.md)
- [开发说明](docs/development.md)
- [使用教程](docs/user-guide.md)

### 本地开发

**后端：**

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -e .
uvicorn app.main:app --reload
```

**前端：**

```bash
cd frontend
npm install
npm run dev
```

### 目录结构

```
backend/    Python FastAPI 后端
frontend/   Vue 3 前端
deploy/     Docker Compose 和数据库初始化
docs/       开发文档
```

---

<div align="center">

**AgentPilot** · Build, Manage, and Experience AI Agents

</div>
