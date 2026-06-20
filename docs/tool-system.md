# 工具系统设计

## 定位

工具用于连接实时业务系统，不应该替代知识库。

适合工具的场景：

- 订单查询
- 物流查询
- 库存查询
- 用户信息查询
- 工单创建
- 数据库查询
- 当前时间

适合知识库的场景：

- FAQ
- 产品手册
- 售后政策
- 内部制度
- 培训资料

## 当前实现

工具注册位置：

```text
backend/app/tools/registry.py
```

内置工具：

- `current_time`
- `order_lookup`

数据库持久化工具：

```text
backend/app/repositories/tools.py
```

接口：

```text
GET    /api/tools           工具列表
POST   /api/tools           创建工具
GET    /api/tools/{id}      工具详情
PUT    /api/tools/{id}      更新工具
DELETE /api/tools/{id}      删除工具
POST   /api/tools/{id}/test 工具测试
```

当前已支持：

- 工具表 `tools` 持久化存储
- HTTP 工具配置（URL、Method、Headers、Query、Body、触发关键词、超时）
- 工具 CRUD（创建、读取、更新、删除）
- 工具测试接口（发送实际 HTTP 请求，返回状态码、耗时和输出）
- Agent 绑定数据库工具
- 运行时按关键词触发工具调用
- 内置工具作为 fallback，数据库工具优先

## 工具调用日志

每次工具调用自动记录到 `tool_calls` 表：

| 字段 | 说明 |
|------|------|
| `run_id` | 关联的运行 ID |
| `tool_id` | 关联的工具 ID |
| `tool_name` | 工具名称 |
| `input` | 调用输入 |
| `output` | 调用输出 |
| `status` | 调用状态（success / failed） |
| `status_code` | HTTP 状态码 |
| `elapsed_ms` | 耗时（毫秒） |
| `error` | 错误信息 |
| `detail` | 详细信息（JSON） |

查询接口：`GET /tools/calls?limit=50`（需鉴权）

## 当前限制

- 工具管理页面已具备基础创建、编辑、删除和测试能力，后续需要优化交互体验。
- 还没有 SQL 工具。
- 还没有鉴权配置页。
- 工具配置中的 Headers 可能包含敏感信息（如 Bearer Token），当前明文存储，建议加密。

## 工具能力规划

### HTTP 工具

配置项：

- 名称
- 描述
- URL
- Method
- Headers
- Query 参数
- Body 模板
- 超时时间
- 鉴权方式

### SQL 工具

配置项：

- 名称
- 描述
- 数据源
- SQL 模板
- 参数 schema
- 只读限制
- 超时时间

### 工具测试

工具管理页应支持：

- 输入测试参数。
- 调用工具。
- 查看请求和响应。
- 查看耗时。
- 查看错误原因。

## 调用流程

1. Agent 绑定工具。
2. 用户提问。
3. 运行时判断是否需要工具。
4. 生成工具参数。
5. 调用工具。
6. 保存工具调用记录。
7. 将工具结果交给大模型生成回答。

## 安全原则

- SQL 工具默认只允许只读查询。
- HTTP 工具不应明文展示敏感 Header。
- 工具测试和调用应记录日志。
- 后台工具管理需要管理员权限。
