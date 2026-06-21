<template>
  <n-config-provider :theme="naiveTheme">
    <n-message-provider>
      <n-dialog-provider>
        <router-view v-if="isPortalRoute" />
        <n-layout v-else class="app-shell" has-sider>
          <n-layout-sider bordered width="232">
            <div class="brand">AgentPilot</div>
            <n-menu :options="filteredMenuOptions" :value="route.path" @update:value="go" />
          </n-layout-sider>
          <n-layout>
            <n-layout-header bordered class="topbar">
              <div>
                <strong>{{ t('app.title') }}</strong>
                <span>{{ t('app.subtitle') }}</span>
              </div>
              <div class="topbar-actions">
                <n-button secondary @click="toggleLocale">{{ ui.locale === 'zh' ? 'EN' : '中' }}</n-button>
                <n-button secondary @click="ui.toggleTheme">
                  {{ ui.theme === "dark" ? t('common.light') : t('common.dark') }}
                </n-button>
                <n-button v-if="auth.isAuthenticated" secondary @click="handleLogout">{{ t('common.logout') }}</n-button>
                <n-button secondary @click="goPortal">{{ t('common.goPortal') }}</n-button>
              </div>
            </n-layout-header>
            <n-layout-content class="content">
              <router-view />
            </n-layout-content>
          </n-layout>
        </n-layout>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed, h, onMounted } from "vue";
import { darkTheme } from "naive-ui";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { useI18n } from "vue-i18n";
import { useAuthStore } from "./stores/auth";
import { useUiStore } from "./stores/ui";

const route = useRoute();
const router = useRouter();
const ui = useUiStore();
const auth = useAuthStore();
const { t, locale } = useI18n();
const isPortalRoute = computed(() => route.path === "/portal" || route.path === "/login");
const naiveTheme = computed(() => (ui.theme === "dark" ? darkTheme : null));

const menuOptions = [
  { label: () => h(RouterLink, { to: "/" }, { default: () => t('nav.dashboard') }), key: "/" },
  { label: () => h(RouterLink, { to: "/guide" }, { default: () => t('nav.guide') }), key: "/guide" },
  { label: () => h(RouterLink, { to: "/agents" }, { default: () => t('nav.agents') }), key: "/agents" },
  {
    label: () => h(RouterLink, { to: "/knowledge" }, { default: () => t('nav.knowledge') }),
    key: "/knowledge"
  },
  { label: () => h(RouterLink, { to: "/tools" }, { default: () => t('nav.tools') }), key: "/tools" },
  {
    label: () => h(RouterLink, { to: "/settings/model" }, { default: () => t('nav.modelSettings') }),
    key: "/settings/model"
  },
  { label: () => h(RouterLink, { to: "/runs" }, { default: () => t('nav.runs') }), key: "/runs" },
  { label: () => h(RouterLink, { to: "/eval" }, { default: () => t('nav.eval') }), key: "/eval" },
  { label: () => h(RouterLink, { to: "/workflows" }, { default: () => t('nav.workflows') }), key: "/workflows" },
  { label: () => h(RouterLink, { to: "/rag-tuning" }, { default: () => t('nav.ragTuning') }), key: "/rag-tuning" },
  { label: () => h(RouterLink, { to: "/chat" }, { default: () => t('nav.chat') }), key: "/chat" },
];

// 管理员专有菜单项
const adminMenuOptions = [
  { label: () => h(RouterLink, { to: "/users" }, { default: () => t('nav.users') }), key: "/users" },
];

const filteredMenuOptions = computed(() => {
  const base = [...menuOptions];
  if (auth.user?.role === "admin") {
    base.push(...adminMenuOptions);
  }
  return base;
});

function go(path: string) {
  router.push(path);
}

function goPortal() {
  router.push("/portal");
}

function handleLogout() {
  auth.logout();
  router.push("/login");
}

function toggleLocale() {
  ui.toggleLocale();
  locale.value = ui.locale;
}

onMounted(() => {
  ui.initTheme();
});
</script>
