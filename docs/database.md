# 数据库设计

当前数据库使用 PostgreSQL，向量字段预留 pgvector 方向。支持多模态 Embedding（文本 + 图片统一向量空间）。

## agents

智能体表。

字段：

- `id`：UUID 主键
- `name`：名称
- `description`：描述
- `system_prompt`：系统提示词
- `model`：模型名，可为空
- `status`：状态
- `config`：JSON 配置
- `created_at`
- `updated_at`

`config` 当前存储：

```json
{
  "model_config_id": "...",
  "knowledge_base_ids": ["..."],
  "tool_ids": ["current_time"]
}
```

## agent_runs

运行记录表。

字段：

- `id`：UUID 主键
- `agent_id`：智能体 ID
- `status`：运行状态
- `input`：用户输入
- `output`：模型输出
- `trace_id`：追踪 ID
- `usage`：JSON 使用信息
- `created_at`
- `updated_at`

## run_steps

运行步骤表。

字段：

- `id`：UUID 主键
- `run_id`：运行 ID
- `name`：步骤名
- `status`：步骤状态
- `detail`：JSON 详情
- `created_at`
- `updated_at`

## knowledge_bases

知识库表。

字段：

- `id`：UUID 主键
- `name`：名称
- `description`：描述
- `created_at`
- `updated_at`

## documents

文档表。

字段：

- `id`：UUID 主键
- `knowledge_base_id`：知识库 ID
- `filename`：文件名
- `status`：状态
- `created_at`
- `updated_at`

## document_chunks

文档切片表。支持多模态：文本块和图片块统一存储，通过 `content_type` 区分。

字段：

- `id`：UUID 主键
- `document_id`：文档 ID
- `content`：切片内容（文本块为文字内容，图片块为图片描述或占位文本）
- `content_type`：内容类型，`text`（文本块）或 `image`（图片块）
- `source`：来源文件
- `image_url`：图片存储路径（仅图片块有值，指向 MinIO 中的图片文件）
- `embedding`：多模态向量数据（文本和图片在同一向量空间，支持跨模态检索）
- `created_at`
- `updated_at`

多模态说明：

- 文本块：`content_type = "text"`，`content` 存储文本内容，`image_url` 为空，`embedding` 由文本 Embedding 模型生成。
- 图片块：`content_type = "image"`，`content` 存储图片描述（可选），`image_url` 指向 MinIO 中的图片文件，`embedding` 由多模态 Embedding 模型（如 CLIP）的图片编码器生成。
- 跨模态检索：文本查询和图片查询的向量在同一空间，可以直接用余弦相似度匹配。

## model_configs

模型配置表。

字段：

- `id`：UUID 主键
- `name`：配置名
- `base_url`：OpenAI-compatible Base URL
- `api_key`：API Key
- `default_model`：默认模型名
- `is_default`：是否默认
- `created_at`
- `updated_at`

## tools

工具表。

字段：

- `id`：UUID 主键
- `name`：名称（唯一）
- `type`：类型，当前支持 `http`
- `description`：描述
- `config`：JSON 配置（URL、Method、Headers、Query、Body、触发关键词、超时等）
- `enabled`：是否启用
- `created_at`
- `updated_at`

`config` 当前存储（HTTP 工具）：

```json
{
  "url": "http://host.docker.internal:8000/api/mock/order",
  "method": "GET",
  "trigger_keywords": ["订单", "物流"],
  "headers": {},
  "query": {},
  "body": {},
  "timeout_seconds": 20
}
```

## 第二版计划新增表

### users

- `id`
- `username`
- `password_hash`
- `role`
- `status`
- `created_at`
- `updated_at`

### tool_calls

- `id`
- `run_id`
- `tool_id`
- `input`
- `output`
- `status`
- `elapsed_ms`
- `created_at`

### agent_versions

- `id`
- `agent_id`
- `version`
- `snapshot`
- `published`
- `created_at`
