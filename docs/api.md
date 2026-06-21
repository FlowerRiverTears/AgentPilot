# API 说明

后端默认地址：

```text
http://localhost:8000/api
```

## 统一错误响应

所有接口错误时返回统一格式：

```json
{
  "detail": "错误描述信息"
}
```

常见 HTTP 状态码：

| 状态码 | 含义 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 无效 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 422 | 请求体验证失败 |
| 500 | 服务器内部错误 |

## Health

### GET `/health`

检查服务状态。

返回：

```json
{
  "status": "ok",
  "app": "AgentPilot",
  "version": "3.0.0",
  "trace_id": "..."
}
```

## 智能体

### GET `/agents`

获取智能体列表。

### GET `/agents/published`

获取已发布智能体列表。前台体验页只使用这个接口。

### POST `/agents`

创建智能体。

请求：

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

### GET `/agents/{agent_id}`

获取单个智能体详情。

### PUT `/agents/{agent_id}`

更新智能体配置。

### DELETE `/agents/{agent_id}`

软删除智能体。

### POST `/agents/{agent_id}/publish`

发布智能体。发布后前台可见。

### POST `/agents/{agent_id}/unpublish`

下线智能体。下线后前台不可见。

### POST `/agents/{agent_id}/duplicate`

复制智能体，复制出的智能体为草稿状态。

## 知识库

### GET `/knowledge-bases`

获取知识库列表。

### POST `/knowledge-bases`

创建知识库。

请求：

```json
{
  "name": "产品手册",
  "description": "产品说明和 FAQ"
}
```

### DELETE `/knowledge-bases/{kb_id}`

删除知识库。

### POST `/knowledge-bases/{kb_id}/documents`

上传文档。

请求类型：`multipart/form-data`

字段：

- `file`

### POST `/knowledge-bases/{kb_id}/retrieve-test`

检索测试。

请求：

```json
{
  "query": "如何申请售后？",
  "top_k": 5
}
```

### GET `/knowledge-bases/sample-documents`

获取示例文档列表。返回可用于导入的示例文档。

### POST `/knowledge-bases/{kb_id}/sample-documents/{document_id}`

将示例文档导入到指定知识库。

## Mock 接口

Mock 接口提供模拟数据，用于工具测试和演示。

### GET `/mock/order`

返回模拟订单数据。

### GET `/mock/inventory`

返回模拟库存数据。

### GET `/mock/weather`

返回模拟天气数据。

## 模型配置

### GET `/settings/model`

获取默认模型配置。返回当前标记为默认的模型配置。

### PUT `/settings/model`

更新默认模型配置。如果没有默认配置则自动创建。

### GET `/settings/models`

获取模型配置列表。

### POST `/settings/models`

创建模型配置。

请求：

```json
{
  "name": "minimax",
  "base_url": "https://api.minimax.io/v1",
  "api_key": "...",
  "default_model": "MiniMax-M2.7",
  "is_default": true
}
```

### PUT `/settings/models/{config_id}`

更新模型配置。

### POST `/settings/models/{config_id}/default`

设置默认模型配置。

### POST `/settings/models/{config_id}/test`

测试模型配置。

### DELETE `/settings/models/{config_id}`

删除模型配置。

## 工具

### GET `/tools`

获取工具列表。返回数据库中所有已创建的工具，包含内置工具和用户自建的 HTTP 工具。

### POST `/tools`

创建工具。

请求：

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

### GET `/tools/{tool_id}`

获取单个工具详情。

### PUT `/tools/{tool_id}`

更新工具配置。支持部分更新，未传字段保持原值。

### DELETE `/tools/{tool_id}`

删除工具。

### POST `/tools/{tool_id}/test`

测试工具。发送实际 HTTP 请求并返回结果。

请求：

```json
{
  "input": {}
}
```

返回：

```json
{
  "ok": true,
  "status_code": 200,
  "elapsed_ms": 128,
  "output": { ... },
  "error": ""
}
```

## 运行

### POST `/runs`

执行智能体。

请求：

```json
{
  "agent_id": "...",
  "input": "我的订单 10086 发货了吗？"
}
```

返回：

```json
{
  "run_id": "...",
  "agent_id": "...",
  "status": "completed",
  "model": "...",
  "answer": "...",
  "citations": [],
  "steps": []
}
```

