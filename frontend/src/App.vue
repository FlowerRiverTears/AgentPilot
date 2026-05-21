<template>
  <n-config-provider>
    <n-message-provider>
      <n-dialog-provider>
        <n-layout class="app-shell" has-sider>
          <n-layout-sider bordered width="232">
            <div class="brand">AgentPilot</div>
            <n-menu :options="menuOptions" :value="route.path" @update:value="go" />
          </n-layout-sider>
          <n-layout>
            <n-layout-header bordered class="topbar">
              <div>
                <strong>智能体工作台</strong>
                <span>大模型 / 检索增强 / 切面 / 向量</span>
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
import { h } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const menuOptions = [
  { label: () => h(RouterLink, { to: "/" }, { default: () => "总览" }), key: "/" },
  { label: () => h(RouterLink, { to: "/agents" }, { default: () => "智能体" }), key: "/agents" },
  {
    label: () => h(RouterLink, { to: "/knowledge" }, { default: () => "知识库" }),
    key: "/knowledge"
  },
  { label: () => h(RouterLink, { to: "/chat" }, { default: () => "运行任务" }), key: "/chat" }
];

function go(path: string) {
  router.push(path);
}
</script>
