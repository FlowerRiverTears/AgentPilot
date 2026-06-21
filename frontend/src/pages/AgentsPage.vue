<template>
  <div class="two-column">
    <n-card :title="editingAgentId ? t('agents.editAgent') : t('agents.createAgent')">
      <n-form label-placement="top">
        <n-form-item :label="t('common.name')">
          <n-input v-model:value="form.name" :placeholder="t('agents.namePlaceholder')" />
        </n-form-item>
        <n-form-item :label="t('common.description')">
          <n-input v-model:value="form.description" :placeholder="t('agents.descPlaceholder')" />
        </n-form-item>
        <n-form-item :label="t('agents.modelConfig')">
          <n-select
            v-model:value="form.model_config_id"
            :options="modelConfigOptions"
            :placeholder="t('agents.selectModelConfig')"
          />
        </n-form-item>
        <n-form-item :label="t('agents.promptTemplate')">
          <n-select
            :value="promptTemplate"
            :options="promptTemplateOptions"
            :placeholder="t('agents.selectPromptTemplate')"
            clearable
            @update:value="applyPromptTemplate"
          />
        </n-form-item>
        <n-form-item :label="t('agents.systemPrompt')">
          <n-input
            v-model:value="form.system_prompt"
            type="textarea"
            :autosize="{ minRows: 5, maxRows: 8 }"
          />
        </n-form-item>
        <n-form-item :label="t('agents.knowledgeBase')">
          <n-select
            v-model:value="form.knowledge_base_ids"
            multiple
            :options="kbOptions"
            :placeholder="t('agents.selectKB')"
          />
        </n-form-item>
        <n-form-item :label="t('agents.appliedTools')">
          <n-select
            v-model:value="form.tool_ids"
            multiple
            :options="toolOptions"
            :placeholder="t('agents.selectTools')"
          />
        </n-form-item>
        <n-form-item :label="t('agents.subAgents')">
          <n-select
            v-model:value="form.sub_agent_ids"
            multiple
            :options="subAgentOptions"
            :placeholder="t('agents.subAgentsPlaceholder')"
          />
          <template #feedback>
            <span class="form-hint">{{ t('agents.subAgentsHint') }}</span>
          </template>
        </n-form-item>
        <n-form-item :label="t('agents.toolChain')">
          <div class="tool-chain">
            <p class="form-hint">{{ t('agents.toolChainHint') }}</p>
            <div v-if="form.tool_ids.length === 0" class="chain-empty">
              {{ t('agents.noBoundTools') }}
            </div>
            <template v-else>
              <n-list bordered v-if="form.tool_chain.length > 0">
                <n-list-item v-for="(step, index) in form.tool_chain" :key="step.tool_id">
                  <div class="chain-step">
                    <div class="chain-step-head">
                      <n-tag size="small" round type="info">{{ t('agents.chainStep') }} {{ index + 1 }}</n-tag>
                      <span class="chain-tool-name">{{ toolName(step.tool_id) }}</span>
                    </div>
                    <div class="chain-step-body">
                      <div class="chain-mapping-row">
                        <span class="chain-label">{{ t('agents.inputMapping') }}</span>
                        <n-select
                          v-model:value="step.input_mapping.query"
                          :options="inputMappingOptions"
                          size="small"
                          class="chain-mapping-select"
                        />
                      </div>
                      <n-space size="small" class="chain-actions">
                        <n-button size="small" :disabled="index === 0" @click="moveChainStep(index, -1)">{{ t('agents.moveUp') }}</n-button>
                        <n-button size="small" :disabled="index === form.tool_chain.length - 1" @click="moveChainStep(index, 1)">{{ t('agents.moveDown') }}</n-button>
                        <n-button size="small" type="error" secondary @click="removeChainStep(index)">{{ t('agents.removeFromChain') }}</n-button>
                      </n-space>
                    </div>
                  </div>
                </n-list-item>
              </n-list>
              <div v-else class="chain-empty">
                {{ t('agents.toolChainEmpty') }}
              </div>
              <div v-if="availableChainTools.length > 0" class="chain-add-row">
                <n-select
                  v-model:value="chainAddToolId"
                  :options="availableChainTools"
                  :placeholder="t('agents.selectTool')"
                  size="small"
                  class="chain-add-select"
                />
                <n-button size="small" type="primary" :disabled="!chainAddToolId" @click="addChainStep">{{ t('agents.addToChain') }}</n-button>
              </div>
            </template>
          </div>
        </n-form-item>
        <div class="form-actions">
          <n-button type="primary" block @click="submit">
            {{ editingAgentId ? t('common.save') : t('common.create') }}
          </n-button>
          <n-button v-if="editingAgentId" block secondary @click="resetForm">{{ t('agents.cancelEdit') }}</n-button>
        </div>
      </n-form>
    </n-card>

    <n-card :title="t('agents.agentList')">
      <template #header-extra>
        <n-button type="primary" @click="triggerImport">{{ t('agents.importAgent') }}</n-button>
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
import { computed, h, onMounted, reactive, ref, watch } from "vue";
import { NButton, NPopconfirm, NSpace, NTag, useMessage, type DataTableColumns } from "naive-ui";
import { useI18n } from "vue-i18n";

