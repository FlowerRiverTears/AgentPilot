<template>
  <div class="login-page">
    <n-card class="login-card" :title="t('login.title')" size="large">
      <n-form @submit.prevent="handleLogin">
        <n-form-item :label="t('login.username')">
          <n-input v-model:value="form.username" :placeholder="t('login.usernamePlaceholder')" :disabled="loading" />
        </n-form-item>
        <n-form-item :label="t('login.password')">
          <n-input
            v-model:value="form.password"
            type="password"
            show-password-on="click"
            :placeholder="t('login.passwordPlaceholder')"
            :disabled="loading"
            @keyup.enter="handleLogin"
          />
        </n-form-item>
        <n-button type="primary" block :loading="loading" @click="handleLogin">{{ t('login.submit') }}</n-button>
      </n-form>
      <n-alert type="info" class="login-tip" :bordered="false">
        {{ t('login.defaultAccount') }}
      </n-alert>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useMessage } from "naive-ui";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const route = useRoute();
const message = useMessage();
const auth = useAuthStore();
const { t } = useI18n();

const form = reactive({ username: "admin", password: "" });
const loading = ref(false);

async function handleLogin() {
  if (!form.username.trim() || !form.password.trim()) {
    message.warning(t('login.emptyWarning'));
    return;
  }
  loading.value = true;
  try {
    await auth.login(form.username.trim(), form.password);
    message.success(t('login.success'));
    const redirect = (route.query.redirect as string) || "/";
    router.push(redirect);
  } catch {
    message.error(t('login.failed'));
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 400px;
  max-width: 90vw;
}
.login-tip {
  margin-top: 16px;
}
</style>
