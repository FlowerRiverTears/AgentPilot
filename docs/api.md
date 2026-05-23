# API 说明

后端默认地址：

```text
http://localhost:8000/api
```

## Health

### GET `/health`

检查服务状态。

返回：

```json
{
  "status": "ok",
  "app": "AgentPilot",
  "version": "0.1.0",
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

## 模型配置

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

获取可用工具列表。

当前内置：

- `current_time`
- `order_lookup`

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

流式运行接口占位，当前仍基于完整回答拆分 token 输出。

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

## 第二版计划接口

- `POST /tools`
- `PUT /tools/{id}`
- `DELETE /tools/{id}`
- `POST /tools/{id}/test`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
