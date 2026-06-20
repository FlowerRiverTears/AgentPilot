<template>
  <div class="two-column">
    <n-card :title="editingAgentId ? '编辑智能体' : '创建智能体'">
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
        <n-form-item label="Prompt 模板">
          <n-select
            :value="promptTemplate"
            :options="promptTemplateOptions"
            placeholder="选择 Prompt 模板（可选）"
            clearable
            @update:value="applyPromptTemplate"
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
        <div class="form-actions">
          <n-button type="primary" block @click="submit">
            {{ editingAgentId ? "保存修改" : "创建" }}
          </n-button>
          <n-button v-if="editingAgentId" block secondary @click="resetForm">取消编辑</n-button>
        </div>
      </n-form>
    </n-card>

    <n-card title="智能体列表">
      <template #header-extra>
        <n-button type="primary" @click="triggerImport">导入智能体</n-button>
        <input
          ref="fileInputRef"
          type="file"
          accept=".json"
          style="display: none"
          @change="handleImport"
        />
      </template>
      <n-data-table :columns="columns" :data="store.agents" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from "vue";
import { NButton, NPopconfirm, NSpace, NTag, useMessage, type DataTableColumns } from "naive-ui";

import { api } from "../api/client";
import type { Agent } from "../api/types";
import { useWorkspaceStore } from "../stores/workspace";

const message = useMessage();
const store = useWorkspaceStore();
const editingAgentId = ref<string | null>(null);

// Prompt 模板预置列表
const promptTemplateOptions = [
  { label: "通用助手", value: "你是一个乐于助人的AI助手，请清晰、准确地回答用户问题。" },
  { label: "客服助手", value: "你是一个专业的客服助手。请耐心、礼貌地回答用户问题，遇到无法解决的问题请引导用户联系人工客服。" },
  { label: "代码助手", value: "你是一个专业的编程助手。请提供准确、高效的代码建议，并附上简要说明。代码需遵循最佳实践。" },
  { label: "翻译助手", value: "你是一个专业翻译助手。请将用户输入翻译为目标语言，保持原文语义和语气。如未指定目标语言，默认翻译为英文。" },
  { label: "文档总结", value: "你是一个文档总结助手。请根据提供的文档内容生成简洁的摘要，突出关键信息和要点。" },
  { label: "数据分析", value: "你是一个数据分析助手。请根据提供的数据进行分析，给出清晰的结论和建议，必要时使用表格展示。" }
];

const promptTemplate = ref<string | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

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

const statusTagType = (status: string) => {
  if (status === "published") return "success";
  if (status === "draft") return "info";
  if (status === "deleted") return "default";
  return "warning";
};

const statusLabel = (status: string) => {
  if (status === "published") return "已发布";
  if (status === "draft") return "草稿";
  return status;
};

const columns: DataTableColumns<Agent> = [
  { title: "名称", key: "name", width: 140 },
  {
    title: "模型配置",
    key: "model_config_id",
    width: 180,
    render(row) {
      return modelConfigName(row.model_config_id);
    }
  },
  { title: "描述", key: "description", ellipsis: { tooltip: true } },
  {
    title: "状态",
    key: "status",
    width: 90,
    render: (row) => h(NTag, { type: statusTagType(row.status), size: "small" }, { default: () => statusLabel(row.status) })
  },
  {
    title: "操作",
    key: "actions",
    width: 340,
    render(row) {
      const buttons = [
        h(NButton, { size: "small", secondary: true, onClick: () => startEdit(row) }, { default: () => "编辑" })
      ];
      if (row.status === "draft") {
        buttons.push(
          h(NButton, { size: "small", type: "success", secondary: true, onClick: () => handlePublish(row.id) }, { default: () => "发布" })
        );
      }
      if (row.status === "published") {
        buttons.push(
          h(NButton, { size: "small", type: "warning", secondary: true, onClick: () => handleUnpublish(row.id) }, { default: () => "下线" })
        );
      }
      buttons.push(
        h(NButton, { size: "small", secondary: true, onClick: () => handleDuplicate(row.id) }, { default: () => "复制" })
      );
      buttons.push(
        h(NButton, { size: "small", secondary: true, onClick: () => handleExport(row.id) }, { default: () => "导出" })
      );
      buttons.push(
        h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
          trigger: () => h(NButton, { size: "small", type: "error", secondary: true }, { default: () => "删除" }),
          default: () => "确认删除该智能体？"
        })
      );
      return h(NSpace, { size: 4 }, { default: () => buttons });
    }
  }
];

