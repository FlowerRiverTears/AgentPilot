# 开发说明

## Docker Compose

推荐使用 Docker Compose 启动完整环境：

```bash
cd deploy
docker compose up --build
```

访问地址：

- 前台体验：http://localhost:5173/portal
- 后台工作台：http://localhost:5173
- 使用教程：http://localhost:5173/guide
- 后端接口文档：http://localhost:8000/docs
- PostgreSQL：localhost:15432
- Redis：localhost:16379
- MinIO API：http://localhost:19000
- MinIO 控制台：http://localhost:19001

## 常用 Docker 命令

```bash
cd deploy
docker compose build agentpilot-backend agentpilot-frontend
docker compose up -d agentpilot-backend agentpilot-frontend
docker logs --tail 120 agentpilot-backend
docker logs --tail 120 agentpilot-frontend
```

## 本地后端

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -e .
uvicorn app.main:app --reload
```

环境变量参考根目录 `.env.example`。Docker 环境中默认使用 Compose 内部服务名：

```text
DATABASE_URL=postgresql+asyncpg://agentpilot:agentpilot@agentpilot-postgres:5432/agentpilot
REDIS_URL=redis://agentpilot-redis:6379/0
MINIO_ENDPOINT=agentpilot-minio:9000
```

## 本地前端

```bash
cd frontend
npm install
npm run dev
```

PowerShell 如果阻止 `npm.ps1`，可以使用：

```bash
npm.cmd run dev
npm.cmd run build
```

## 当前前端页面

- `/`：总览
- `/guide`：使用教程
- `/agents`：智能体后台
- `/knowledge`：知识库
- `/tools`：工具管理
- `/settings/model`：模型配置
- `/runs`：运行历史
- `/chat`：运行测试
- `/portal`：独立前台体验页，刷新后保留会话和上下文

`/portal` 不显示后台菜单；前台和后台通过按钮互相跳转。

## 运行时链路

一次智能体运行会经过：

1. 接收用户问题。
2. 根据智能体绑定的知识库执行检索。
3. 根据智能体绑定的工具和用户问题调用应用工具。
4. 将知识库上下文、工具结果和用户问题交给大模型。
5. 保存运行记录、执行步骤、引用来源和回答。

检索增强细节：

- 上传 PDF 时使用 PDF 文本提取，不再把二进制内容直接切块。
- 文档入库前会过滤不可读文本，避免 PDF 对象流或压缩流进入知识库。
- 检索结果会过滤乱码、重复片段和低相关内容。
- 真实 Embedding 服务不可用时会退回本地向量，同时使用中文关键词匹配兜底。

## 知识库和工具

知识库用于稳定资料，例如 FAQ、产品手册、政策说明。

工具用于实时业务数据，例如订单、库存、物流、用户信息。

当前内置工具：

- `current_time`：当前时间。
- `order_lookup`：订单查询示例。

工具入口：

- 内置工具注册：`backend/app/tools/registry.py`
- 数据库持久化工具：`backend/app/repositories/tools.py`
- 工具列表接口：`GET /api/tools`
- 工具 CRUD 接口：`POST / PUT / DELETE /api/tools`
- 工具测试接口：`POST /api/tools/{id}/test`
- 运行时调用：`backend/app/agents/runtime.py`

## 回答展示

前端回答展示位于：

- 前台：`frontend/src/pages/PortalPage.vue`
- 运行测试：`frontend/src/pages/ChatPage.vue`
- 格式化工具：`frontend/src/utils/answerFormat.ts`

当前支持：

- `<think>...</think>` 折叠为“思考过程”。
- Markdown 代码块显示为灰色代码框。
- 清理标题符号和分隔线。
- Markdown 渲染结果经 DOMPurify 消毒，防止 XSS 攻击。

## 流式输出

前台 `/portal` 使用 SSE（Server-Sent Events）流式输出：

- 后端端点：`POST /api/runs/stream`，返回 `text/event-stream`。
- 前端使用 `fetch` + `ReadableStream` 逐块读取。
- 后台 `/chat` 仍使用非流式接口 `POST /api/runs`。

## 路由

前端路由定义在 `frontend/src/router/index.ts`。

- 未匹配路径会重定向到首页（`/:pathMatch(.*)*`）。

## 主题

深色 / 亮色主题状态在：

```text
frontend/src/stores/ui.ts
```

主题会写入 `localStorage`，并同步到 `body[data-theme]`，用于控制自定义 CSS 变量。
