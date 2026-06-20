<template>
  <div class="page-grid">
    <n-page-header>
      <template #title>
        总览
        <n-tag type="success" size="small" round class="version-tag">v{{ version }}</n-tag>
      </template>
      <template #subtitle>
        AgentPilot v{{ version }} 第二版全部功能已完成 · 后台制造智能体，前台体验智能体
      </template>
    </n-page-header>

    <!-- 模块上线状态 -->
    <div class="status-banner">
      <n-card v-for="mod in modules" :key="mod.title" size="small" class="status-card">
        <div class="status-card-head">
          <span class="status-dot" :class="mod.online ? 'online' : 'offline'" />
          <strong>{{ mod.title }}</strong>
        </div>
        <p class="muted">{{ mod.desc }}</p>
      </n-card>
    </div>

    <!-- 真实数据指标 -->
    <div class="metrics">
      <n-card v-for="m in metrics" :key="m.label" class="metric-card">
        <div class="metric-value">{{ m.value }}</div>
        <div class="metric-label">{{ m.label }}</div>
        <div v-if="m.hint" class="muted">{{ m.hint }}</div>
      </n-card>
    </div>

    <n-card title="第二版进度（已完成）">
      <n-steps :current="8" status="finish">
        <n-step title="智能体管理" description="编辑、发布、下线、复制、软删除" />
        <n-step title="运行历史" description="Run 列表、详情、失败重试" />
        <n-step title="工具系统" description="HTTP 工具创建、测试、运行时调用、调用日志" />
        <n-step title="流式输出与检索增强" description="SSE、Embedding、pgvector、PDF 解析、多轮上下文" />
        <n-step title="多模态检索" description="图片提取、多模态 Embedding、跨模态检索、MinIO 图片存储" />
        <n-step title="基础权限" description="JWT 认证、角色权限、后台鉴权、前台匿名、Token 管理" />
        <n-step title="前台体验增强" description="回答重试、错误提示、Mermaid 图表渲染" />
        <n-step title="对话与智能体增强" description="会话管理、上下文压缩、多知识库、导入导出、反馈、模板库" />
      </n-steps>
    </n-card>

    <div class="dashboard-grid">
      <n-card title="常用入口">
        <div class="dashboard-actions">
          <n-button type="primary" @click="router.push('/guide')">查看使用教程</n-button>
          <n-button secondary @click="router.push('/agents')">创建智能体</n-button>
          <n-button secondary @click="router.push('/knowledge')">管理知识库</n-button>
          <n-button secondary @click="router.push('/tools')">工具管理</n-button>
          <n-button secondary @click="router.push('/settings/model')">配置模型</n-button>
          <n-button secondary @click="router.push('/runs')">运行历史</n-button>
          <n-button secondary @click="router.push('/portal')">进入前台</n-button>
        </div>
      </n-card>

      <n-card title="第二版已完成">
        <n-list>
          <n-list-item v-for="item in completedItems" :key="item">
            <n-thing :title="item" />
          </n-list-item>
        </n-list>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { api } from "../api/client";

const router = useRouter();

interface StatsData {
  app: string;
  version: string;
  environment: string;
  auth_enabled: boolean;
  ocr_enabled: boolean;
  status: string;
  agents_total: number;
  agents_published: number;
  runs_total: number;
  knowledge_bases: number;
  documents: number;
  tools: number;
  tool_calls: number;
  conversations: number;
  feedback_likes: number;
  feedback_dislikes: number;
}

const stats = ref<StatsData | null>(null);
const version = ref("3.0.0");

const modules = computed(() => [
  {
    title: "鉴权",
    desc: stats.value?.auth_enabled ? "JWT + bcrypt，角色权限控制" : "鉴权已关闭",
    online: stats.value?.auth_enabled ?? true
  },
  {
    title: "可观测性",
    desc: "Trace ID、运行历史、工具调用日志",
    online: true
  },
  {
    title: "RAG 检索",
    desc: "pgvector 向量检索 + 多知识库合并",
    online: true
  },
  {
    title: "流式输出",
    desc: "SSE 实时回答 + 上下文压缩",
    online: true
  },
  {
    title: "OCR 识别",
    desc: stats.value?.ocr_enabled ? "Tesseract 扫描件 PDF" : "OCR 已关闭",
    online: stats.value?.ocr_enabled ?? false
  },
  {
    title: "多模态",
    desc: "图片提取 + 跨模态检索 + MinIO",
    online: true
  },
  {
    title: "对话记忆",
    desc: "会话管理 + 上下文压缩 + 搜索",
    online: true
  },
  {
    title: "反馈系统",
    desc: "点赞/点踩 + 反馈统计",
    online: true
  }
]);

const metrics = computed(() => {
  const s = stats.value;
  return [
    { label: "智能体总数", value: s?.agents_total ?? "-", hint: s ? `已发布 ${s.agents_published} 个` : "" },
    { label: "运行总数", value: s?.runs_total ?? "-", hint: "累计执行次数" },
    { label: "知识库", value: s?.knowledge_bases ?? "-", hint: s ? `${s.documents} 篇文档` : "" },
    { label: "工具", value: s?.tools ?? "-", hint: s ? `${s.tool_calls} 次调用` : "" },
    { label: "会话", value: s?.conversations ?? "-", hint: "前台对话记录" },
    { label: "反馈", value: s ? `${s.feedback_likes}/${s.feedback_dislikes}` : "-", hint: "赞 / 踩" }
  ];
});

async function loadStats() {
  try {
    const response = await api.get<StatsData>("/health/stats");
    stats.value = response.data;
    version.value = response.data.version || "3.0.0";
  } catch (error) {
    console.error("加载统计数据失败", error);
  }
}

onMounted(() => {
  void loadStats();
});

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
  "知识库文档级管理和单文档删除",
  "前台回答重试（重新生成回答）",
  "流式错误明确提示（区分网络/模型/超时错误）",
  "Mermaid.js 图表渲染（流程图、时序图、甘特图）",
  "OCR 支持扫描件 PDF（Tesseract + pdf2image）",
  "对话记忆管理（历史会话列表、删除、搜索）",
  "上下文压缩（滑动窗口 + 摘要，Token 超阈值自动压缩）",
  "多知识库绑定（一个智能体绑定多个知识库，检索合并结果）",
  "智能体导入/导出（JSON 格式跨环境迁移）",
  "回答反馈（点赞/点踩记录到数据库）",
  "Prompt 模板库（预置模板一键套用）"
];
</script>

<style scoped>
.version-tag {
  margin-left: 8px;
  vertical-align: middle;
}

.status-banner {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.status-card {
  text-align: left;
}

.status-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.online {
  background: #18a058;
  box-shadow: 0 0 6px #18a058;
}

.status-dot.offline {
  background: #d03050;
}

.status-card .muted {
  font-size: 12px;
  margin: 0;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.metric-card {
  text-align: center;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-strong);
  line-height: 1.2;
}

.metric-label {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-muted);
}

.metric-card .muted {
  font-size: 11px;
  margin-top: 2px;
}

.dashboard-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
