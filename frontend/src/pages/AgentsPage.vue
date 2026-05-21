<template>
  <div class="two-column">
    <n-card title="创建智能体">
      <n-form label-placement="top">
        <n-form-item label="名称">
          <n-input v-model:value="form.name" placeholder="客服助手" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="form.description" placeholder="基于知识库回答客户问题" />
        </n-form-item>
        <n-form-item label="模型">
          <n-input v-model:value="form.model" placeholder="qwen2.5:7b" />
        </n-form-item>
        <n-form-item label="系统提示词">
          <n-input
            v-model:value="form.system_prompt"
            type="textarea"
            :autosize="{ minRows: 5, maxRows: 8 }"
          />
        </n-form-item>
        <n-form-item label="知识库">
          <n-select
            v-model:value="form.knowledge_base_ids"
            multiple
            :options="kbOptions"
            placeholder="选择知识库"
          />
        </n-form-item>
        <n-button type="primary" block @click="submit">创建</n-button>
      </n-form>
    </n-card>

    <n-card title="智能体列表">
      <n-data-table :columns="columns" :data="store.agents" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive } from "vue";
import { NTag, useMessage } from "naive-ui";

import { useWorkspaceStore } from "../stores/workspace";

const message = useMessage();
const store = useWorkspaceStore();

const form = reactive({
  name: "",
  description: "",
  model: "",
  system_prompt: "你是一个企业 AI 智能体。回答必须清晰、准确，并在使用知识库时说明来源。",
  knowledge_base_ids: [] as string[]
});

const kbOptions = computed(() =>
  store.knowledgeBases.map((item) => ({ label: item.name, value: item.id }))
);

const columns = [
  { title: "名称", key: "name" },
  { title: "模型", key: "model" },
  { title: "描述", key: "description" },
  {
    title: "状态",
    key: "status",
    render: (row: { status: string }) => h(NTag, { type: "info" }, { default: () => row.status })
  }
];

async function submit() {
  await store.createAgent({
    ...form,
    tool_ids: []
  });
  message.success("智能体已创建");
  form.name = "";
  form.description = "";
}

onMounted(async () => {
  await Promise.all([store.loadAgents(), store.loadKnowledgeBases()]);
});
</script>
