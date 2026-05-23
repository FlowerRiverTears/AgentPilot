# 系统架构

## 总体结构

AgentPilot 由前端、后端、数据库和基础设施组成。

```text
用户浏览器
  ├─ 后台工作台：模型、知识库、工具、智能体管理
  └─ 前台体验：选择已创建智能体并对话

Vue 3 前端
  └─ /api 请求

FastAPI 后端
  ├─ 模型配置
  ├─ 知识库检索
  ├─ 应用工具调用
  ├─ 智能体运行时
  └─ 运行记录

PostgreSQL / Redis / MinIO
```

## 前端模块

- `App.vue`：后台布局、主题切换、前后台入口。
- `DashboardPage.vue`：总览和第一版状态。
- `GuidePage.vue`：使用教程。
- `AgentsPage.vue`：智能体后台。
- `KnowledgePage.vue`：知识库管理和检索测试。
- `ModelSettingsPage.vue`：模型配置。
- `ChatPage.vue`：后台运行测试。
- `PortalPage.vue`：独立前台体验页。
- `stores/workspace.ts`：业务状态和 API 调用。
- `stores/ui.ts`：深色 / 亮色主题状态。
- `utils/answerFormat.ts`：回答格式化。

## 后端模块

- `api/routes/agents.py`：智能体接口。
- `api/routes/knowledge.py`：知识库接口。
- `api/routes/runs.py`：运行接口。
- `api/routes/settings.py`：模型配置接口。
- `api/routes/tools.py`：工具列表接口。
- `agents/runtime.py`：智能体运行时。
- `llm/gateway.py`：OpenAI-compatible 模型网关。
- `repositories/memory.py`：当前数据库访问层。
- `tools/registry.py`：内置工具注册和调用。
- `rag/pipeline.py`：切块和检索逻辑。

## 数据流

1. 后台创建模型配置。
2. 后台创建知识库并上传文档。
3. 后台创建智能体，绑定模型、知识库和工具。
4. 前台读取智能体列表。
5. 用户发送问题。
6. 后端检索知识库并调用工具。
7. 后端调用大模型生成回答。
8. 前端展示回答、引用来源和执行过程。

## 部署结构

Docker Compose 包含：

- `agentpilot-frontend`：Nginx 托管前端构建产物。
- `agentpilot-backend`：FastAPI 服务。
- `agentpilot-postgres`：PostgreSQL + pgvector。
- `agentpilot-redis`：Redis。
- `agentpilot-minio`：对象存储。

## 设计原则

- 前台和后台职责分离。
- 知识库负责稳定资料，工具负责实时业务数据。
- 智能体运行必须可追踪。
- 模型网关保持 OpenAI-compatible，便于替换供应商。
- 第二版优先补管理能力，再做复杂编排。
