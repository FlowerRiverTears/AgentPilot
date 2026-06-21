<template>
  <div class="settings-page">
    <n-card :title="t('modelSettings.title')">
      <n-alert type="info" class="settings-tip">
        {{ t('modelSettings.tip') }}
      </n-alert>

      <n-form label-placement="top">
        <n-form-item :label="t('modelSettings.configName')">
          <n-input v-model:value="form.name" :placeholder="t('modelSettings.configNamePlaceholder')" />
        </n-form-item>
        <n-form-item :label="t('modelSettings.baseUrl')">
          <n-input
            v-model:value="form.base_url"
            :placeholder="t('modelSettings.baseUrlPlaceholder')"
          />
        </n-form-item>
        <n-form-item label="API Token">
          <n-input
            v-model:value="form.api_key"
            type="password"
            show-password-on="click"
            :placeholder="t('modelSettings.apiTokenPlaceholder')"
          />
        </n-form-item>
        <n-form-item :label="t('modelSettings.defaultModel')">
          <n-input v-model:value="form.default_model" :placeholder="t('modelSettings.defaultModelPlaceholder')" />
        </n-form-item>
        <n-checkbox v-model:checked="form.is_default">{{ t('modelSettings.setAsDefault') }}</n-checkbox>
        <div class="settings-actions">
          <n-button type="primary" :loading="saving" @click="save">
            {{ editingId ? t('common.save') : t('modelSettings.addConfig') }}
          </n-button>
          <n-button v-if="editingId" @click="resetForm">{{ t('modelSettings.cancelEdit') }}</n-button>
        </div>
      </n-form>
    </n-card>

    <n-card :title="t('modelSettings.configList')">
      <n-data-table :columns="columns" :data="store.modelConfigs" :bordered="false" />
    </n-card>

    <n-card :title="t('modelSettings.currentDefault')">
      <n-descriptions bordered :column="1" label-placement="left">
        <n-descriptions-item :label="t('modelSettings.configName')">
          {{ store.modelConfig?.name || t('modelSettings.notLoaded') }}
        </n-descriptions-item>
        <n-descriptions-item :label="t('modelSettings.baseUrl')">
          {{ store.modelConfig?.base_url || t('modelSettings.notLoaded') }}
        </n-descriptions-item>
        <n-descriptions-item label="Token">
          {{ store.modelConfig?.api_key_set ? t('modelSettings.configured') : t('modelSettings.notConfigured') }}
        </n-descriptions-item>
        <n-descriptions-item :label="t('modelSettings.defaultModel')">
          {{ store.modelConfig?.default_model || t('modelSettings.notLoaded') }}
        </n-descriptions-item>
      </n-descriptions>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from "vue";
import { NButton, NSpace, NTag, useDialog, useMessage, type DataTableColumns } from "naive-ui";
import { useI18n } from "vue-i18n";

import type { ModelConfig } from "../api/types";
import { useWorkspaceStore } from "../stores/workspace";

const { t } = useI18n();
const message = useMessage();
const dialog = useDialog();
const store = useWorkspaceStore();
const saving = ref(false);
const testingId = ref<string | null>(null);
const editingId = ref<string | null>(null);

const form = reactive({
  name: "",
  base_url: "",
  api_key: "",
  default_model: "",
  is_default: false
});

const columns: DataTableColumns<ModelConfig> = [
  { title: t('common.name'), key: "name" },
  { title: t('modelSettings.baseUrl'), key: "base_url", ellipsis: { tooltip: true } },
  { title: t('modelSettings.model'), key: "default_model" },
  {
    title: "Token",
    key: "api_key_set",
    render(row) {
      return h(NTag, { type: row.api_key_set ? "success" : "warning", size: "small" }, {
        default: () => (row.api_key_set ? t('modelSettings.configured') : t('modelSettings.notConfigured'))
      });
    }
  },
  {
    title: t('modelSettings.default'),
    key: "is_default",
    render(row) {
      return row.is_default
        ? h(NTag, { type: "info", size: "small" }, { default: () => t('modelSettings.default') })
        : h(
            NButton,
            { size: "small", secondary: true, onClick: () => setDefault(row.id) },
            { default: () => t('modelSettings.setDefault') }
          );
    }
  },
  {
    title: t('common.actions'),
    key: "actions",
    render(row) {
      return h(
        NSpace,
        { size: 8 },
        {
          default: () => [
            h(NButton, { size: "small", onClick: () => edit(row) }, { default: () => t('modelSettings.edit') }),
            h(
              NButton,
              {
                size: "small",
                secondary: true,
                loading: testingId.value === row.id,
                onClick: () => test(row)
              },
              { default: () => t('modelSettings.test') }
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
              { default: () => t('common.delete') }
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
    message.warning(t('modelSettings.fillRequired'));
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
      message.success(t('modelSettings.updated'));
    } else {
      await store.createModelConfig(payload);
      message.success(t('modelSettings.added'));
    }
    resetForm();
  } catch (error) {
    message.error(t('modelSettings.saveFailed'));
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
  form.name = "";
  form.base_url = "";
  form.api_key = "";
  form.default_model = "";
  form.is_default = false;
}

async function setDefault(configId: string) {
  try {
    await store.setDefaultModelConfig(configId);
    message.success(t('modelSettings.defaultSwitched'));
  } catch (e: any) {
    message.error(e?.message || t('modelSettings.setDefaultFailed'));
  }
}

async function test(row: ModelConfig) {
  testingId.value = row.id;
  try {
    const result = await store.testModelConfig(row.id);
    if (result.ok) {
      message.success(t('modelSettings.testSuccess', { name: row.name, message: result.message }));
    } else {
      message.error(t('modelSettings.testFail', { name: row.name, message: result.message }));
    }
  } catch (error) {
    message.error(t('modelSettings.testError'));
    console.error(error);
  } finally {
    testingId.value = null;
  }
}

function confirmDelete(row: ModelConfig) {
  dialog.warning({
    title: t('modelSettings.deleteConfig'),
    content: t('modelSettings.confirmDelete', { name: row.name }),
    positiveText: t('common.delete'),
    negativeText: t('common.cancel'),
    onPositiveClick: async () => {
      try {
        await store.deleteModelConfig(row.id);
        message.success(t('modelSettings.deleted'));
      } catch (e: any) {
        message.error(e?.message || t('modelSettings.deleteFailed'));
      }
    }
  });
}

onMounted(load);
</script>
