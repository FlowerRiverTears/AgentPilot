import { createRouter, createWebHistory } from "vue-router";

import AgentsPage from "../pages/AgentsPage.vue";
import ChatPage from "../pages/ChatPage.vue";
import DashboardPage from "../pages/DashboardPage.vue";
import KnowledgePage from "../pages/KnowledgePage.vue";
import ModelSettingsPage from "../pages/ModelSettingsPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: DashboardPage },
    { path: "/agents", component: AgentsPage },
    { path: "/knowledge", component: KnowledgePage },
    { path: "/settings/model", component: ModelSettingsPage },
    { path: "/chat", component: ChatPage }
  ]
});

export default router;
