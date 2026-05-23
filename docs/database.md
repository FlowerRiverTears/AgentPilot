# 数据库设计

当前数据库使用 PostgreSQL，向量字段预留 pgvector 方向。

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

文档切片表。

字段：

- `id`：UUID 主键
- `document_id`：文档 ID
- `content`：切片内容
- `source`：来源文件
- `embedding`：向量数据
- `created_at`
- `updated_at`

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

## 第二版计划新增表

### users

- `id`
- `username`
- `password_hash`
- `role`
- `status`
- `created_at`
- `updated_at`

### tools

- `id`
- `name`
- `type`
- `description`
- `config`
- `enabled`
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