import { api } from "../api/client";
import type { Agent, ToolChainStep } from "../api/types";
import { useWorkspaceStore } from "../stores/workspace";

const { t } = useI18n();
const message = useMessage();
const store = useWorkspaceStore();
const editingAgentId = ref<string | null>(null);

// Prompt 模板预置列表
const promptTemplateOptions = [
  { label: () => t('agents.templates.general'), value: "你是一个乐于助人的AI助手，请清晰、准确地回答用户问题。" },
  { label: () => t('agents.templates.customerService'), value: "你是一个专业的客服助手。请耐心、礼貌地回答用户问题，遇到无法解决的问题请引导用户联系人工客服。" },
  { label: () => t('agents.templates.codeAssistant'), value: "你是一个专业的编程助手。请提供准确、高效的代码建议，并附上简要说明。代码需遵循最佳实践。" },
  { label: () => t('agents.templates.translator'), value: "你是一个专业翻译助手。请将用户输入翻译为目标语言，保持原文语义和语气。如未指定目标语言，默认翻译为英文。" },
  { label: () => t('agents.templates.docSummary'), value: "你是一个文档总结助手。请根据提供的文档内容生成简洁的摘要，突出关键信息和要点。" },
  { label: () => t('agents.templates.dataAnalysis'), value: "你是一个数据分析助手。请根据提供的数据进行分析，给出清晰的结论和建议，必要时使用表格展示。" }
];

const promptTemplate = ref<string | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

const form = reactive({
  name: "",
  description: "",
  model_config_id: null as string | null,
  system_prompt: "你是一个企业 AI 智能体。回答必须清晰、准确，并在使用知识库时说明来源。",
  knowledge_base_ids: [] as string[],
  tool_ids: [] as string[],
  sub_agent_ids: [] as string[],
  tool_chain: [] as ToolChainStep[]
});

// 工具链编排：待添加到链中的工具选择
const chainAddToolId = ref<string | null>(null);

// 工具链输入映射可选项
const inputMappingOptions = [
  { label: "$user_input", value: "$user_input" },
  { label: "$prev_output", value: "$prev_output" }
];

const kbOptions = computed(() =>
  store.knowledgeBases.map((item) => ({ label: item.name, value: item.id }))
);

const modelConfigOptions = computed(() =>
  store.modelConfigs.map((item) => ({
    label: `${item.name} / ${item.default_model}${item.is_default ? ` / ${t('agents.defaultConfig')}` : ""}`,
    value: item.id
  }))
);

const toolOptions = computed(() =>
  store.tools.map((item) => ({
    label: `${item.name} / ${item.description}`,
    value: item.id
  }))
);

// 子智能体选项：已发布智能体列表，排除当前编辑的智能体自身以避免循环引用
const subAgentOptions = computed(() =>
  store.publishedAgents
    .filter((item) => item.id !== editingAgentId.value)
    .map((item) => ({ label: item.name, value: item.id }))
);

