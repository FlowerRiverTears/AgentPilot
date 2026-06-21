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
- `/eval`：评测系统
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

## 环境要求

| 工具 | 最低版本 |
|------|----------|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker | 24+ |
| Docker Compose | v2+ |

## 数据库迁移

当前使用 Alembic 管理数据库迁移。

### 创建迁移

修改模型后，生成迁移脚本：

```bash
cd backend
alembic revision --autogenerate -m "描述本次变更"
```

### 执行迁移

```bash
cd backend
alembic upgrade head
```

### 回滚迁移

```bash
cd backend
alembic downgrade -1
```

### 查看迁移状态

```bash
cd backend
alembic current
alembic history
```

> 注意：Docker 环境中后端启动时会自动执行 `alembic upgrade head`，无需手动操作。

## 代码规范

- 后端：遵循 PEP 8，使用 ruff 格式化和检查。
- 前端：使用 ESLint + Prettier，配置在 `frontend/.eslintrc` 和 `frontend/.prettierrc`。
- Git 提交信息：建议使用 Conventional Commits 格式（`feat:`, `fix:`, `docs:`, `chore:` 等）。

## 测试

- 后端测试：`pytest`，测试文件位于 `backend/tests/`。
- 前端测试：暂未配置，规划使用 Vitest。
- 运行后端测试：`cd backend && pytest`

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://agentpilot:agentpilot@localhost:15432/agentpilot` | 数据库连接 |
| `REDIS_URL` | `redis://localhost:16379/0` | Redis 连接 |
| `MINIO_ENDPOINT` | `localhost:19000` | MinIO 端点 |
| `MINIO_ACCESS_KEY` | `agentpilot` | MinIO 访问密钥 |
| `MINIO_SECRET_KEY` | `agentpilot123` | MinIO 密钥 |
| `JWT_SECRET_KEY` | `agentpilot-dev-secret-change-in-production` | JWT 签名密钥（⚠️ 生产环境必须修改） |
| `JWT_EXPIRE_MINUTES` | `1440` | Token 有效期（分钟） |
| `AUTH_ENABLED` | `true` | 是否启用鉴权 |
| `ADMIN_USERNAME` | `admin` | 默认管理员用户名 |
| `ADMIN_PASSWORD` | `admin123` | 默认管理员密码（⚠️ 首次登录后请修改） |
| `ENCRYPTION_KEY` | — | API Key 加密密钥（Fernet，生产环境必须设置） |
| `RATE_LIMIT_ENABLED` | `true` | 是否启用登录限流 |
| `LOGIN_RATE_LIMIT` | `5` | 每分钟最大登录尝试次数 |

## 日志

- 后端日志输出到 stdout，Docker 环境下通过 `docker logs` 查看。
- 日志级别：DEBUG / INFO / WARNING / ERROR。
- 建议生产环境使用 JSON 结构化日志，便于日志聚合和分析。

## v3.0 新增内容

### 新增环境变量

v3.0 新增以下环境变量，用于支持向量数据库切换、OCR、上下文压缩等新功能：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VECTOR_DB_BACKEND` | `pgvector` | 向量数据库后端（pgvector/qdrant） |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant 服务地址 |
| `APP_VERSION` | `3.0.0` | 应用版本号 |
| `OCR_ENABLED` | `true` | 是否启用 OCR |
| `OCR_LANGUAGE` | `chi_sim+eng` | Tesseract 语言 |
| `OCR_DPI` | `200` | PDF 转图片 DPI |
| `CONTEXT_TOKEN_THRESHOLD` | `6000` | 上下文压缩阈值 |
| `CONTEXT_RECENT_TURNS` | `6` | 保留最近对话轮数 |

> 说明：`VECTOR_DB_BACKEND` 切换为 `qdrant` 时需同时配置 `QDRANT_URL`；OCR 相关变量仅在 `OCR_ENABLED=true` 时生效；上下文压缩会在对话 token 数超过 `CONTEXT_TOKEN_THRESHOLD` 时触发，保留最近 `CONTEXT_RECENT_TURNS` 轮对话。

### 新增 Python 依赖

v3.0 后端新增以下 Python 依赖：

- `pytesseract`：OCR 文字识别，用于扫描件和图片型 PDF 的文字提取。
- `pdf2image`：PDF 转图片，配合 pytesseract 实现扫描件 OCR。

安装方式：

```bash
cd backend
pip install pytesseract pdf2image
```

> 系统依赖：使用 OCR 功能还需安装 Tesseract OCR 引擎和 poppler。Windows 可通过安装包安装 Tesseract，poppler 需单独配置；Linux 可通过 `apt install tesseract-ocr poppler-utils` 安装。

### 新增前端依赖

v3.0 前端新增以下依赖：

- `mermaid`：图表渲染库，用于渲染 Mermaid 语法的流程图、时序图、甘特图等。

安装方式：

```bash
cd frontend
npm install mermaid
```

### 新增 API 路由

v3.0 后端新增以下 API 路由：

| 路由 | 说明 |
|------|------|
| `/api/conversations` | 会话管理（创建、查询、删除会话） |
| `/api/feedback` | 反馈管理（点赞、点踩、统计查询） |
| `/api/files` | 文件上传（支持 PDF/TXT/MD/图片） |
| `/api/eval` | 智能体评测（数据集管理、触发评测、查看报告） |
| `/api/workflows` | 工作流管理（工作流 CRUD、节点配置、执行） |
| `/api/rag-tuning` | RAG 调优（检索参数配置、检索测试） |
| `/ws/chat` | WebSocket 聊天（双向实时通信） |

> 说明：`/ws/chat` 为 WebSocket 端点，不同于其他 REST 接口，使用 ws/wss 协议连接。

### 新增前端页面

v3.0 前端新增以下页面路由：

| 路由 | 页面 | 说明 |
|------|------|------|
| `/eval` | 智能体评测 | 创建评测数据集、触发评测、查看准确率报告 |
| `/workflows` | 工作流画布 | 可视化编排工作流节点和连线 |
| `/rag-tuning` | RAG 调优 | 按知识库调整检索参数并实时测试 |

> 说明：新增页面均需管理员登录后访问，路由定义在 `frontend/src/router/index.ts`。
