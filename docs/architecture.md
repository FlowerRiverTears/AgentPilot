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
- `EvalPage.vue`：评测系统页面。
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
- `api/routes/eval.py`：评测系统接口。
- `api/routes/files.py`：文件上传接口。
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
- 管理员操作使用 `get_current_admin` 依赖，仅 admin 角色可访问。
- 开发环境可通过 `auth_enabled=False` 关闭鉴权。
- 生产模式下强制要求设置强 JWT 密钥，拒绝默认值启动。
- 登录接口限流：每分钟最多 5 次尝试，防止暴力破解。
- Token 黑名单：登出后 Token 通过 Redis 维护的黑名单失效。

### 授权

- 用户模型包含 `role` 字段（admin/user），RBAC 校验已实现 admin 级别。
- Admin 可管理所有资源，user 仅可查看运行历史和使用前台。
- API Key 管理功能规划中。

### 数据安全

- API Key 使用 Fernet/AES-256 加密存储，不再明文保存。
- 前端 XSS 防护：Markdown 渲染结果经 DOMPurify 消毒。
- 工具调用日志不记录敏感 Header 值。

### 网络安全

- 生产环境应强制 HTTPS。
- Docker 部署时数据库和 Redis 端口不应直接暴露到公网。
- CORS 配置应限制允许的来源域名。
- SSRF 防护：工具 HTTP 请求拦截内网地址（127.0.0.1、10.x、172.16-31.x、192.168.x），防止服务端请求伪造。

## v3.0 新增架构

### 多 Agent 协作架构

v3.0 引入主 Agent 调度子 Agent 的多智能体协作模式，支持复杂问题的分解与协同回答。

**架构设计**

- 主 Agent 负责理解用户意图，将复杂问题拆解为子任务。
- 主 Agent 通过 LLM 输出 `<call_agent>` 标签触发子 Agent 调用。
- 子 Agent 执行完毕后，结果回传主 Agent 进行整合。
- 递归调用深度限制为 **3 层**，防止无限递归和资源耗尽。

**调用流程图**

```text
用户输入
   │
   ▼
主 Agent LLM 推理
   │
   ▼
解析 <call_agent> 标签
   │
   ├─ 无标签 → 直接生成回答
   │
   ▼
调用子 Agent（递归，最多 3 层）
   │
   ▼
子 Agent 执行（检索/工具/LLM）
   │
   ▼
结果整合回主 Agent
   │
   ▼
生成最终回答
```

**深度限制说明**

| 层级 | 角色 | 说明 |
|------|------|------|
| 0 | 主 Agent | 接收用户输入，调度子 Agent |
| 1 | 一级子 Agent | 执行主 Agent 分配的子任务 |
| 2 | 二级子 Agent | 执行一级子 Agent 的进一步分解任务 |
| 3 | 三级子 Agent | 最大递归深度，禁止再向下调用 |

### 工具调用链架构

v3.0 支持工具串行编排，多个工具按顺序执行，前一个工具的输出可作为下一个工具的输入。

**串行编排执行流程**

```text
用户输入
   │
   ▼
工具链编排（在 LLM 生成前执行）
   │
   ├─ 工具 A 执行 → output_A
   │
   ├─ 工具 B 执行（input = $prev_output / $user_input）→ output_B
   │
   └─ 工具 C 执行（input = $prev_output）→ output_C
   │
   ▼
所有工具结果 + 用户问题 → LLM 生成回答
```

**input_mapping 映射机制**

工具链中每个工具节点的输入通过 `input_mapping` 配置：

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `$user_input` | 用户原始输入 | 查询订单号 12345 |
| `$prev_output` | 上一个工具的输出 | 订单详情 JSON |

**设计要点**

- 工具链在 LLM 生成前执行，确保工具结果作为上下文参与模型推理。
- 任意工具执行失败会中断链路并返回错误信息，避免脏数据污染后续步骤。
- 工具链配置存储在智能体配置中，运行时按顺序加载执行。

### 工作流引擎架构

v3.0 引入可视化工作流引擎，支持通过节点编排构建复杂业务流程。

**6 种节点类型**

