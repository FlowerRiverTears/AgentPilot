<template>
  <div class="page-grid">
    <n-page-header title="总览" subtitle="AgentPilot 第二版推进中" />

    <div class="metrics">
      <n-card title="第二版总进度">
        <div class="metric-value">核心完成</div>
        <div class="muted">流式输出、RAG、多轮对话已接入</div>
      </n-card>
      <n-card title="智能体管理">
        <div class="metric-value">完成</div>
        <div class="muted">编辑、发布、复制、删除</div>
      </n-card>
      <n-card title="运行历史">
        <div class="metric-value">完成</div>
        <div class="muted">列表、详情、引用、步骤</div>
      </n-card>
      <n-card title="检索增强">
        <div class="metric-value">完成</div>
        <div class="muted">PDF 解析、Embedding、pgvector 检索</div>
      </n-card>
    </div>

    <n-card title="第二版进度">
      <n-steps :current="4" status="finish">
        <n-step title="智能体管理" description="编辑、发布、下线、复制、软删除" />
        <n-step title="运行历史" description="Run 列表和详情页" />
        <n-step title="工具系统" description="HTTP 工具创建、测试和运行时调用" />
        <n-step title="流式输出与检索增强" description="SSE、真实 Embedding、pgvector、PDF 解析、多轮上下文" />
      </n-steps>
    </n-card>

    <div class="dashboard-grid">
      <n-card title="第二版已完成">
        <n-list>
          <n-list-item v-for="item in completedItems" :key="item">
            <n-thing :title="item" />
          </n-list-item>
        </n-list>
      </n-card>

      <n-card title="常用入口">
        <div class="dashboard-actions">
          <n-button type="primary" @click="router.push('/guide')">查看使用教程</n-button>
          <n-button secondary @click="router.push('/settings/model')">配置模型</n-button>
          <n-button secondary @click="router.push('/knowledge')">管理知识库</n-button>
          <n-button secondary @click="router.push('/agents')">创建智能体</n-button>
          <n-button secondary @click="router.push('/tools')">工具管理</n-button>
          <n-button secondary @click="router.push('/runs')">运行历史</n-button>
          <n-button secondary @click="router.push('/portal')">进入前台</n-button>
        </div>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

const completedItems = [
  "创建知识库",
  "上传文档",
  "文档切块并写入数据库",
  "输入问题做检索测试",
  "展示文档来源、命中文档片段和相似度",
  "创建智能体",
  "智能体绑定模型、知识库和应用工具",
  "执行任务并展示回答、引用来源和执行轨迹",
  "独立前台体验页",
  "Docker Compose 一键启动和说明文档",
  "智能体编辑、发布、下线、复制、软删除",
  "前台只展示已发布智能体",
  "运行历史列表和详情页",
  "HTTP 工具创建、测试和运行时调用",
  "SSE 流式输出（前台实时显示回答）",
  "真实 Embedding 服务接入（Ollama bge-m3）",
  "pgvector 数据库端向量检索",
  "多轮对话支持",
  "切换智能体时保留前台会话上下文",
  "PDF 上传解析为可检索文本，避免二进制乱码切块"
];
</script>
