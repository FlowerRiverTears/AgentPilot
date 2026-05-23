<template>
  <div class="settings-page">
    <n-card title="模型配置">
      <n-alert type="info" class="settings-tip">
        可以维护多套 OpenAI-compatible 接口配置，例如 ollama、deepseek、minmax。运行任务默认使用标记为默认的配置。
      </n-alert>

      <n-form label-placement="top">
        <n-form-item label="配置名称">
          <n-input v-model:value="form.name" placeholder="例如：ollama、minmax、deepseek" />
        </n-form-item>
        <n-form-item label="接口地址">
          <n-input
            v-model:value="form.base_url"
            placeholder="例如：https://api.openai.com/v1 或 http://host.docker.internal:11434/v1"
          />
        </n-form-item>
        <n-form-item label="API Token">
          <n-input
            v-model:value="form.api_key"
            type="password"
            show-password-on="click"
            placeholder="编辑时留空表示不修改已有 Token"
          />
        </n-form-item>
        <n-form-item label="默认模型">
          <n-input v-model:value="form.default_model" placeholder="例如：gpt-4o-mini、deepseek-chat、qwen2.5:7b" />
        </n-form-item>
        <n-checkbox v-model:checked="form.is_default">设为默认配置</n-checkbox>
        <div class="settings-actions">
          <n-button type="primary" :loading="saving" @click="save">
            {{ editingId ? "保存修改" : "新增配置" }}
          </n-button>
          <n-button v-if="editingId" @click="resetForm">取消编辑</n-button>
        </div>
      </n-form>
    </n-card>

    <n-card title="配置列表">
      <n-data-table :columns="columns" :data="store.modelConfigs" :bordered="false" />
    </n-card>

    <n-card title="当前默认">
      <n-descriptions bordered :column="1" label-placement="left">
        <n-descriptions-item label="配置名称">
          {{ store.modelConfig?.name || "未加载" }}
        </n-descriptions-item>
        <n-descriptions-item label="接口地址">
          {{ store.modelConfig?.base_url || "未加载" }}
        </n-descriptions-item>
        <n-descriptions-item label="Token">
          {{ store.modelConfig?.api_key_set ? "已配置" : "未配置" }}
        </n-descriptions-item>
        <n-descriptions-item label="默认模型">
          {{ store.modelConfig?.default_model || "未加载" }}
        </n-descriptions-item>
      </n-descriptions>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from "vue";
import { NButton, NSpace, NTag, useDialog, useMessage, type DataTableColumns } from "naive-ui";

import type { ModelConfig } from "../api/types";
import { useWorkspaceStore } from "../stores/workspace";

const message = useMessage();
const dialog = useDialog();
const store = useWorkspaceStore();
const saving = ref(false);
const testingId = ref<string | null>(null);
const editingId = ref<string | null>(null);

const form = reactive({
  name: "minmax",
  base_url: "",
  api_key: "",
  default_model: "",
  is_default: false
});

const columns: DataTableColumns<ModelConfig> = [
  { title: "名称", key: "name" },
  { title: "接口地址", key: "base_url", ellipsis: { tooltip: true } },
  { title: "模型", key: "default_model" },
  {
    title: "Token",
    key: "api_key_set",
    render(row) {
      return h(NTag, { type: row.api_key_set ? "success" : "warning", size: "small" }, {
        default: () => (row.api_key_set ? "已配置" : "未配置")
      });
    }
  },
  {
    title: "默认",
    key: "is_default",
    render(row) {
      return row.is_default
        ? h(NTag, { type: "info", size: "small" }, { default: () => "默认" })
        : h(
            NButton,
            { size: "small", secondary: true, onClick: () => setDefault(row.id) },
            { default: () => "设默认" }
          );
    }
  },
  {
    title: "操作",
    key: "actions",
    render(row) {
      return h(
        NSpace,
        { size: 8 },
        {
          default: () => [
            h(NButton, { size: "small", onClick: () => edit(row) }, { default: () => "编辑" }),
            h(
              NButton,
              {
                size: "small",
                secondary: true,
                loading: testingId.value === row.id,
                onClick: () => test(row)
              },
              { default: () => "测试" }
            ),
            h(
              NButton,
              {
                size: "small",
                type: "error",
                secondary: true,
                disabled: row.is_default,
                onClick: () => confirmDelete(row)
              },
              { default: () => "删除" }
            )
          ]
        }
      );
    }
  }
];

async function load() {
  await store.loadModelConfigs();
  if (!store.modelConfigs.length) {
    await store.loadModelConfig();
  }
}

function validate() {
  if (!form.name.trim() || !form.base_url.trim() || !form.default_model.trim()) {
    message.warning("请填写配置名称、接口地址和默认模型");
    return false;
  }
  return true;
}

async function save() {
  if (!validate()) {
    return;
  }

  saving.value = true;
  try {
    const payload = {
      name: form.name.trim(),
      base_url: form.base_url.trim(),
      api_key: form.api_key.trim(),
      default_model: form.default_model.trim(),
      is_default: form.is_default
    };
    if (editingId.value) {
      await store.updateNamedModelConfig(editingId.value, payload);
      message.success("模型配置已更新");
    } else {
      await store.createModelConfig(payload);
      message.success("模型配置已新增");
    }
    resetForm();
  } catch (error) {
    message.error("保存失败，请检查名称是否重复或后端服务是否正常");
    console.error(error);
  } finally {
    saving.value = false;
  }
}

function edit(row: ModelConfig) {
  editingId.value = row.id;
  form.name = row.name;
  form.base_url = row.base_url;
  form.api_key = "";
  form.default_model = row.default_model;
  form.is_default = row.is_default;
}

function resetForm() {
  editingId.value = null;
  form.name = "minmax";
  form.base_url = "";
  form.api_key = "";
  form.default_model = "";
  form.is_default = false;
}

async function setDefault(configId: string) {
  await store.setDefaultModelConfig(configId);
  message.success("默认模型配置已切换");
}

async function test(row: ModelConfig) {
  testingId.value = row.id;
  try {
    const result = await store.testModelConfig(row.id);
    if (result.ok) {
      message.success(`${row.name} 测试成功：${result.message}`);
    } else {
      message.error(`${row.name} 测试失败：${result.message}`);
    }
  } catch (error) {
    message.error("测试失败，请检查后端服务");
    console.error(error);
  } finally {
    testingId.value = null;
  }
}

function confirmDelete(row: ModelConfig) {
  dialog.warning({
    title: "删除模型配置",
    content: `确认删除 ${row.name} 吗？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await store.deleteModelConfig(row.id);
      message.success("模型配置已删除");
    }
  });
}

onMounted(load);
</script>
