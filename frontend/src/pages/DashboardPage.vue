<template>
  <div class="page-grid">
    <n-page-header>
      <template #title>
        {{ t('dashboard.title') }}
        <n-tag type="success" size="small" round class="version-tag">v{{ version }}</n-tag>
      </template>
      <template #subtitle>
        AgentPilot v{{ version }} {{ t('dashboard.subtitle') }}
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

    <n-card :title="t('dashboard.progressTitle')">
      <n-steps :current="16" status="finish">
        <n-step :title="t('dashboard.steps.agentMgmt')" :description="t('dashboard.steps.agentMgmtDesc')" />
        <n-step :title="t('dashboard.steps.runHistory')" :description="t('dashboard.steps.runHistoryDesc')" />
        <n-step :title="t('dashboard.steps.toolSystem')" :description="t('dashboard.steps.toolSystemDesc')" />
        <n-step :title="t('dashboard.steps.streamingRAG')" :description="t('dashboard.steps.streamingRAGDesc')" />
        <n-step :title="t('dashboard.steps.multimodal')" :description="t('dashboard.steps.multimodalDesc')" />
        <n-step :title="t('dashboard.steps.auth')" :description="t('dashboard.steps.authDesc')" />
        <n-step :title="t('dashboard.steps.portalEnhance')" :description="t('dashboard.steps.portalEnhanceDesc')" />
        <n-step :title="t('dashboard.steps.conversationEnhance')" :description="t('dashboard.steps.conversationEnhanceDesc')" />
        <n-step :title="t('dashboard.steps.multiAgent')" :description="t('dashboard.steps.multiAgentDesc')" />
        <n-step :title="t('dashboard.steps.toolChainOrchestration')" :description="t('dashboard.steps.toolChainOrchestrationDesc')" />
        <n-step :title="t('dashboard.steps.evalStep')" :description="t('dashboard.steps.evalStepDesc')" />
        <n-step :title="t('dashboard.steps.fileUploadStep')" :description="t('dashboard.steps.fileUploadStepDesc')" />
        <n-step :title="t('dashboard.steps.workflowStep')" :description="t('dashboard.steps.workflowStepDesc')" />
        <n-step :title="t('dashboard.steps.ragTuningStep')" :description="t('dashboard.steps.ragTuningStepDesc')" />
        <n-step :title="t('dashboard.steps.websocketStep')" :description="t('dashboard.steps.websocketStepDesc')" />
        <n-step :title="t('dashboard.steps.vectorDBStep')" :description="t('dashboard.steps.vectorDBStepDesc')" />
      </n-steps>
    </n-card>

    <div class="dashboard-grid">
      <n-card :title="t('dashboard.quickAccess')">
        <div class="dashboard-actions">
          <n-button type="primary" @click="router.push('/guide')">{{ t('dashboard.viewGuide') }}</n-button>
          <n-button secondary @click="router.push('/agents')">{{ t('dashboard.createAgent') }}</n-button>
          <n-button secondary @click="router.push('/knowledge')">{{ t('dashboard.manageKB') }}</n-button>
          <n-button secondary @click="router.push('/tools')">{{ t('dashboard.toolMgmt') }}</n-button>
          <n-button secondary @click="router.push('/settings/model')">{{ t('dashboard.configModel') }}</n-button>
          <n-button secondary @click="router.push('/runs')">{{ t('dashboard.runHistory') }}</n-button>
          <n-button secondary @click="router.push('/eval')">{{ t('nav.eval') }}</n-button>
          <n-button secondary @click="router.push('/workflows')">{{ t('nav.workflows') }}</n-button>
          <n-button secondary @click="router.push('/rag-tuning')">{{ t('nav.ragTuning') }}</n-button>
          <n-button secondary @click="router.push('/portal')">{{ t('common.goPortal') }}</n-button>
        </div>
      </n-card>

      <n-card :title="t('dashboard.completed')">
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
import { useI18n } from "vue-i18n";