| 节点类型 | 说明 | 典型用途 |
|----------|------|----------|
| `start` | 流程起点 | 接收用户输入 |
| `agent` | 智能体节点 | 调用指定智能体执行任务 |
| `tool` | 工具节点 | 调用配置的工具 |
| `knowledge` | 知识库节点 | 检索指定知识库 |
| `condition` | 条件分支节点 | 根据表达式选择分支 |
| `end` | 流程终点 | 输出最终结果 |

**执行机制**

- 拓扑排序确定节点执行顺序，保证依赖关系正确。
- 条件分支节点根据表达式求值结果选择后续路径。
- 节点间通过上下文传递数据，支持引用上游节点输出。

**节点执行流程图**

```text
start
  │
  ▼
agent / tool / knowledge
  │
  ▼
condition ──┬─ 条件 A → 节点 X
            │
            └─ 条件 B → 节点 Y
                          │
                          ▼
                         end
```

### 向量数据库切换架构

v3.0 抽象向量存储层，支持在 pgvector 和 Qdrant 之间切换。

**VectorStoreBackend 抽象接口**

```text
上层应用（RAG Pipeline / 检索服务）
            │
            ▼
   VectorStoreBackend 抽象接口
   ├─ add_documents()
   ├─ search()
   └─ delete()
            │
   ┌────────┴────────┐
   ▼                 ▼
pgvector 后端     Qdrant 后端
（PostgreSQL 扩展） （REST API）
```

**后端实现**

| 后端 | 实现方式 | 适用场景 |
|------|----------|----------|
| pgvector | PostgreSQL 扩展，SQL 查询 | 已有 PostgreSQL 环境，中小规模数据 |
| Qdrant | REST API 调用 | 大规模向量检索，独立向量服务 |

**配置切换**

通过环境变量 `VECTOR_DB_BACKEND` 切换：

```bash
# 使用 pgvector（默认）
VECTOR_DB_BACKEND=pgvector

# 使用 Qdrant
VECTOR_DB_BACKEND=qdrant
QDRANT_URL=http://localhost:6333
```

### WebSocket 通信架构

v3.0 在原有 SSE 基础上新增 WebSocket 通信模式，支持双向实时通信。

**SSE vs WebSocket 对比**

| 特性 | SSE | WebSocket |
|------|-----|-----------|
| 通信方向 | 单向（服务端→客户端） | 双向 |
| 协议 | HTTP | WebSocket |
| 自动重连 | 浏览器内置 | 需手动实现 |
| 心跳保活 | 不需要 | 需要 |
| 适用场景 | 简单流式回答 | 实时交互、文件上传进度 |

**WebSocket 事件转换流程**

```text
客户端
  │
  ├─ 发送 chat_message 事件
  │
  ▼
WebSocket 服务端
  │
  ├─ 解析事件 → 转换为内部运行请求
  │
  ├─ 调用智能体运行时
  │
  ├─ 流式接收 LLM 输出
  │
  ▼
客户端
  ├─ 接收 token 事件（逐字输出）
  ├─ 接收 done 事件（回答完成）
  └─ 接收 error 事件（异常）
```

**自动重连和心跳保活**

- 客户端检测连接断开后自动重连，指数退避避免雪崩。
- 服务端定时发送心跳包（ping），客户端响应 pong 维持连接。
- 重连后恢复会话上下文，保证对话连续性。

### RAG 调优架构

v3.0 支持按知识库维度独立配置检索参数，精细化调优检索效果。

**参数配置维度**

| 参数 | 说明 | 调优影响 |
|------|------|----------|
| `chunk_size` | 文档切块大小 | 大小影响召回粒度 |
| `overlap` | 切块重叠字符数 | 避免语义截断 |
| `top_k` | 返回结果数量 | 多少影响上下文丰富度 |
| `score_threshold` | 相似度阈值 | 高低过滤低相关结果 |
| 向量权重 | 向量检索权重 | 与关键词权重搭配 |
| 关键词权重 | 关键词检索权重 | 与向量权重搭配 |

**调优流程**

```text
配置检索参数
   │
   ▼
检索测试（输入问题）
   │
   ▼
验证检索效果（查看召回片段）
   │
   ├─ 效果不佳 → 调整参数 → 重新测试
   │
   ▼
保存配置（绑定到知识库）
```

**设计要点**

- 调优参数与知识库一一绑定，不同知识库可独立配置。
- 检索测试实时反映参数变化效果，所见即所得。
- 配置持久化到数据库，运行时自动加载对应知识库的调优参数。
