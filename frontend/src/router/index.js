import { createRouter, createWebHistory } from "vue-router";

import HomeView from "../views/HomeView.vue";
import ChatView from "../views/ChatView.vue";
import FeedbackView from "../views/FeedbackView.vue";
import KnowledgeView from "../views/KnowledgeView.vue";
import RunsView from "../views/RunsView.vue";

// 前端把系统组织成一个工作台：首页、知识库、对话、运行记录、反馈统计。
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/chat", name: "chat", component: ChatView },
    { path: "/feedback", name: "feedback", component: FeedbackView },
    { path: "/knowledge", name: "knowledge", component: KnowledgeView },
    { path: "/runs", name: "runs", component: RunsView },
  ],
});

export default router;
