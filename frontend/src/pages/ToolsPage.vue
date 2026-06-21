<template>
  <div class="two-column">
    <n-card :title="editingToolId ? t('tools.editTool') : t('tools.createTool')">
      <n-form label-placement="top">
        <section class="tool-form-section">
          <div class="section-header">
            <h3>{{ t('tools.basicInfo') }}</h3>
            <n-dropdown v-if="!editingToolId" :options="templateOptions" @select="loadTemplate">
              <n-button size="small" secondary>
                {{ t('tools.loadTemplate') }} ▾
              </n-button>
            </n-dropdown>
          </div>
          <n-form-item :label="t('common.name')">
            <n-input v-model:value="form.name" :placeholder="t('tools.namePlaceholder')" />
          </n-form-item>
          <n-form-item :label="t('common.description')">
            <n-input v-model:value="form.description" :placeholder="t('tools.descPlaceholder')" />
          </n-form-item>
          <n-form-item :label="t('tools.triggerKeywords')">
            <n-select
              v-model:value="form.config.trigger_keywords"
              multiple
              filterable
              tag
              :placeholder="t('tools.keywordsPlaceholder')"
              :options="keywordOptions"
            />
          </n-form-item>
        </section>

        <section class="tool-form-section">
          <h3>{{ t('tools.requestConfig') }}</h3>
          <n-form-item :label="t('tools.requestUrl')">
            <n-input v-model:value="form.config.url" placeholder="https://api.example.com/order" />
          </n-form-item>
          <div class="tool-inline-grid">
            <n-form-item :label="t('tools.method')">
              <n-select
                v-model:value="form.config.method"
                :options="methodOptions"
                :placeholder="t('tools.selectMethod')"
              />
            </n-form-item>
            <n-form-item :label="t('tools.timeoutSeconds')">
              <n-input-number v-model:value="form.config.timeout_seconds" :min="1" :max="120" />
            </n-form-item>
          </div>
          <n-form-item label="Headers JSON">
            <n-input v-model:value="headersText" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
          </n-form-item>
          <n-form-item label="Query JSON">
            <n-input v-model:value="queryText" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
          </n-form-item>
          <n-form-item label="Body JSON">
            <n-input v-model:value="bodyText" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
          </n-form-item>
        </section>

        <n-form-item :label="t('common.status')" class="tool-status-field">
          <n-switch v-model:value="form.enabled" />
          <span style="margin-left: 8px">{{ form.enabled ? t('tools.enabled') : t('tools.disabled') }}</span>
        </n-form-item>

        <div class="form-actions">
          <n-button type="primary" block @click="submit">
            {{ editingToolId ? t('common.save') : t('common.create') }}
          </n-button>
          <n-button v-if="editingToolId" block secondary @click="testTool">{{ t('tools.testTool') }}</n-button>
          <n-button v-if="editingToolId" block @click="resetForm">{{ t('tools.cancelEdit') }}</n-button>
        </div>
      </n-form>
    </n-card>

    <n-card :title="t('tools.toolList')">
      <n-data-table :columns="columns" :data="store.tools" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from "vue";
import { NButton, NDropdown, NPopconfirm, NSpace, NTag, useMessage, type DataTableColumns, type DropdownOption } from "naive-ui";
import { useI18n } from "vue-i18n";

import type { HttpToolConfig, ToolDefinition, ToolPayload } from "../api/types";
import { useWorkspaceStore } from "../stores/workspace";

const { t } = useI18n();
const message = useMessage();
const store = useWorkspaceStore();
const editingToolId = ref<string | null>(null);
const headersText = ref("{}");
const queryText = ref("{}");
const bodyText = ref("{}");

const defaultConfig = (): HttpToolConfig => ({
  url: "",
  method: "GET",
  trigger_keywords: [],
  headers: {},
  query: {},
  body: {},
  timeout_seconds: 20
});

const form = reactive<ToolPayload>({
  name: "",
  type: "http",
  description: "",
  config: defaultConfig(),
  enabled: true
});

const methodOptions = [
  { label: "GET", value: "GET" },
  { label: "POST", value: "POST" }
];

const templateOptions: DropdownOption[] = [
  { label: () => t('tools.templateOrder'), key: "order" },
  { label: () => t('tools.templateInventory'), key: "inventory" },
  { label: () => t('tools.templateWeather'), key: "weather" },
  { label: () => t('tools.templateUser'), key: "user" }
];

interface ToolTemplate {
  name: string;
  description: string;
  config: HttpToolConfig;
  headers: Record<string, string>;
  query: Record<string, unknown>;
  body: Record<string, unknown>;
}

const toolTemplates: Record<string, ToolTemplate> = {
  order: {
    name: "订单查询",
    description: "查询订单状态、物流信息和发货进度，适合处理用户关于订单的咨询。",
    config: {
      url: "/api/mock/order",
      method: "GET",
      trigger_keywords: ["订单", "物流", "发货", "快递", "配送"],
      headers: {},
      query: {},
      body: {},
      timeout_seconds: 10
    },
    headers: {},
    query: {},
    body: {}
  },
  inventory: {
    name: "库存查询",
    description: "查询商品库存数量和仓库状态，适合处理用户关于商品是否有货的咨询。",
    config: {
      url: "/api/mock/inventory",
      method: "GET",
      trigger_keywords: ["库存", "有货", "缺货", "现货", "补货"],
      headers: {},
      query: {},
      body: {},
      timeout_seconds: 10
    },
    headers: {},
    query: {},
    body: {}
  },
  weather: {
    name: "天气查询",
    description: "查询城市天气信息，包括温度、湿度、风力和空气质量，适合处理天气相关咨询。",
    config: {
      url: "/api/mock/weather",
      method: "GET",
      trigger_keywords: ["天气", "气温", "下雨", "温度", "湿度"],
      headers: {},
      query: {},
      body: {},
      timeout_seconds: 10
    },
    headers: {},
    query: {},
    body: {}
  },
  user: {
    name: "用户查询",
    description: "查询用户资料和账户信息，适合处理用户关于个人资料的咨询。",
    config: {
      url: "/api/mock/order",
      method: "POST",
      trigger_keywords: ["用户", "账户", "资料", "个人信息", "会员"],
      headers: { "Content-Type": "application/json" },
      query: {},
      body: { "action": "query_profile" },
      timeout_seconds: 10
    },
    headers: { "Content-Type": "application/json" },
    query: {},
    body: { action: "query_profile" }
  }
};

