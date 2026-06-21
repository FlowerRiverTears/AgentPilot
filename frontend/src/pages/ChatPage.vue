<template>
  <div class="two-column">
    <n-card :title="t('chat.title')">
      <n-alert v-if="!agentOptions.length" type="warning" class="run-tip">
        {{ t('chat.noAgents') }}
      </n-alert>
      <n-alert v-else-if="store.modelConfig && !store.modelConfig.api_key_set" type="info" class="run-tip">
        {{ t('chat.noToken') }}
      </n-alert>
      <n-form label-placement="top">
        <n-form-item :label="t('chat.agent')">
          <n-select v-model:value="agentId" :options="agentOptions" :placeholder="t('chat.selectAgent')" />
        </n-form-item>
        <n-form-item :label="t('chat.task')">
          <n-input
            v-model:value="input"
            type="textarea"
            :autosize="{ minRows: 8, maxRows: 12 }"
            :placeholder="t('chat.taskPlaceholder')"
          />
        </n-form-item>
        <n-button type="primary" block :loading="loading" :disabled="!agentOptions.length" @click="run">
          {{ t('chat.startExecution') }}
        </n-button>
      </n-form>
    </n-card>
    <div class="page-grid">
      <n-card :title="t('chat.answer')">
        <n-empty v-if="!store.lastRun" :description="t('chat.noResult')" />
        <div v-else class="answer-block">
          <div class="answer-meta">
            <span>{{ t('chat.statusLabel') }}{{ store.lastRun.status }}</span>
            <span>{{ t('chat.modelLabel') }}{{ store.lastRun.model }}</span>
          </div>
          <div class="answer-render">
            <template v-for="(part, index) in answerParts" :key="index">
              <MermaidBlock v-if="part.type === 'mermaid'" :source="part.content" />
              <pre v-else-if="part.type === 'code'" class="answer-code"><code>{{ part.content }}</code></pre>
              <div v-else class="answer-text markdown-body" v-html="part.html || part.content" />
            </template>
          </div>
        </div>
      </n-card>
      <n-card :title="t('chat.execution')">
        <n-timeline v-if="store.lastRun">
          <n-timeline-item
            v-for="step in store.lastRun.steps"
            :key="step.name"
            type="success"
            :title="step.name"
            :content="step.detail"
          />
        </n-timeline>
        <n-empty v-else :description="t('chat.noExecution')" />
      </n-card>
      <n-card :title="t('chat.citations')">
        <n-list v-if="store.lastRun?.citations.length">
          <n-list-item v-for="chunk in store.lastRun.citations" :key="chunk.chunk_id">
            <n-thing :title="chunk.source" :description="`${t('common.similarity')}${chunk.score.toFixed(3)}`">
              <div v-if="chunk.content_type === 'image' && chunk.image_url" class="citation-image">
                <img :src="minioImageUrl(chunk.image_url)" :alt="chunk.content" class="citation-img" />
                <div class="citation-snippet">
                  {{ snippet(chunk.content) }}
                </div>
              </div>
              <div v-else class="citation-snippet">
                {{ snippet(chunk.content) }}
              </div>
            </n-thing>
          </n-list-item>
        </n-list>
        <n-empty v-else :description="t('chat.noCitations')" />
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useMessage } from "naive-ui";
import { useI18n } from "vue-i18n";

import { useWorkspaceStore } from "../stores/workspace";
import { cleanAnswerText, parseAnswerParts } from "../utils/answerFormat";
import MermaidBlock from "../components/MermaidBlock.vue";

const { t } = useI18n();
const message = useMessage();
const store = useWorkspaceStore();
const agentId = ref<string | null>(null);
const input = ref("");
const loading = ref(false);

const agentOptions = computed(() => store.agents.map((item) => ({ label: item.name, value: item.id })));

async function run() {
  await store.loadAgents();
  if (agentId.value && !store.agents.some((agent) => agent.id === agentId.value)) {
    agentId.value = store.agents[0]?.id ?? null;
    message.warning(t('chat.agentListRefreshed'));
    return;
  }

  if (!agentId.value || !input.value.trim()) {
    message.warning(t('chat.selectAgentAndTask'));
    return;
  }
  loading.value = true;
  try {
    await store.runAgent(agentId.value, input.value);
    message.success(t('chat.taskCompleted'));
  } catch (error) {
    await store.loadAgents();
    if (!store.agents.length) {
      agentId.value = null;
      message.error(t('chat.agentLost'));
      return;
    }
    message.error(t('chat.taskFailed'));
    console.error(error);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await Promise.all([store.reloadForRunPage(), store.loadModelConfig()]);
  agentId.value = store.agents[0]?.id ?? null;
});

function snippet(text: string, limit = 180) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) {
    return normalized;
  }
  return `${normalized.slice(0, limit)}...`;
}

function minioImageUrl(path: string) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  const base = window.location.port === "5173" ? "http://localhost:19000" : "http://localhost:9000";
  return `${base}${path}`;
}

const answerText = computed(() => cleanAnswerText(store.lastRun?.answer ?? ""));
const answerParts = computed(() => parseAnswerParts(store.lastRun?.answer ?? ""));
</script>
