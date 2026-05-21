<template>
  <div class="two-column">
    <n-card title="运行任务">
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
        <n-button type="primary" block :loading="loading" @click="run">开始执行</n-button>
      </n-form>
    </n-card>
    <div class="page-grid">
      <n-card title="回答">
        <n-empty v-if="!store.lastRun" description="还没有执行结果" />
        <div v-else>{{ store.lastRun.answer }}</div>
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

const message = useMessage();
const store = useWorkspaceStore();
const agentId = ref<string | null>(null);
const input = ref("");
const loading = ref(false);

const agentOptions = computed(() => store.agents.map((item) => ({ label: item.name, value: item.id })));

async function run() {
  if (!agentId.value || !input.value.trim()) {
    message.warning("请选择智能体并输入任务");
    return;
  }
  loading.value = true;
  try {
    await store.runAgent(agentId.value, input.value);
  } finally {
    loading.value = false;
  }
}

onMounted(() => store.loadAgents());

function snippet(text: string, limit = 180) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) {
    return normalized;
  }
  return `${normalized.slice(0, limit)}...`;
}
</script>