function modelConfigName(configId?: string | null) {
  if (!configId) return "默认配置";
  const config = store.modelConfigs.find((item) => item.id === configId);
  return config ? `${config.name} / ${config.default_model}` : "配置已删除";
}

function startEdit(agent: Agent) {
  editingAgentId.value = agent.id;
  form.name = agent.name;
  form.description = agent.description;
  form.model_config_id = agent.model_config_id ?? null;
  form.system_prompt = agent.system_prompt;
  form.knowledge_base_ids = [...agent.knowledge_base_ids];
  form.tool_ids = [...agent.tool_ids];
  // 编辑时清空模板选择，避免覆盖已有提示词
  promptTemplate.value = null;
}

function resetForm() {
  editingAgentId.value = null;
  form.name = "";
  form.description = "";
  form.model_config_id = store.modelConfigs.find((item) => item.is_default)?.id ?? store.modelConfigs[0]?.id ?? null;
  form.system_prompt = "你是一个企业 AI 智能体。回答必须清晰、准确，并在使用知识库时说明来源。";
  form.knowledge_base_ids = [];
  form.tool_ids = [];
  promptTemplate.value = null;
}

// 选择 Prompt 模板后自动填充系统提示词
function applyPromptTemplate(value: string | null) {
  promptTemplate.value = value;
  if (value) {
    form.system_prompt = value;
  }
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

  try {
    if (editingAgentId.value) {
      await store.updateAgent(editingAgentId.value, {
        name: form.name.trim(),
        description: form.description.trim(),
        system_prompt: form.system_prompt,
        model_config_id: form.model_config_id,
        knowledge_base_ids: form.knowledge_base_ids,
        tool_ids: form.tool_ids
      });
      message.success("智能体已更新");
      resetForm();
    } else {
      await store.createAgent({
        name: form.name.trim(),
        description: form.description.trim(),
        system_prompt: form.system_prompt,
        model_config_id: form.model_config_id,
        knowledge_base_ids: form.knowledge_base_ids,
        tool_ids: form.tool_ids
      });
      message.success("智能体已创建");
      form.name = "";
      form.description = "";
      form.tool_ids = [];
    }
  } catch (e: any) {
    message.error(e?.message || "操作失败，请重试");
  }
}

async function handlePublish(agentId: string) {
  try {
    await store.publishAgent(agentId);
    message.success("智能体已发布");
  } catch (e: any) {
    message.error(e?.message || "发布失败");
  }
}

async function handleUnpublish(agentId: string) {
  try {
    await store.unpublishAgent(agentId);
    message.success("智能体已下线");
  } catch (e: any) {
    message.error(e?.message || "下线失败");
  }
}

async function handleDuplicate(agentId: string) {
  try {
    await store.duplicateAgent(agentId);
    message.success("智能体已复制");
  } catch (e: any) {
    message.error(e?.message || "复制失败");
  }
}

async function handleDelete(agentId: string) {
  try {
    await store.deleteAgent(agentId);
    message.success("智能体已删除");
    if (editingAgentId.value === agentId) {
      resetForm();
    }
  } catch (e: any) {
    message.error(e?.message || "删除失败");
  }
}

// 导出智能体配置为 JSON 文件下载
async function handleExport(agentId: string) {
  try {
    const response = await api.get(`/agents/${agentId}/export`);
    const blob = new Blob([JSON.stringify(response.data, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${response.data.name || "agent"}-export.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    message.success("智能体已导出");
  } catch (e: any) {
    message.error(e?.message || "导出失败");
  }
}

// 触发文件选择器
function triggerImport() {
  fileInputRef.value?.click();
}

// 导入智能体配置
async function handleImport(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  try {
    const text = await file.text();
    const config = JSON.parse(text);
    await api.post("/agents/import", config);
    message.success("智能体导入成功");
    await store.loadAgents();
  } catch (e: any) {
    message.error(e?.message || "导入失败，请检查文件格式");
  } finally {
    // 重置 input，允许再次选择同一文件
    target.value = "";
  }
}

onMounted(async () => {
  try {
    await Promise.all([
      store.loadAgents(),
      store.loadKnowledgeBases(),
      store.loadModelConfigs(),
      store.loadTools()
    ]);
    form.model_config_id =
      store.modelConfigs.find((item) => item.is_default)?.id ?? store.modelConfigs[0]?.id ?? null;
  } catch (e: any) {
    message.error("加载数据失败");
  }
});
</script>