### POST `/runs/stream`

流式运行接口，使用 SSE 逐 token 输出。

### GET `/runs`

获取运行历史列表。

返回包含：

- `run_id`
- `agent_id`
- `agent_name`
- `status`
- `input`
- `model`
- `trace_id`
- `created_at`

### GET `/runs/{run_id}`

获取单次运行详情。

返回包含：

- 输入
- 回答
- 引用来源
- 执行步骤
- 模型
- 状态
- Trace ID

## 认证

### POST `/auth/login`

管理员登录。

请求：

```json
{ "username": "admin", "password": "admin123" }
```

返回：

```json
{ "access_token": "...", "token_type": "bearer", "username": "admin", "role": "admin" }
```

### POST `/auth/logout`

退出登录（前端清除 Token）。

### GET `/auth/me`

获取当前用户信息（需鉴权）。

## 工具调用日志

### GET `/tools/calls`

查询最近的工具调用日志（需鉴权）。

查询参数：`limit`（默认 50）

## 文档管理

### GET `/knowledge-bases/{kb_id}/documents`

列出知识库下的文档（需鉴权）。

### DELETE `/knowledge-bases/{kb_id}/documents/{doc_id}`

删除单个文档及其关联切片（需鉴权）。

## 跨模态检索

### POST `/knowledge-bases/{kb_id}/retrieve-by-image`

跨模态图片检索。

请求类型：`multipart/form-data`

字段：

- `file`（图片文件）
- `top_k`（可选，默认5）

## 运行重试

### POST `/runs/{run_id}/retry`

根据历史 Run 重新执行（需鉴权）。

## 反馈

### POST `/feedback`

提交回答反馈（支持匿名提交）。

请求：

```json
{
  "run_id": "...",
  "agent_id": "...",
  "rating": "like",
  "comment": ""
}
```

`rating` 取值：`like`（点赞）或 `dislike`（点踩）。`run_id` 和 `agent_id` 至少填一个。

### GET `/feedback`

获取反馈列表（需鉴权）。

查询参数：`agent_id`（可选，按智能体过滤）

### GET `/feedback/stats`

获取反馈统计（需鉴权）。

返回每个智能体的点赞/点踩数量。

## 对话记忆

### GET `/conversations`

获取对话列表（可选鉴权）。

查询参数：`agent_id`（可选，按智能体过滤）

### GET `/conversations/search`

搜索对话（可选鉴权）。

查询参数：`q`（搜索关键词）

### GET `/conversations/{conversation_id}`

获取单个对话详情（可选鉴权）。

### POST `/conversations`

创建或更新对话（可选鉴权）。

请求：

```json
{
  "agent_id": "...",
  "session_id": "...",
  "title": "会话标题",
  "messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
  "summary": "",
  "summary_to_turn": 0
}
```

### DELETE `/conversations/{conversation_id}`

删除对话（可选鉴权）。

## 智能体导入导出

### POST `/agents/import`

导入智能体（需鉴权）。

请求：与创建智能体格式相同。

### GET `/agents/{agent_id}/export`

导出智能体配置为 JSON（需鉴权）。

返回包含智能体完整配置和 `exported_at` 时间戳。

## 评测系统

### POST `/eval/datasets`

创建评测数据集（需鉴权）。

### GET `/eval/datasets`

列出评测数据集（需鉴权）。

### GET `/eval/datasets/{dataset_id}`

获取数据集详情（需鉴权）。

### DELETE `/eval/datasets/{dataset_id}`

删除数据集（需鉴权）。

### POST `/eval/datasets/{dataset_id}/run`

执行评测（需鉴权）。

### GET `/eval/results`

列出评测结果（需鉴权）。

### GET `/eval/results/{result_id}`

获取评测结果详情（需鉴权）。

## 文件上传

### POST `/files/upload`

上传文件（PDF/图片/TXT，最大 10MB，需鉴权）。

请求：`multipart/form-data`

- `file`：文件内容

响应：

```json
{
  "filename": "example.pdf",
  "content": "提取的文本内容",
  "char_count": 1234
}
```

## v3.0 新增 API

