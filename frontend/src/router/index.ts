import { createRouter, createWebHistory } from "vue-router";

import AgentsPage from "../pages/AgentsPage.vue";
import ChatPage from "../pages/ChatPage.vue";
import DashboardPage from "../pages/DashboardPage.vue";
import GuidePage from "../pages/GuidePage.vue";
import KnowledgePage from "../pages/KnowledgePage.vue";
import ModelSettingsPage from "../pages/ModelSettingsPage.vue";
import PortalPage from "../pages/PortalPage.vue";
import ToolsPage from "../pages/ToolsPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: DashboardPage },
    { path: "/guide", component: GuidePage },
    { path: "/agents", component: AgentsPage },
    { path: "/knowledge", component: KnowledgePage },
    { path: "/tools", component: ToolsPage },
    { path: "/settings/model", component: ModelSettingsPage },
    { path: "/portal", component: PortalPage },
    { path: "/chat", component: ChatPage }
  ]
});

export default router;
