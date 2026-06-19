<template>
  <n-config-provider :theme="naiveTheme">
    <n-message-provider>
      <n-dialog-provider>
        <router-view v-if="isPortalRoute" />
        <n-layout v-else class="app-shell" has-sider>
          <n-layout-sider bordered width="232">
            <div class="brand">AgentPilot</div>
            <n-menu :options="menuOptions" :value="route.path" @update:value="go" />
          </n-layout-sider>
          <n-layout>
            <n-layout-header bordered class="topbar">
              <div>
                <strong>智能体工作台</strong>
                <span>后台制造智能体，前台体验智能体</span>
              </div>
              <div class="topbar-actions">
                <n-button secondary @click="ui.toggleTheme">
                  {{ ui.theme === "dark" ? "亮色" : "深色" }}
                </n-button>
                <n-button v-if="auth.isAuthenticated" secondary @click="handleLogout">退出登录</n-button>
                <n-button secondary @click="goPortal">进入前台</n-button>
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

import { useAuthStore } from "./stores/auth";
import { useUiStore } from "./stores/ui";

const route = useRoute();
const router = useRouter();
const ui = useUiStore();
const auth = useAuthStore();
const isPortalRoute = computed(() => route.path === "/portal" || route.path === "/login");
const naiveTheme = computed(() => (ui.theme === "dark" ? darkTheme : null));

const menuOptions = [
  { label: () => h(RouterLink, { to: "/" }, { default: () => "总览" }), key: "/" },
  { label: () => h(RouterLink, { to: "/guide" }, { default: () => "使用教程" }), key: "/guide" },
  { label: () => h(RouterLink, { to: "/agents" }, { default: () => "智能体后台" }), key: "/agents" },
  {
    label: () => h(RouterLink, { to: "/knowledge" }, { default: () => "知识库" }),
    key: "/knowledge"
  },
  { label: () => h(RouterLink, { to: "/tools" }, { default: () => "工具管理" }), key: "/tools" },
  {
    label: () => h(RouterLink, { to: "/settings/model" }, { default: () => "模型配置" }),
    key: "/settings/model"
  },
  { label: () => h(RouterLink, { to: "/runs" }, { default: () => "运行历史" }), key: "/runs" },
  { label: () => h(RouterLink, { to: "/chat" }, { default: () => "运行测试" }), key: "/chat" }
];

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

onMounted(() => {
  ui.initTheme();
});
</script>
