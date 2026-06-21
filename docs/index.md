# AgentPilot 项目文档

> 开源 AI Agent 工作台 — 创建、编排、知识库问答、工具调用与评测平台

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [系统架构](architecture.md) | 总体架构、模块划分、数据流、安全架构 |
| [数据库设计](database.md) | 14 张表的完整定义、ER 图、安全备注 |
| [API 参考](api.md) | 全部接口定义、请求/响应格式、错误码 |
| [工具系统](tool-system.md) | 工具设计、调用流程、安全原则 |
| [智能体运行时](agent-runtime.md) | 运行流程、上下文结构、对话记忆、反馈机制 |
| [开发指南](development.md) | 环境搭建、代码规范、数据库迁移、环境变量 |
| [使用教程](user-guide.md) | 面向用户的操作指南 |
| [第二版路线（已完成）](roadmap-v2.md) | P0-P6 完成报告和 v3 远期规划 |
| [第三版路线（已完成）](roadmap-v3.md) | P7-P9 多 Agent 协作、工具链编排、智能体评测、文件上传、工作流画布、RAG 调优、WebSocket、向量数据库切换 |
| [第四版路线（规划中）](roadmap-v4.md) | P9-P15 安全体系、可观测性、测试、性能优化、工作流画布、MCP、企业级特性 |
| [开发问题记录](development-issues.md) | 30+ 个开发问题的原因和解决方案 |
| [用户权限体系设计](用户权限体系设计.md) | RBAC 设计、权限矩阵、实施步骤 |
| [文档体系修改建议](文档体系修改建议.md) | 企业级文档改进建议（部分已修复） |

---

## 项目概述

AgentPilot 是一个面向开发者和团队的开源 AI Agent 工作台。用户可以在图形化界面中创建智能体、配置工具、接入知识库、编排多步骤任务，并在后台看到 Agent 的执行轨迹、工具调用、检索证据和成本信息。

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+、FastAPI、Pydantic、SQLAlchemy 2.x |
| 前端 | Vue 3、TypeScript、Vite、Pinia、Naive UI |
| 数据层 | PostgreSQL + pgvector、Redis、MinIO |
| 部署 | Docker Compose |
| LLM | OpenAI-compatible API、Ollama |

### 快速开始

```bash
cd deploy
docker compose up --build
```

| 服务 | 地址 |
|------|------|
| 后台工作台 | http://localhost:5173 |
| 前台体验 | http://localhost:5173/portal |
| 接口文档 | http://localhost:8000/docs |

详见 [开发指南](development.md)。
