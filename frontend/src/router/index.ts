import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

import AgentsPage from "../pages/AgentsPage.vue";
import ChatPage from "../pages/ChatPage.vue";
import DashboardPage from "../pages/DashboardPage.vue";
import EvalPage from "../pages/EvalPage.vue";
import GuidePage from "../pages/GuidePage.vue";
import KnowledgePage from "../pages/KnowledgePage.vue";
import LoginPage from "../pages/LoginPage.vue";
import ModelSettingsPage from "../pages/ModelSettingsPage.vue";
import PortalPage from "../pages/PortalPage.vue";
import RagTuningPage from "../pages/RagTuningPage.vue";
import RunsPage from "../pages/RunsPage.vue";
import ToolsPage from "../pages/ToolsPage.vue";
import UsersPage from "../pages/UsersPage.vue";
import WorkflowPage from "../pages/WorkflowPage.vue";

const PUBLIC_PATHS = ["/login", "/portal"];
const ADMIN_PATHS = ["/users"];

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
    { path: "/eval", component: EvalPage },
    { path: "/workflows", component: WorkflowPage },
    { path: "/rag-tuning", component: RagTuningPage },
    { path: "/portal", component: PortalPage, meta: { public: true } },
    { path: "/chat", component: ChatPage },
    { path: "/users", component: UsersPage, meta: { admin: true } },
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
  if ((to.meta.admin || ADMIN_PATHS.includes(to.path)) && auth.user?.role !== "admin") {
    return { path: "/" };
  }
  return true;
});

export default router;