v3.0 版本新增会话管理、反馈、文件上传、智能体评测、工作流、RAG 调优、WebSocket 实时通信及健康检查增强等 API。以下为各接口详细说明。

### 会话管理 API

#### GET `/conversations`

获取会话列表，支持按关键词搜索。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| search | string | 否 | 搜索关键词，匹配会话标题或摘要 |

响应示例：

```json
[
  {
    "id": "conv-001",
    "session_id": "sess-abc123",
    "title": "产品咨询",
    "summary": "用户询问了产品功能",
    "created_at": "2026-06-21T10:00:00",
    "updated_at": "2026-06-21T10:05:00"
  }
]
```

#### GET `/conversations/{id}`

获取单个会话详情。

路径参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| id | UUID | 会话 ID |

响应示例：

```json
{
  "id": "conv-001",
  "session_id": "sess-abc123",
  "messages": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "您好，有什么可以帮您？"}
  ],
  "summary": "用户问候",
  "created_at": "2026-06-21T10:00:00",
  "updated_at": "2026-06-21T10:05:00"
}
```

#### POST `/conversations`

创建会话。

请求 Body：

```json
{
  "agent_id": "...",
  "session_id": "sess-abc123",
  "title": "产品咨询",
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "summary": ""
}
```

响应示例：

```json
{
  "id": "conv-001",
  "session_id": "sess-abc123",
  "title": "产品咨询",
  "created_at": "2026-06-21T10:00:00"
}
```

#### DELETE `/conversations/{id}`

删除会话。

路径参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| id | UUID | 会话 ID |

响应示例：

```json
{
  "detail": "已删除"
}
```

### 反馈 API

#### POST `/feedback`

提交回答反馈（支持匿名提交）。

请求 Body：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| run_id | UUID | 否* | 关联运行记录 |
| agent_id | UUID | 否* | 关联智能体 |
| rating | string | 是 | `like` 或 `dislike` |
| comment | string | 否 | 反馈评论 |

> *`run_id` 和 `agent_id` 至少填一个。

请求示例：

```json
{
  "run_id": "...",
  "agent_id": "...",
  "rating": "like",
  "comment": "回答很准确"
}
```

响应示例：

```json
{
  "id": "fb-001",
  "rating": "like",
  "created_at": "2026-06-21T10:00:00"
}
```

#### GET `/feedback`

获取反馈列表（需鉴权）。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agent_id | UUID | 否 | 按智能体过滤 |

响应示例：

```json
[
  {
    "id": "fb-001",
    "run_id": "...",
    "agent_id": "...",
    "rating": "like",
    "comment": "回答很准确",
    "created_at": "2026-06-21T10:00:00"
  }
]
```

#### GET `/feedback/stats`

获取反馈统计（需鉴权），返回赞/踩数量。

响应示例：

```json
{
  "total": 100,
  "like": 85,
  "dislike": 15,
  "by_agent": [
    {"agent_id": "...", "agent_name": "客服助手", "like": 50, "dislike": 5}
  ]
}
```

### 文件上传 API

#### POST `/files/upload`

上传文件并提取文本内容（需鉴权）。

请求类型：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 文件内容 |

支持类型：PDF、TXT、MD、图片（PNG/JPG）
大小限制：10MB

响应示例：

```json
{
  "file_id": "file-001",
  "filename": "example.pdf",
  "content_type": "application/pdf",
  "text_content": "提取的文本内容...",
  "char_count": 1234,
  "message": "文件上传成功"
}
```

### 智能体评测 API

#### GET `/eval/datasets`

获取评测数据集列表（需鉴权）。

响应示例：

```json
[
  {
    "id": "ds-001",
    "name": "客服评测集",
    "description": "客服场景测试",
    "agent_id": "...",
    "cases": [
      {"question": "如何退货？", "expected_keywords": ["退货", "7天"]}
    ],
    "created_at": "2026-06-21T10:00:00"
  }
]
```

#### POST `/eval/datasets`

创建评测数据集（需鉴权）。

请求 Body：

```json
{
  "name": "客服评测集",
  "description": "客服场景测试",
  "agent_id": "...",
  "cases": [
    {"question": "如何退货？", "expected_keywords": ["退货", "7天"]},
    {"question": "保修期多久？", "expected_keywords": ["保修", "1年"]}
  ]
}
```

