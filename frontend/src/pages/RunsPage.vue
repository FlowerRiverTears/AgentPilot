<template>
  <div class="page-grid">
    <n-page-header :title="t('runs.title')" :subtitle="t('runs.subtitle')" />
    <n-card>
      <n-data-table :columns="columns" :data="store.runs" :bordered="false" :loading="loading" />
    </n-card>

    <n-modal v-model:show="showDetail" preset="card" :title="t('runs.runDetails')" style="max-width: 800px">
      <template v-if="detail">
        <n-descriptions bordered :column="2" label-placement="left" class="run-detail-desc">
          <n-descriptions-item :label="t('runs.agent')">{{ detail.agent_name }}</n-descriptions-item>
          <n-descriptions-item :label="t('runs.model')">{{ detail.model }}</n-descriptions-item>
          <n-descriptions-item :label="t('common.status')">
            <n-tag :type="detail.status === 'failed' ? 'error' : 'success'" size="small">
              {{ detail.status === 'failed' ? t('runs.failed') : t('runs.success') }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item :label="t('runs.duration')">{{ detail.duration_ms ? `${detail.duration_ms}ms` : "-" }}</n-descriptions-item>
          <n-descriptions-item :label="t('runs.createdAt')" :span="2">{{ detail.created_at }}</n-descriptions-item>
        </n-descriptions>

        <n-divider>{{ t('runs.input') }}</n-divider>
        <div class="run-detail-text">{{ detail.input }}</div>

        <n-divider>{{ t('runs.answer') }}</n-divider>
        <div class="answer-render">
          <template v-for="(part, index) in answerParts" :key="index">
            <MermaidBlock v-if="part.type === 'mermaid'" :source="part.content" />
            <pre v-else-if="part.type === 'code'" class="answer-code"><code>{{ part.content }}</code></pre>
            <div v-else class="answer-text markdown-body" v-html="part.html || part.content" />
          </template>
        </div>

        <n-divider v-if="detail.steps?.length">{{ t('runs.execution') }}</n-divider>
        <n-timeline v-if="detail.steps?.length">
          <n-timeline-item
            v-for="step in detail.steps"
            :key="step.name"
            :type="step.status === 'completed' ? 'success' : 'error'"
            :title="step.name"
            :content="step.detail"
          />
        </n-timeline>

        <n-divider v-if="detail.status === 'failed' || detail.usage?.error">{{ t('runs.failureReason') }}</n-divider>
        <n-alert v-if="detail.status === 'failed' || detail.usage?.error" type="error" :bordered="false">
          {{ detail.usage?.error || t('runs.failureHint') }}
        </n-alert>

        <n-divider v-if="detail.tool_results?.length">{{ t('runs.toolCalls') }}</n-divider>
        <n-list v-if="detail.tool_results?.length" bordered>
          <n-list-item v-for="(tool, idx) in detail.tool_results" :key="idx">
            <n-thing :title="tool.name">
              <template #header-extra>
                <n-tag size="small" :type="tool.content && !tool.content.startsWith('Error') ? 'success' : 'error'">
                  {{ tool.content && !tool.content.startsWith('Error') ? t('runs.success') : t('runs.failed') }}
                </n-tag>
              </template>
              <div class="tool-result-content">{{ tool.content }}</div>
            </n-thing>
          </n-list-item>
        </n-list>

        <n-divider v-if="detail.citations?.length">{{ t('runs.citations') }}</n-divider>
        <n-list v-if="detail.citations?.length">
          <n-list-item v-for="chunk in detail.citations" :key="chunk.chunk_id">
            <n-thing :title="chunk.source" :description="`${t('common.similarity')}${chunk.score.toFixed(3)}`">
              <div v-if="chunk.content_type === 'image' && chunk.image_url" class="citation-image">
                <img :src="minioImageUrl(chunk.image_url)" :alt="chunk.content" class="citation-img" />
                <div class="citation-snippet">{{ snippet(chunk.content) }}</div>
              </div>
              <div v-else class="citation-snippet">{{ snippet(chunk.content) }}</div>
            </n-thing>
          </n-list-item>
        </n-list>

        <n-divider />
        <div class="run-detail-actions">
          <n-button type="primary" :loading="retrying" @click="handleRetry">{{ t('runs.reExecute') }}</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from "vue";
import { NButton, useMessage, type DataTableColumns } from "naive-ui";
import { useI18n } from "vue-i18n";

import type { RunDetail, RunSummary } from "../api/types";
import { useWorkspaceStore } from "../stores/workspace";
import { useUiStore } from "../stores/ui";
import { parseAnswerParts } from "../utils/answerFormat";
import MermaidBlock from "../components/MermaidBlock.vue";

const { t } = useI18n();
const message = useMessage();
const store = useWorkspaceStore();
const ui = useUiStore();
const loading = ref(false);
const showDetail = ref(false);
const detail = ref<RunDetail | null>(null);
const retrying = ref(false);

const columns: DataTableColumns<RunSummary> = [
  {
    title: t('runs.time'),
    key: "created_at",
    width: 180,
    render(row) {
      try {
        return new Date(row.created_at).toLocaleString(ui.locale === 'zh' ? 'zh-CN' : 'en-US');
      } catch {
        return row.created_at;
      }
    }
  },
  { title: t('runs.agent'), key: "agent_name", width: 140 },
  {
    title: t('runs.input'),
    key: "input",
    ellipsis: { tooltip: true }
  },
  { title: t('runs.model'), key: "model", width: 160 },
  {
    title: t('runs.duration'),
    key: "duration_ms",
    width: 100,
    render(row) {
      return row.duration_ms ? `${row.duration_ms}ms` : "-";
    }
  },
  {
    title: t('common.actions'),
    key: "actions",
    width: 80,
    render(row) {
      return h(NButton, { size: "small", secondary: true, onClick: () => viewDetail(row.run_id) }, { default: () => t('runs.details') });
    }
  }
];

async function viewDetail(runId: string) {
  try {
    detail.value = await store.getRun(runId);
    showDetail.value = true;
  } catch {
    message.error(t('runs.getDetailFailed'));
  }
}

async function handleRetry() {
  if (!detail.value) return;
  retrying.value = true;
  try {
    await store.retryRun(detail.value.run_id);
    message.success(t('runs.retrySuccess'));
    showDetail.value = false;
    await store.loadRuns();
  } catch {
    message.error(t('runs.retryFailed'));
  } finally {
    retrying.value = false;
  }
}

const answerParts = computed(() => parseAnswerParts(detail.value?.answer ?? ""));

function snippet(text: string, limit = 180) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit)}...`;
}

function minioImageUrl(path: string) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  const base = window.location.port === "5173" ? "http://localhost:19000" : "http://localhost:9000";
  return `${base}${path}`;
}

onMounted(async () => {
  loading.value = true;
  try {
    await store.loadRuns();
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.tool-result-content {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.5;
  padding: 8px;
  background: var(--n-color-embedded, #f5f5f5);
  border-radius: 4px;
}

.run-detail-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
