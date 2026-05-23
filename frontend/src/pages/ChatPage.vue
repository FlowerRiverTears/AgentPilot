<template>
  <div class="two-column">
    <n-card title="运行任务">
      <n-alert v-if="!agentOptions.length" type="warning" class="run-tip">
        还没有智能体。请先到“智能体”页面创建一个。Token 请在“模型配置”页面填写。
      </n-alert>
      <n-alert v-else-if="store.modelConfig && !store.modelConfig.api_key_set" type="info" class="run-tip">
        当前未配置 API Token。可以先用开发模式回答，也可以到“模型配置”页面填写自己的 Token。
      </n-alert>
      <n-form label-placement="top">
        <n-form-item label="智能体">
          <n-select v-model:value="agentId" :options="agentOptions" placeholder="选择智能体" />
        </n-form-item>
        <n-form-item label="任务">
          <n-input
            v-model:value="input"
            type="textarea"
            :autosize="{ minRows: 8, maxRows: 12 }"
            placeholder="请输入任务或问题"
          />
        </n-form-item>
        <n-button type="primary" block :loading="loading" :disabled="!agentOptions.length" @click="run">
          开始执行
        </n-button>
      </n-form>
    </n-card>
    <div class="page-grid">
      <n-card title="回答">
        <n-empty v-if="!store.lastRun" description="还没有执行结果" />
        <div v-else class="answer-block">
          <div class="answer-meta">
            <span>状态：{{ store.lastRun.status }}</span>
            <span>模型：{{ store.lastRun.model }}</span>
          </div>
          <div class="answer-render">
            <template v-for="(part, index) in answerParts" :key="index">
              <pre v-if="part.type === 'code'" class="answer-code"><code>{{ part.content }}</code></pre>
              <div v-else class="answer-text">{{ part.content }}</div>
            </template>
          </div>
        </div>
      </n-card>
      <n-card title="执行过程">
        <n-timeline v-if="store.lastRun">
          <n-timeline-item
            v-for="step in store.lastRun.steps"
            :key="step.name"
            type="success"
            :title="step.name"
            :content="step.detail"
          />
        </n-timeline>
        <n-empty v-else description="还没有执行记录" />
      </n-card>
      <n-card title="引用来源">
        <n-list v-if="store.lastRun?.citations.length">
          <n-list-item v-for="chunk in store.lastRun.citations" :key="chunk.chunk_id">
            <n-thing :title="chunk.source" :description="`相似度：${chunk.score.toFixed(3)}`">
              <div class="citation-snippet">
                {{ snippet(chunk.content) }}
              </div>
            </n-thing>
          </n-list-item>
        </n-list>
        <n-empty v-else description="暂无引用" />
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useMessage } from "naive-ui";

import { useWorkspaceStore } from "../stores/workspace";
import { cleanAnswerText, parseAnswerParts } from "../utils/answerFormat";

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
    message.warning("智能体列表已刷新，请重新选择后再执行");
    return;
  }

  if (!agentId.value || !input.value.trim()) {
    message.warning("请选择智能体并输入任务");
    return;
  }
  loading.value = true;
  try {
    await store.runAgent(agentId.value, input.value);
    message.success("任务已执行完成");
  } catch (error) {
    await store.loadAgents();
    if (!store.agents.length) {
      agentId.value = null;
      message.error("智能体不存在或已丢失。当前第一版使用内存存储，后端重启后需要重新创建智能体。");
      return;
    }
    message.error("任务执行失败，请检查智能体、模型配置或后端服务");
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

const answerText = computed(() => cleanAnswerText(store.lastRun?.answer ?? ""));
const answerParts = computed(() => parseAnswerParts(store.lastRun?.answer ?? ""));
</script>