响应示例：

```json
{
  "id": "ds-001",
  "name": "客服评测集",
  "description": "客服场景测试",
  "agent_id": "...",
  "cases": [...],
  "created_at": "2026-06-21T10:00:00"
}
```

#### GET `/eval/datasets/{id}`

获取数据集详情（需鉴权）。

路径参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| id | UUID | 数据集 ID |

#### DELETE `/eval/datasets/{id}`

删除数据集（需鉴权）。

#### POST `/eval/datasets/{id}/run`

触发评测执行（需鉴权）。

路径参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| id | UUID | 数据集 ID |

响应示例：

```json
{
  "id": "res-001",
  "dataset_id": "ds-001",
  "agent_id": "...",
  "status": "running",
  "created_at": "2026-06-21T10:00:00"
}
```

#### GET `/eval/results`

获取评测结果列表（需鉴权）。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| dataset_id | UUID | 否 | 按数据集过滤 |

#### GET `/eval/results/{id}`

获取评测结果详情（需鉴权）。

响应示例：

```json
{
  "id": "res-001",
  "dataset_id": "ds-001",
  "agent_id": "...",
  "status": "completed",
  "total_cases": 10,
  "passed_cases": 8,
  "accuracy": 0.8,
  "avg_duration_ms": 1200,
  "details": [
    {
      "question": "如何退货？",
      "answer": "...",
      "expected_keywords": ["退货", "7天"],
      "matched_keywords": ["退货"],
      "passed": true,
      "duration_ms": 1100
    }
  ],
  "created_at": "2026-06-21T10:00:00"
}
```

### 工作流 API

#### GET `/workflows`

获取工作流列表。

响应示例：

```json
[
  {
    "id": "wf-001",
    "name": "客服处理流程",
    "description": "客户问题分类处理",
    "status": "published",
    "created_at": "2026-06-21T10:00:00",
    "updated_at": "2026-06-21T10:00:00"
  }
]
```

#### POST `/workflows`

创建工作流。

请求 Body：

```json
{
  "name": "客服处理流程",
  "description": "客户问题分类处理",
  "nodes": [
    {"id": "n1", "type": "input", "label": "用户输入", "config": {}},
    {"id": "n2", "type": "agent", "label": "客服智能体", "config": {"agent_id": "..."}}
  ],
  "edges": [
    {"source": "n1", "target": "n2"}
  ]
}
```

响应示例：

```json
{
  "id": "wf-001",
  "name": "客服处理流程",
  "description": "客户问题分类处理",
  "nodes": [...],
  "edges": [...],
  "status": "draft",
  "created_at": "2026-06-21T10:00:00"
}
```

#### GET `/workflows/{id}`

获取工作流详情。

路径参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| id | UUID | 工作流 ID |

#### PUT `/workflows/{id}`

更新工作流。请求 Body 与创建相同，所有字段可选。

#### DELETE `/workflows/{id}`

删除工作流。

#### POST `/workflows/{id}/publish`

发布工作流，发布后状态变为 `published`。

响应示例：

```json
{
  "id": "wf-001",
  "status": "published",
  "updated_at": "2026-06-21T10:05:00"
}
```

#### POST `/workflows/run`

执行工作流。

请求 Body：

```json
{
  "workflow_id": "wf-001",
  "input": "我的订单 10086 发货了吗？"
}
```

响应示例：

```json
{
  "id": "run-001",
  "workflow_id": "wf-001",
  "status": "completed",
  "output": "您的订单已发货...",
  "duration_ms": 2500,
  "created_at": "2026-06-21T10:00:00"
}
```

#### GET `/workflows/runs`

获取工作流执行记录列表。

响应示例：

```json
[
  {
    "id": "run-001",
    "workflow_id": "wf-001",
    "status": "completed",
    "input": "...",
    "output": "...",
    "duration_ms": 2500,
    "created_at": "2026-06-21T10:00:00"
  }
]
```

#### GET `/workflows/runs/{id}`

获取执行记录详情，包含各节点执行结果。

响应示例：