// 工具链中尚未添加的已绑定工具，用于"添加到工具链"下拉
const availableChainTools = computed(() => {
  const usedIds = new Set(form.tool_chain.map((step) => step.tool_id));
  return store.tools
    .filter((item) => form.tool_ids.includes(item.id) && !usedIds.has(item.id))
    .map((item) => ({ label: `${item.name} / ${item.description}`, value: item.id }));
});

// 根据 tool_id 查询工具名称
function toolName(toolId: string) {
  const tool = store.tools.find((item) => item.id === toolId);
  return tool ? tool.name : toolId;
}

// 添加一个工具到工具链末尾，默认输入映射为 $user_input
function addChainStep() {
  if (!chainAddToolId.value) return;
  form.tool_chain.push({
    tool_id: chainAddToolId.value,
    input_mapping: { query: "$user_input" }
  });
  chainAddToolId.value = null;
}

// 移除工具链中指定位置的步骤
function removeChainStep(index: number) {
  form.tool_chain.splice(index, 1);
}

// 工具链步骤排序：direction 为 -1 上移，1 下移
function moveChainStep(index: number, direction: number) {
  const target = index + direction;
  if (target < 0 || target >= form.tool_chain.length) return;
  const steps = form.tool_chain;
  [steps[index], steps[target]] = [steps[target], steps[index]];
}

// 当已绑定工具变化时，同步清理工具链中已解绑的工具步骤
watch(
  () => form.tool_ids,
  (newToolIds) => {
    const idSet = new Set(newToolIds);
    form.tool_chain = form.tool_chain.filter((step) => idSet.has(step.tool_id));
  }
);

const statusTagType = (status: string) => {
  if (status === "published") return "success";
  if (status === "draft") return "info";
  if (status === "deleted") return "default";
  return "warning";
};

const statusLabel = (status: string) => {
  if (status === "published") return t('agents.statusPublished');
  if (status === "draft") return t('agents.statusDraft');
  return status;
};

const columns: DataTableColumns<Agent> = [
  { title: t('common.name'), key: "name", width: 140 },
  {
    title: t('agents.modelConfig'),
    key: "model_config_id",
    width: 180,
    render(row) {
      return modelConfigName(row.model_config_id);
    }
  },
  { title: t('common.description'), key: "description", ellipsis: { tooltip: true } },
  {
    title: t('common.status'),
    key: "status",
    width: 90,
    render: (row) => h(NTag, { type: statusTagType(row.status), size: "small" }, { default: () => statusLabel(row.status) })
  },
  {
    title: t('common.actions'),
    key: "actions",
    width: 340,
    render(row) {
      const buttons = [
        h(NButton, { size: "small", secondary: true, onClick: () => startEdit(row) }, { default: () => t('agents.edit') })
      ];
      if (row.status === "draft") {
        buttons.push(
          h(NButton, { size: "small", type: "success", secondary: true, onClick: () => handlePublish(row.id) }, { default: () => t('agents.publish') })
        );
      }
      if (row.status === "published") {
        buttons.push(
          h(NButton, { size: "small", type: "warning", secondary: true, onClick: () => handleUnpublish(row.id) }, { default: () => t('agents.unpublish') })
        );
      }
      buttons.push(
        h(NButton, { size: "small", secondary: true, onClick: () => handleDuplicate(row.id) }, { default: () => t('agents.duplicate') })
      );
      buttons.push(
        h(NButton, { size: "small", secondary: true, onClick: () => handleExport(row.id) }, { default: () => t('agents.export') })
      );
      buttons.push(
        h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
          trigger: () => h(NButton, { size: "small", type: "error", secondary: true }, { default: () => t('common.delete') }),
          default: () => t('agents.confirmDelete')
        })
      );
      return h(NSpace, { size: 4 }, { default: () => buttons });
    }
  }
];

function modelConfigName(configId?: string | null) {
  if (!configId) return t('agents.defaultConfig');
  const config = store.modelConfigs.find((item) => item.id === configId);
  return config ? `${config.name} / ${config.default_model}` : t('agents.configDeleted');
}

