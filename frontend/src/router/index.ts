import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

import AgentsPage from "../pages/AgentsPage.vue";
import ChatPage from "../pages/ChatPage.vue";
import DashboardPage from "../pages/DashboardPage.vue";
import GuidePage from "../pages/GuidePage.vue";
import KnowledgePage from "../pages/KnowledgePage.vue";
import LoginPage from "../pages/LoginPage.vue";
import ModelSettingsPage from "../pages/ModelSettingsPage.vue";
import PortalPage from "../pages/PortalPage.vue";
import RunsPage from "../pages/RunsPage.vue";
import ToolsPage from "../pages/ToolsPage.vue";

const PUBLIC_PATHS = ["/login", "/portal"];

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginPage, meta: { public: true } },
    { path: "/", component: DashboardPage },
    { path: "/guide", component: GuidePage },
    { path: "/agents", component: AgentsPage },
    { path: "/knowledge", component: KnowledgePage },
    { path: "/tools", component: ToolsPage },
    { path: "/settings/model", component: ModelSettingsPage },
    { path: "/runs", component: RunsPage },
    { path: "/portal", component: PortalPage, meta: { public: true } },
    { path: "/chat", component: ChatPage },
    { path: "/:pathMatch(.*)*", redirect: "/" }
  ]
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.meta.public || PUBLIC_PATHS.includes(to.path)) {
    return true;
  }
  if (!auth.isAuthenticated) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  return true;
});

export default router;
