<template>
  <div class="settings-page">
    <n-card title="模型配置">
      <n-alert type="info" class="settings-tip">
        这里配置用户自己的大模型接口和 Token。Token 只会提交给当前后端运行时使用，不会写入前端代码。
      </n-alert>

      <n-form label-placement="top">
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
            placeholder="请输入你自己的 Token"
          />
        </n-form-item>
        <n-form-item label="默认模型">
          <n-input v-model:value="form.default_model" placeholder="例如：gpt-4o-mini、deepseek-chat、qwen2.5:7b" />
        </n-form-item>
        <n-button type="primary" :loading="saving" @click="save">保存配置</n-button>
      </n-form>
    </n-card>

    <n-card title="当前状态">
      <n-descriptions bordered :column="1" label-placement="left">
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
import { onMounted, reactive, ref } from "vue";
import { useMessage } from "naive-ui";

import { useWorkspaceStore } from "../stores/workspace";

const message = useMessage();
const store = useWorkspaceStore();
const saving = ref(false);

const form = reactive({
  base_url: "",
  api_key: "",
  default_model: ""
});

async function load() {
  const config = await store.loadModelConfig();
  form.base_url = config.base_url;
  form.default_model = config.default_model;
}

async function save() {
  if (!form.base_url.trim() || !form.default_model.trim()) {
    message.warning("请填写接口地址和默认模型");
    return;
  }

  saving.value = true;
  try {
    await store.updateModelConfig({
      base_url: form.base_url.trim(),
      api_key: form.api_key.trim(),
      default_model: form.default_model.trim()
    });
    form.api_key = "";
    message.success("模型配置已保存");
  } catch (error) {
    message.error("保存失败，请检查后端服务");
    console.error(error);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>
