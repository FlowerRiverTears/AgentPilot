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
        <n-form-item label="模型配置">
          <n-select
            v-model:value="form.model_config_id"
            :options="modelConfigOptions"
            placeholder="选择已配置的大模型"
          />
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
        <n-form-item label="应用工具">
          <n-select
            v-model:value="form.tool_ids"
            multiple
            :options="toolOptions"
            placeholder="选择需要调用的应用工具"
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
import { NTag, useMessage, type DataTableColumns } from "naive-ui";

import type { Agent } from "../api/types";
import { useWorkspaceStore } from "../stores/workspace";

const message = useMessage();
const store = useWorkspaceStore();

const form = reactive({
  name: "",
  description: "",
  model_config_id: null as string | null,
  system_prompt: "你是一个企业 AI 智能体。回答必须清晰、准确，并在使用知识库时说明来源。",
  knowledge_base_ids: [] as string[],
  tool_ids: [] as string[]
});

const kbOptions = computed(() =>
  store.knowledgeBases.map((item) => ({ label: item.name, value: item.id }))
);

const modelConfigOptions = computed(() =>
  store.modelConfigs.map((item) => ({
    label: `${item.name} / ${item.default_model}${item.is_default ? " / 默认" : ""}`,
    value: item.id
  }))
);

const toolOptions = computed(() =>
  store.tools.map((item) => ({
    label: `${item.name} / ${item.description}`,
    value: item.id
  }))
);

const columns: DataTableColumns<Agent> = [
  { title: "名称", key: "name" },
  {
    title: "模型配置",
    key: "model_config_id",
    render(row) {
      return modelConfigName(row.model_config_id);
    }
  },
  { title: "描述", key: "description" },
  {
    title: "状态",
    key: "status",
    render: (row) => h(NTag, { type: "info" }, { default: () => row.status })
  }
];

function modelConfigName(configId?: string | null) {
  if (!configId) {
    return "默认配置";
  }
  const config = store.modelConfigs.find((item) => item.id === configId);
  return config ? `${config.name} / ${config.default_model}` : "配置已删除";
}

async function submit() {
  if (!form.name.trim()) {
    message.warning("请填写智能体名称");
    return;
  }
  if (!form.model_config_id) {
    message.warning("请选择模型配置");
    return;
  }

  await store.createAgent({
    ...form,
    name: form.name.trim(),
    description: form.description.trim(),
    model: undefined
  });
  message.success("智能体已创建");
  form.name = "";
  form.description = "";
  form.tool_ids = [];
}

onMounted(async () => {
  await Promise.all([
    store.loadAgents(),
    store.loadKnowledgeBases(),
    store.loadModelConfigs(),
    store.loadTools()
  ]);
  form.model_config_id =
    store.modelConfigs.find((item) => item.is_default)?.id ?? store.modelConfigs[0]?.id ?? null;
});
</script>
