<template>
  <div class="two-column">
    <n-card :title="editingToolId ? '编辑工具' : '创建工具'">
      <n-form label-placement="top">
        <section class="tool-form-section">
          <h3>基础信息</h3>
          <n-form-item label="名称">
            <n-input v-model:value="form.name" placeholder="订单查询" />
          </n-form-item>
          <n-form-item label="描述">
            <n-input v-model:value="form.description" placeholder="查询订单状态" />
          </n-form-item>
          <n-form-item label="触发关键词">
            <n-select
              v-model:value="form.config.trigger_keywords"
              multiple
              filterable
              tag
              placeholder="例如：订单、物流、发货"
              :options="keywordOptions"
            />
          </n-form-item>
        </section>

        <section class="tool-form-section">
          <h3>请求配置</h3>
          <n-form-item label="请求地址">
            <n-input v-model:value="form.config.url" placeholder="https://api.example.com/order" />
          </n-form-item>
          <div class="tool-inline-grid">
            <n-form-item label="方法">
              <n-select
                v-model:value="form.config.method"
                :options="methodOptions"
                placeholder="选择方法"
              />
            </n-form-item>
            <n-form-item label="超时（秒）">
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

        <n-form-item label="状态" class="tool-status-field">
          <n-switch v-model:value="form.enabled">
            {{ form.enabled ? "启用" : "停用" }}
          </n-switch>
        </n-form-item>

        <div class="form-actions">
          <n-button type="primary" block @click="submit">
            {{ editingToolId ? "保存修改" : "创建" }}
          </n-button>
          <n-button v-if="editingToolId" block secondary @click="testTool">测试工具</n-button>
          <n-button v-if="editingToolId" block @click="resetForm">取消编辑</n-button>
        </div>
      </n-form>
    </n-card>

    <n-card title="工具列表">
      <n-data-table :columns="columns" :data="store.tools" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from "vue";
import { NButton, NPopconfirm, NSpace, NTag, useMessage, type DataTableColumns } from "naive-ui";

import type { HttpToolConfig, ToolDefinition, ToolPayload } from "../api/types";
import { useWorkspaceStore } from "../stores/workspace";

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

const keywordOptions = computed(() =>
  Array.from(
    new Set(
      store.tools.flatMap((item) => item.config.trigger_keywords || [])
    )
  ).map((item) => ({ label: item, value: item }))
);

const columns: DataTableColumns<ToolDefinition> = [
  { title: "名称", key: "name", width: 150 },
  { title: "类型", key: "type", width: 100 },
  {
    title: "描述",
    key: "description",
    ellipsis: { tooltip: true }
  },
  {
    title: "状态",
    key: "enabled",
    width: 100,
    render: (row) =>
      h(NTag, { type: row.enabled ? "success" : "warning", size: "small" }, {
        default: () => (row.enabled ? "启用" : "停用")
      })
  },
  {
    title: "操作",
    key: "actions",
    width: 220,
    render(row) {
      return h(NSpace, { size: 8 }, {
        default: () => [
          h(NButton, { size: "small", onClick: () => edit(row) }, { default: () => "编辑" }),
          h(NPopconfirm, { onPositiveClick: () => remove(row) }, {
            trigger: () => h(NButton, { size: "small", type: "error", secondary: true }, { default: () => "删除" }),
            default: () => `确认删除 ${row.name}？`
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
    throw new Error("JSON 格式有误");
  }
}

async function submit() {
  if (!form.name.trim()) {
    message.warning("请填写工具名称");
    return;
  }
  if (!form.config.url.trim()) {
    message.warning("请填写请求地址");
    return;
  }
  try {
    const payload: ToolPayload = {
      name: form.name.trim(),
      type: "http",
      description: form.description.trim(),
      config: {
        ...form.config,
        url: form.config.url.trim(),
        headers: readJson(headersText.value),
        query: readJson(queryText.value),
        body: readJson(bodyText.value)
      },
      enabled: form.enabled
    };

    if (editingToolId.value) {
      await store.updateTool(editingToolId.value, payload);
      message.success("工具已更新");
    } else {
      await store.createTool(payload);
      message.success("工具已创建");
    }
    resetForm();
  } catch (error) {
    message.error(error instanceof Error ? error.message : "保存失败");
  }
}

async function remove(tool: ToolDefinition) {
  await store.deleteTool(tool.id);
  if (editingToolId.value === tool.id) {
    resetForm();
  }
  message.success("工具已删除");
}

async function testTool() {
  if (!editingToolId.value) {
    message.warning("请先保存工具后再测试");
    return;
  }
  try {
    const result = await store.testTool(editingToolId.value, {});
    message[result.ok ? "success" : "error"](
      result.ok ? `测试通过，耗时 ${result.elapsed_ms} ms` : result.error || "测试失败"
    );
  } catch {
    message.error("测试失败");
  }
}

watch(
  () => form.config,
  () => {
    syncJsonText();
  },
  { deep: true }
);

onMounted(async () => {
  await store.loadTools();
  resetForm();
});
</script>
