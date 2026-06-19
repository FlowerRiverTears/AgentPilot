<template>
  <div class="page-grid">
    <n-page-header title="总览" subtitle="AgentPilot v0.2.0 鉴权与可观测性已上线" />

    <div class="metrics">
      <n-card title="第二版总进度">
        <div class="metric-value">78% 完成</div>
        <div class="muted">鉴权、工具日志、失败重试、文档管理已接入</div>
      </n-card>
      <n-card title="智能体管理">
        <div class="metric-value">完成</div>
        <div class="muted">编辑、发布、复制、删除</div>
      </n-card>
      <n-card title="运行历史">
        <div class="metric-value">完成</div>
        <div class="muted">列表、详情、引用、步骤、失败重试</div>
      </n-card>
      <n-card title="基础权限">
        <div class="metric-value">完成</div>
        <div class="muted">管理员登录、后台鉴权、Token 管理</div>
      </n-card>
    </div>

    <n-card title="第二版进度">
      <n-steps :current="6" status="finish">
        <n-step title="智能体管理" description="编辑、发布、下线、复制、软删除" />
        <n-step title="运行历史" description="Run 列表、详情、失败重试" />
        <n-step title="工具系统" description="HTTP 工具创建、测试、运行时调用、调用日志" />
        <n-step title="流式输出与检索增强" description="SSE、Embedding、pgvector、PDF 解析、多轮上下文" />
        <n-step title="多模态检索" description="图片提取、多模态 Embedding、跨模态检索、MinIO 图片存储" />
        <n-step title="基础权限" description="管理员登录、后台鉴权、前台匿名、Token 过期和退出" />
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
  "刷新服务台后保留会话和上下文",
  "PDF 上传解析为可检索文本，避免二进制乱码切块",
  "检索结果过滤乱码、重复片段和低相关上下文",
  "PDF 图片提取并独立切块向量化",
  "图片存入 MinIO 对象存储",
  "多模态 Embedding（CLIP 等统一向量空间模型）",
  "文本和图片在同一向量空间中检索",
  "跨模态检索：文本查图片、图片查文本",
  "检索结果区分文本块和图片块，图片块展示缩略图",
  "引用来源支持图片引用展示",
  "管理员登录（JWT + bcrypt 密码哈希）",
  "后台 API 鉴权保护，前台匿名访问",
  "Token 过期处理和退出登录",
  "工具调用日志记录和查询",
  "运行失败原因展示和重试入口",
  "知识库文档级管理和单文档删除"
];
</script>