function loadTemplate(key: string) {
  const template = toolTemplates[key];
  if (!template) return;
  editingToolId.value = null;
  form.name = template.name;
  form.type = "http";
  form.description = template.description;
  form.config = { ...defaultConfig(), ...template.config };
  form.enabled = true;
  headersText.value = JSON.stringify(template.headers, null, 2);
  queryText.value = JSON.stringify(template.query, null, 2);
  bodyText.value = JSON.stringify(template.body, null, 2);
  message.info(t('tools.templateLoaded', { name: template.name }));
}

const keywordOptions = computed(() =>
  Array.from(
    new Set(
      store.tools.flatMap((item) => item.config.trigger_keywords || [])
    )
  ).map((item) => ({ label: item, value: item }))
);

const columns: DataTableColumns<ToolDefinition> = [
  { title: t('common.name'), key: "name", width: 150 },
  { title: t('tools.type'), key: "type", width: 100 },
  {
    title: t('common.description'),
    key: "description",
    ellipsis: { tooltip: true }
  },
  {
    title: t('common.status'),
    key: "enabled",
    width: 100,
    render: (row) =>
      h(NTag, { type: row.enabled ? "success" : "warning", size: "small" }, {
        default: () => (row.enabled ? t('tools.enabled') : t('tools.disabled'))
      })
  },
  {
    title: t('common.actions'),
    key: "actions",
    width: 220,
    render(row) {
      return h(NSpace, { size: 8 }, {
        default: () => [
          h(NButton, { size: "small", onClick: () => edit(row) }, { default: () => t('tools.edit') }),
          h(NPopconfirm, { onPositiveClick: () => remove(row) }, {
            trigger: () => h(NButton, { size: "small", type: "error", secondary: true }, { default: () => t('common.delete') }),
            default: () => t('tools.confirmDelete', { name: row.name })
          })
        ]
      });
    }
  }
];

function edit(tool: ToolDefinition) {
  editingToolId.value = tool.id;
  form.name = tool.name;
  form.type = "http";
  form.description = tool.description;
  form.config = { ...defaultConfig(), ...tool.config };
  form.enabled = tool.enabled;
  syncJsonText();
}

function resetForm() {
  editingToolId.value = null;
  form.name = "";
  form.description = "";
  form.type = "http";
  form.config = defaultConfig();
  form.enabled = true;
  syncJsonText();
}

function syncJsonText() {
  headersText.value = JSON.stringify(form.config.headers ?? {}, null, 2);
  queryText.value = JSON.stringify(form.config.query ?? {}, null, 2);
  bodyText.value = JSON.stringify(form.config.body ?? {}, null, 2);
}

function readJson(text: string) {
  try {
    return text.trim() ? JSON.parse(text) : {};
  } catch {
    throw new Error(t('tools.jsonFormatError'));
  }
}

async function submit() {
  if (!form.name.trim()) {
    message.warning(t('tools.nameRequired'));
    return;
  }
  if (!form.config.url.trim()) {
    message.warning(t('tools.urlRequired'));
    return;
  }
  try {
    let url = form.config.url.trim();
    if (url.startsWith("/api/")) {
      url = `${window.location.origin}${url}`;
    }

    const payload: ToolPayload = {
      name: form.name.trim(),
      type: "http",
      description: form.description.trim(),
      config: {
        ...form.config,
        url,
        headers: readJson(headersText.value),
        query: readJson(queryText.value),
        body: readJson(bodyText.value)
      },
      enabled: form.enabled
    };

    if (editingToolId.value) {
      await store.updateTool(editingToolId.value, payload);
      message.success(t('tools.updated'));
    } else {
      await store.createTool(payload);
      message.success(t('tools.created'));
    }
    resetForm();
  } catch (error) {
    message.error(error instanceof Error ? error.message : t('tools.saveFailed'));
  }
}

async function remove(tool: ToolDefinition) {
  try {
    await store.deleteTool(tool.id);
    if (editingToolId.value === tool.id) {
      resetForm();
    }
    message.success(t('tools.deleted'));
  } catch (e: any) {
    message.error(e?.message || t('tools.deleteFailed'));
  }
}

async function testTool() {
  if (!editingToolId.value) {
    message.warning(t('tools.saveBeforeTest'));
    return;
  }
  try {
    const result = await store.testTool(editingToolId.value, {});
    message[result.ok ? "success" : "error"](
      result.ok ? t('tools.testPassed', { ms: result.elapsed_ms }) : result.error || t('tools.testFailed')
    );
  } catch {
    message.error(t('tools.testFailed'));
  }
}

watch(
  () => [form.config.headers, form.config.query, form.config.body],
  () => {
    if (!editingToolId.value) {
      syncJsonText();
    }
  },
  { deep: true }
);

onMounted(async () => {
  await store.loadTools();
  resetForm();
});
</script>