import { api } from "../api/client";

const router = useRouter();
const { t } = useI18n();

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
  eval_datasets: number;
  eval_results: number;
  workflows: number;
  workflow_runs: number;
}

const stats = ref<StatsData | null>(null);
const version = ref("3.0.0");

const modules = computed(() => [
  {
    title: t('dashboard.modules.auth'),
    desc: stats.value?.auth_enabled ? t('dashboard.modules.authDescOn') : t('dashboard.modules.authDescOff'),
    online: stats.value?.auth_enabled ?? true
  },
  {
    title: t('dashboard.modules.observability'),
    desc: t('dashboard.modules.observabilityDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.rag'),
    desc: t('dashboard.modules.ragDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.streaming'),
    desc: t('dashboard.modules.streamingDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.ocr'),
    desc: stats.value?.ocr_enabled ? t('dashboard.modules.ocrDescOn') : t('dashboard.modules.ocrDescOff'),
    online: stats.value?.ocr_enabled ?? false
  },
  {
    title: t('dashboard.modules.multimodal'),
    desc: t('dashboard.modules.multimodalDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.conversation'),
    desc: t('dashboard.modules.conversationDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.feedback'),
    desc: t('dashboard.modules.feedbackDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.multiAgent'),
    desc: t('dashboard.modules.multiAgentDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.toolChain'),
    desc: t('dashboard.modules.toolChainDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.eval'),
    desc: t('dashboard.modules.evalDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.fileUpload'),
    desc: t('dashboard.modules.fileUploadDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.workflow'),
    desc: t('dashboard.modules.workflowDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.ragTuning'),
    desc: t('dashboard.modules.ragTuningDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.websocket'),
    desc: t('dashboard.modules.websocketDesc'),
    online: true
  },
  {
    title: t('dashboard.modules.vectorDB'),
    desc: t('dashboard.modules.vectorDBDesc'),
    online: true
  }
]);

const metrics = computed(() => {
  const s = stats.value;
  return [
    { label: t('dashboard.metrics.agentsTotal'), value: s?.agents_total ?? "-", hint: s ? t('dashboard.metrics.published', { n: s.agents_published }) : "" },
    { label: t('dashboard.metrics.runsTotal'), value: s?.runs_total ?? "-", hint: t('dashboard.metrics.cumulative') },
    { label: t('dashboard.metrics.knowledgeBases'), value: s?.knowledge_bases ?? "-", hint: s ? t('dashboard.metrics.docsCount', { n: s.documents }) : "" },
    { label: t('dashboard.metrics.tools'), value: s?.tools ?? "-", hint: s ? t('dashboard.metrics.callsCount', { n: s.tool_calls }) : "" },
    { label: t('dashboard.metrics.conversations'), value: s?.conversations ?? "-", hint: t('dashboard.metrics.conversationsHint') },
    { label: t('dashboard.metrics.feedback'), value: s ? `${s.feedback_likes}/${s.feedback_dislikes}` : "-", hint: t('dashboard.metrics.likesDislikes') },
    { label: t('dashboard.metrics.evalDatasets'), value: s?.eval_datasets ?? "-", hint: s ? t('dashboard.metrics.evalHint', { n: s.eval_results }) : "" },
    { label: t('dashboard.metrics.workflow'), value: s?.workflows ?? "-", hint: s ? t('dashboard.metrics.workflowHint', { n: s.workflow_runs }) : "" }
  ];
});

async function loadStats() {
  try {
    const response = await api.get<StatsData>("/health/stats");
    stats.value = response.data;
    version.value = response.data.version || "3.0.0";
  } catch (error) {
    console.error(t('dashboard.loadStatsError'), error);
  }
}

onMounted(() => {
  void loadStats();
});

const completedItems = computed(() => {
  const items = (t('dashboard.completedItems') as unknown as string[]);
  return Array.isArray(items) ? items : [];
});
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