function startEdit(agent: Agent) {
  editingAgentId.value = agent.id;
  form.name = agent.name;
  form.description = agent.description;
  form.model_config_id = agent.model_config_id ?? null;
  form.system_prompt = agent.system_prompt;
  form.knowledge_base_ids = [...agent.knowledge_base_ids];
  form.tool_ids = [...agent.tool_ids];
  // 回显子智能体与工具链编排
  form.sub_agent_ids = [...(agent.sub_agent_ids ?? [])];
  form.tool_chain = (agent.tool_chain ?? []).map((step) => ({
    tool_id: step.tool_id,
    input_mapping: { query: step.input_mapping.query }
  }));
  chainAddToolId.value = null;
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
  form.sub_agent_ids = [];
  form.tool_chain = [];
  chainAddToolId.value = null;
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
    message.warning(t('agents.nameRequired'));
    return;
  }
  if (!form.model_config_id) {
    message.warning(t('agents.modelConfigRequired'));
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
        tool_ids: form.tool_ids,
        sub_agent_ids: form.sub_agent_ids,
        tool_chain: form.tool_chain
      });
      message.success(t('agents.updated'));
      resetForm();
    } else {
      await store.createAgent({
        name: form.name.trim(),
        description: form.description.trim(),
        system_prompt: form.system_prompt,
        model_config_id: form.model_config_id,
        knowledge_base_ids: form.knowledge_base_ids,
        tool_ids: form.tool_ids,
        sub_agent_ids: form.sub_agent_ids,
        tool_chain: form.tool_chain
      });
      message.success(t('agents.created'));
      form.name = "";
      form.description = "";
      form.tool_ids = [];
      form.sub_agent_ids = [];
      form.tool_chain = [];
    }
  } catch (e: any) {
    message.error(e?.message || t('agents.operationFailed'));
  }
}

async function handlePublish(agentId: string) {
  try {
    await store.publishAgent(agentId);
    message.success(t('agents.published'));
  } catch (e: any) {
    message.error(e?.message || t('agents.publishFailed'));
  }
}

async function handleUnpublish(agentId: string) {
  try {
    await store.unpublishAgent(agentId);
    message.success(t('agents.unpublished'));
  } catch (e: any) {
    message.error(e?.message || t('agents.unpublishFailed'));
  }
}

async function handleDuplicate(agentId: string) {
  try {
    await store.duplicateAgent(agentId);
    message.success(t('agents.duplicated'));
  } catch (e: any) {
    message.error(e?.message || t('agents.duplicateFailed'));
  }
}

async function handleDelete(agentId: string) {
  try {
    await store.deleteAgent(agentId);
    message.success(t('agents.deleted'));
    if (editingAgentId.value === agentId) {
      resetForm();
    }
  } catch (e: any) {
    message.error(e?.message || t('agents.deleteFailed'));
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
    message.success(t('agents.exported'));
  } catch (e: any) {
    message.error(e?.message || t('agents.exportFailed'));
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
    message.success(t('agents.imported'));
    await store.loadAgents();
  } catch (e: any) {
    message.error(e?.message || t('agents.importFailed'));
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
      store.loadTools(),
      store.loadPublishedAgents()
    ]);
    form.model_config_id =
      store.modelConfigs.find((item) => item.is_default)?.id ?? store.modelConfigs[0]?.id ?? null;
  } catch (e: any) {
    message.error(t('agents.loadDataFailed'));
  }
});
</script>

<style scoped>
.form-hint {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.tool-chain {
  width: 100%;
  display: grid;
  gap: 10px;
}

.chain-empty {
  padding: 14px;
  border: 1px dashed var(--border-soft);
  border-radius: 8px;
  background: var(--surface-soft);
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
}

.chain-step {
  display: grid;
  gap: 8px;
}

.chain-step-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chain-tool-name {
  font-weight: 600;
  color: var(--text-strong);
}

.chain-step-body {
  display: grid;
  gap: 8px;
}

.chain-mapping-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chain-label {
  color: var(--text-muted);
  font-size: 13px;
  white-space: nowrap;
}

.chain-mapping-select {
  flex: 1;
  min-width: 0;
}

.chain-actions {
  flex-wrap: wrap;
}

.chain-add-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chain-add-select {
  flex: 1;
  min-width: 0;
}
</style>
