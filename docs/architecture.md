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
- `ToolsPage.vue`：工具管理。
- `ModelSettingsPage.vue`：模型配置。
- `RunsPage.vue`：运行历史。
- `ChatPage.vue`：后台运行测试。
- `LoginPage.vue`：管理员登录。
- `PortalPage.vue`：独立前台体验页。
- `stores/workspace.ts`：业务状态和 API 调用。
- `stores/auth.ts`：Token 和用户状态管理。
- `stores/ui.ts`：深色 / 亮色主题状态。
- `utils/answerFormat.ts`：回答格式化。

## 后端模块

- `api/routes/agents.py`：智能体接口。
- `api/routes/auth.py`：鉴权接口，管理员登录、退出、获取当前用户。
- `api/routes/knowledge.py`：知识库接口。
- `api/routes/runs.py`：运行接口。
- `api/routes/settings.py`：模型配置接口。
- `api/routes/tools.py`：工具 CRUD 和测试接口。
- `agents/runtime.py`：智能体运行时。
- `core/deps.py`：鉴权依赖，JWT 鉴权依赖注入（get_current_user、get_optional_user）。
- `core/security.py`：安全工具，JWT 生成/验证、bcrypt 密码哈希。
- `llm/gateway.py`：OpenAI-compatible 模型网关。
- `models/user.py`：用户表模型。
- `models/tool_call.py`：工具调用日志表模型。
- `repositories/memory.py`：当前数据库访问层。
- `repositories/tools.py`：数据库持久化工具访问层。
- `tools/registry.py`：内置工具注册和调用（fallback）。
- `rag/pipeline.py`：切块和检索逻辑。
- `rag/document_loader.py`：文档解析，支持文本和图片提取。
- `vector/embeddings.py`：多模态 Embedding 服务，支持文本和图片向量化。

## 数据流

### 运行时链路

1. 后台创建模型配置。
2. 管理员登录后台。
3. 后台创建知识库并上传文档。
4. 系统解析文档，提取文本和图片，分别切块和多模态 Embedding。
5. 后台创建智能体，绑定模型、知识库和工具。
6. 前台读取智能体列表。
7. 用户发送问题。
8. 后端检索知识库（支持跨模态检索）并调用工具。
9. 后端调用大模型生成回答。
10. 前端展示回答、引用来源和执行过程。

前台 `/portal` 使用 SSE 流式输出（`POST /api/runs/stream`），回答逐字显示；后台 `/chat` 使用非流式接口（`POST /api/runs`），等待完整回答后展示。

### 管理链路

1. 后台创建 HTTP 工具，配置 URL 和触发关键词。
2. 创建智能体时绑定工具。
3. 运行时根据用户问题匹配触发关键词，自动调用工具。

## 部署结构

Docker Compose 包含：

- `agentpilot-frontend`：Nginx 托管前端构建产物。
- `agentpilot-backend`：FastAPI 服务。
- `agentpilot-postgres`：PostgreSQL + pgvector。
- `agentpilot-redis`：Redis。
- `agentpilot-minio`：对象存储。

## 设计原则

- 前台和后台职责分离。
- 知识库负责稳定资料（含图片），工具负责实时业务数据。
- 智能体运行必须可追踪。
- 模型网关保持 OpenAI-compatible，便于替换供应商。
- 幂等性：数据库迁移和初始化使用 IF NOT EXISTS 确保幂等。
- 向后兼容：新增字段提供默认值，不删除已有字段。
- 优雅降级：Embedding 服务不可用时 fallback 到本地 stub 向量；MinIO 不可用时跳过图片上传；工具调用失败时 fallback 到内置工具。
- 可测试性：所有接口可通过 FastAPI 自动生成的 /docs 页面测试。

## 安全架构

### 认证

- JWT Bearer Token 认证，Token 有效期 24 小时。
- 密码使用 bcrypt 哈希存储。
- 后台接口强制鉴权（`get_current_user`），前台接口可选鉴权（`get_optional_user`）。
- 开发环境可通过 `auth_enabled=False` 关闭鉴权。

### 授权

- 用户模型包含 `role` 字段（当前仅 admin），RBAC 校验尚未实现。
- 规划：admin 可管理所有资源，user 仅可查看运行历史和使用前台。

### 数据安全

- API Key 当前明文存储，建议加密（见 database.md 安全备注）。
- 前端 XSS 防护：Markdown 渲染结果经 DOMPurify 消毒。
- 工具调用日志不记录敏感 Header 值。

### 网络安全

- 生产环境应强制 HTTPS。
- Docker 部署时数据库和 Redis 端口不应直接暴露到公网。
- CORS 配置应限制允许的来源域名。
