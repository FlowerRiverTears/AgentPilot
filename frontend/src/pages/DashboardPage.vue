<template>
  <div class="page-grid">
    <n-page-header title="总览" subtitle="AgentPilot 第一版控制台" />

    <div class="metrics">
      <n-card title="模型">
        <div class="metric-value">已接入</div>
        <div class="muted">多模型配置 / 连通性测试</div>
      </n-card>
      <n-card title="知识库">
        <div class="metric-value">已完成</div>
        <div class="muted">上传、切块、检索、引用</div>
      </n-card>
      <n-card title="智能体">
        <div class="metric-value">已完成</div>
        <div class="muted">创建、绑定、运行、追踪</div>
      </n-card>
      <n-card title="前台">
        <div class="metric-value">已上线</div>
        <div class="muted">独立体验页 / 用户对话</div>
      </n-card>
    </div>

    <n-card title="第一版验收状态">
      <n-steps :current="4" status="finish">
        <n-step title="项目骨架" description="FastAPI + Vue + Docker Compose" />
        <n-step title="知识库检索" description="创建知识库、上传文档、检索测试、引用来源" />
        <n-step title="智能体运行" description="创建智能体、绑定模型/知识库/工具、执行任务" />
        <n-step title="前台体验" description="独立前台、回答格式、深色亮色、使用教程" />
      </n-steps>
    </n-card>

    <div class="dashboard-grid">
      <n-card title="已实现链路">
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
  "Docker Compose 一键启动和说明文档"
];
</script>
