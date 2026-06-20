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