```json
{
  "id": "run-001",
  "workflow_id": "wf-001",
  "status": "completed",
  "input": "...",
  "output": "...",
  "node_results": [
    {"node_id": "n1", "status": "completed", "output": "...", "duration_ms": 100},
    {"node_id": "n2", "status": "completed", "output": "...", "duration_ms": 2400}
  ],
  "duration_ms": 2500,
  "created_at": "2026-06-21T10:00:00"
}
```

### RAG 调优 API

#### GET `/rag-tuning/configs`

获取所有知识库的 RAG 配置。

响应示例：

```json
[
  {
    "id": "rc-001",
    "knowledge_base_id": "...",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "top_k": 5,
    "score_threshold": 0.3,
    "retrieval_weight_vector": 0.7,
    "retrieval_weight_lexical": 0.3
  }
]
```

#### GET `/rag-tuning/configs/{kb_id}`

获取指定知识库的 RAG 配置。

路径参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| kb_id | UUID | 知识库 ID |

#### PUT `/rag-tuning/configs/{kb_id}`

更新指定知识库的 RAG 配置。

请求 Body：

```json
{
  "chunk_size": 800,
  "chunk_overlap": 100,
  "top_k": 10,
  "score_threshold": 0.5,
  "retrieval_weight_vector": 0.8,
  "retrieval_weight_lexical": 0.2
}
```

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| chunk_size | integer | 切块大小 | 500 |
| chunk_overlap | integer | 切块重叠 | 50 |
| top_k | integer | 检索数量 | 5 |
| score_threshold | float | 相似度阈值 | 0.3 |
| retrieval_weight_vector | float | 向量权重 | 0.7 |
| retrieval_weight_lexical | float | 关键词权重 | 0.3 |

#### POST `/rag-tuning/test`

检索测试，按当前配置进行检索并返回结果。

请求 Body：

```json
{
  "knowledge_base_id": "...",
  "query": "如何申请售后？",
  "top_k": 5,
  "score_threshold": 0.3
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| knowledge_base_id | UUID | 是 | 知识库 ID |
| query | string | 是 | 查询文本 |
| top_k | integer | 否 | 检索数量，覆盖配置 |
| score_threshold | float | 否 | 相似度阈值，覆盖配置 |

响应示例：

```json
{
  "query": "如何申请售后？",
  "results": [
    {
      "content": "售后申请流程...",
      "score": 0.85,
      "document_id": "...",
      "source": "after_sales.pdf"
    }
  ],
  "total": 1
}
```

### WebSocket API

#### WS `/ws/chat`

WebSocket 聊天端点，支持流式输出和实时步骤推送。

连接地址：

```text
ws://localhost:8000/ws/chat
```

客户端发送消息格式：

```json
{
  "agent_id": "...",
  "input": "你好",
  "messages": [
    {"role": "user", "content": "之前的对话..."}
  ],
  "file_content": ""
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agent_id | UUID | 是 | 智能体 ID |
| input | string | 是 | 用户输入 |
| messages | array | 否 | 历史消息列表 |
| file_content | string | 否 | 上传文件提取的文本内容 |

服务端推送事件类型：

| 事件 | 说明 |
|------|------|
| steps | 执行步骤更新 |
| citations | 引用来源 |
| token | 流式输出的 token |
| error | 错误信息 |
| done | 执行完成 |

`steps` 事件示例：

```json
{
  "event": "steps",
  "data": {
    "name": "retrieval",
    "status": "completed",
    "detail": "检索到 3 条相关文档"
  }
}
```

`token` 事件示例：

```json
{
  "event": "token",
  "data": {"content": "您"}
}
```

`done` 事件示例：

```json
{
  "event": "done",
  "data": {
    "answer": "完整回答内容",
    "citations": [],
    "run_id": "..."
  }
}
```

`error` 事件示例：

```json
{
  "event": "error",
  "data": {"message": "智能体执行失败"}
}
```

### 健康检查增强

#### GET `/health/stats`

获取系统总览统计信息，包含版本号、鉴权状态及各资源数量。

响应示例：

```json
{
  "status": "ok",
  "app": "AgentPilot",
  "version": "3.0.0",
  "auth_enabled": true,
  "counts": {
    "agents": 10,
    "knowledge_bases": 5,
    "documents": 120,
    "tools": 8,
    "conversations": 350,
    "workflows": 3,
    "eval_datasets": 2
  }
}
```
