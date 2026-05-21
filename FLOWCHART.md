# Agent 项目流程图

## 1. 用户使用流程

```mermaid
flowchart TD
    A[用户打开前端 Vue 页面] --> B[登录系统]
    B --> C[选择或创建一个 Agent]
    C --> D[选择知识库和工具]
    D --> E[输入任务或问题]
    E --> F[后端创建一次 Agent Run]
    F --> G[Agent 分析任务]
    G --> H{是否需要查资料}
    H -- 是 --> I[RAG 检索知识库]
    I --> J[找到相关文档片段]
    H -- 否 --> K[直接进入推理]
    J --> K[调用 LLM 生成下一步]
    K --> L{是否需要调用工具}
    L -- 是 --> M[调用工具: 搜索/API/SQL/代码分析]
    M --> N[工具返回结果]
    N --> K
    L -- 否 --> O[生成最终回答或报告]
    O --> P[保存执行记录、引用、成本、日志]
    P --> Q[前端展示答案和执行轨迹]
```

## 2. 系统架构流程

```mermaid
flowchart LR
    U[用户] --> FE[Vue 3 前端]
    FE --> API[FastAPI 后端]

    API --> AUTH[登录和权限模块]
    API --> AGENT[Agent Runtime]
    API --> KB[知识库模块]
    API --> TOOL[工具模块]
    API --> EVAL[评测模块]

    AGENT --> LLM[LLM 网关]
    AGENT --> RAG[RAG 检索流程]
    AGENT --> TOOL

    KB --> PARSE[文档解析]
    PARSE --> CHUNK[文档切块]
    CHUNK --> EMB[生成 Embedding]
    EMB --> PG[(PostgreSQL + pgvector)]

    RAG --> PG
    API --> PG
    API --> REDIS[(Redis)]
    KB --> MINIO[(MinIO 文件存储)]

    LLM --> OPENAI[OpenAI-compatible API]
    LLM --> OLLAMA[Ollama 本地模型]
    LLM --> OTHER[其他模型供应商]

    AGENT --> TRACE[执行轨迹和日志]
    TRACE --> PG
```

## 3. 一个实际例子：客服 Agent

```mermaid
sequenceDiagram
    participant User as 用户
    participant Web as Vue 前端
    participant API as FastAPI 后端
    participant Agent as 客服 Agent
    participant DB as PostgreSQL + pgvector
    participant LLM as 大模型

    User->>Web: 输入问题：怎么申请退款？
    Web->>API: 创建对话任务
    API->>Agent: 启动客服 Agent
    Agent->>DB: 检索退款相关文档
    DB-->>Agent: 返回制度片段和引用来源
    Agent->>LLM: 带着文档片段生成回答
    LLM-->>Agent: 返回回答
    Agent->>API: 保存回答、引用、token、耗时
    API-->>Web: 流式返回答案和执行过程
    Web-->>User: 展示回答和引用来源
```

## 4. 一句话理解

这个项目就是一个后台系统，用来创建和管理不同类型的 AI 助手。

用户不是直接写代码调用大模型，而是在页面里配置：

- 这个 Agent 是干什么的。
- 它能看哪些知识库。
- 它能调用哪些工具。
- 它完成任务时每一步怎么走。
- 它回答得好不好、花了多少钱、哪里失败了。

## 5. 核心技术关键词

- LLM：负责生成回答、推理、总结和工具选择。
- RAG：负责从知识库中检索资料，并把引用来源返回给用户。
- 切面：负责把鉴权、日志、审计、限流、追踪、成本统计这些能力统一挂到执行链路上。
- 向量：负责把文档和问题转成 embedding，并用相似度检索找到相关内容。

## 6. 它为什么算大型项目

它算大型项目，因为它不是一个单功能 Demo，而是一个完整平台，至少包含这些系统：

1. 前端后台系统
   - 登录、布局、表格、表单、图表、工作流画布、聊天页面。

2. 后端 API 系统
   - 用户、权限、Agent、知识库、工具、任务、评测、日志。

3. 数据库系统
   - PostgreSQL 业务表、pgvector 向量检索、Redis 缓存、MinIO 文件存储。

4. LLM 工程系统
   - 多模型接入、流式输出、token 统计、失败重试、成本统计。

5. RAG 知识库系统
   - 文件上传、解析、切块、embedding、检索、引用来源。

6. Agent 执行系统
   - 任务编排、工具调用、执行步骤、长任务、失败恢复。

7. 可观测和评测系统
   - 执行轨迹、工具调用日志、模型效果对比、评测报告。

如果只做第一版 MVP，也至少会包含：

- Vue 前端
- FastAPI 后端
- PostgreSQL + pgvector
- Redis
- 文件上传
- RAG 问答
- Agent 执行记录
- Docker Compose 一键启动

所以它可以从小版本开始做，但整体方向确实是大型项目。
