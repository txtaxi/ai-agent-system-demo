<template>
  <section class="panel">
    <p class="panel-label">对话模块</p>
    <h2>知识问答工作台</h2>
    <p class="section-intro">
      用户可直接提问，系统会自动选择相关知识库候选，执行跨库检索、任务路由、工具选择和 LangGraph 工作流。
    </p>

    <div v-if="pageMessage" class="message-banner error">
      {{ pageMessage }}
    </div>

    <div class="chat-page-layout">
      <aside class="session-sidebar">
        <div class="list-header">
          <h3>会话列表</h3>
          <button type="button" @click="startNewConversation">新建会话</button>
        </div>

        <div v-if="conversations.length === 0" class="empty-state">暂无会话。</div>
        <div v-else class="session-list">
          <button
            v-for="conversation in conversations"
            :key="conversation.id"
            type="button"
            :class="['session-item', { active: activeConversationId === conversation.id }]"
            @click="selectConversation(conversation.id)"
          >
            <strong>{{ conversation.title }}</strong>
            <span>会话 ID：{{ conversation.id }}</span>
          </button>
        </div>
      </aside>

      <div class="chat-main">
        <div class="chat-window">
          <div
            v-for="message in messages"
            :key="message.id"
            :class="['message', message.role === 'assistant' ? 'assistant' : 'user']"
          >
            <span class="role">{{ message.role === "assistant" ? "系统" : "用户" }}</span>

            <div v-if="message.selectedKnowledgeBases?.length" class="route-meta">
              <span class="route-chip">命中知识库</span>
              <span class="route-reason">
                {{ message.selectedKnowledgeBases.map((item) => item.name).join(" / ") }}
              </span>
            </div>

            <div v-if="message.selectedKnowledgeBases?.length" class="kb-list">
              <div v-for="item in message.selectedKnowledgeBases" :key="item.id" class="kb-item">
                <strong>{{ item.name }}</strong>
                <span>得分：{{ Number(item.score).toFixed(3) }}</span>
                <span>{{ item.selectionReason }}</span>
              </div>
            </div>

            <div v-if="message.routeType" class="route-meta">
              <span class="route-chip">{{ routeLabelMap[message.routeType] || message.routeType }}</span>
              <span class="route-reason">{{ message.routeReason }}</span>
            </div>

            <div v-if="message.selectedTool" class="route-meta">
              <span class="route-chip">工具：{{ message.selectedTool }}</span>
              <span class="route-reason">{{ message.selectedToolReason }}</span>
            </div>

            <div v-if="message.awaitingHumanReview" class="route-meta">
              <span class="route-chip">待人工审核</span>
              <span class="route-reason">{{ message.humanReviewReason || "该回答进入人工审核队列。" }}</span>
            </div>
            <div v-else-if="message.humanReviewRequired" class="route-meta">
              <span class="route-chip">建议人工确认</span>
              <span class="route-reason">{{ message.humanReviewReason }}</span>
            </div>

            <p>{{ message.content }}</p>

            <div v-if="message.agentRunId" class="route-meta">
              <RouterLink class="route-chip route-link" :to="`/runs?agent_run_id=${message.agentRunId}`">
                查看本次运行记录
              </RouterLink>
            </div>

            <div v-if="message.citations?.length" class="citation-list">
              <strong>引用来源：</strong>
              <ul>
                <li v-for="item in message.citations" :key="`${message.id}-${item.chunk_id}`">
                  {{ item.knowledge_base_name }} / {{ item.filename }} / 分块 {{ item.chunk_index }} / 相关度
                  {{ Number(item.score).toFixed(3) }}
                </li>
              </ul>
            </div>

            <div
              v-if="message.role === 'assistant' && message.agentRunId && !message.awaitingHumanReview"
              class="route-meta"
            >
              <button
                type="button"
                class="route-chip route-link"
                :disabled="message.feedbackLoading || message.feedback === 'positive'"
                @click="submitFeedback(message, 'positive')"
              >
                {{ message.feedback === "positive" ? "已反馈：有帮助" : "有帮助" }}
              </button>
              <button
                type="button"
                class="route-chip route-link"
                :disabled="message.feedbackLoading || message.feedback === 'negative'"
                @click="submitFeedback(message, 'negative')"
              >
                {{ message.feedback === "negative" ? "已反馈：没帮助" : "没帮助" }}
              </button>
            </div>
          </div>
        </div>

        <div class="composer">
          <select v-model="selectedKnowledgeBaseId" :disabled="knowledgeBases.length === 0">
            <option value="">自动选择知识库</option>
            <option v-for="item in knowledgeBases" :key="item.id" :value="String(item.id)">
              {{ item.name }}
            </option>
          </select>
          <textarea
            v-model="question"
            :disabled="knowledgeBases.length === 0"
            placeholder="输入你的问题..."
            rows="5"
          />
          <button type="button" @click="askQuestion" :disabled="loading || knowledgeBases.length === 0">
            {{ loading ? "生成中..." : "发送" }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import apiClient from "../api/client";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const routeLabelMap = {
  qa: "标准问答",
  summary: "总结模式",
  comparison: "对比模式",
};

const knowledgeBases = ref([]);
const conversations = ref([]);
const selectedKnowledgeBaseId = ref("");
const question = ref("");
const loading = ref(false);
const activeConversationId = ref(null);
const pageMessage = ref("");
const messages = ref(buildWelcomeMessages());

function buildWelcomeMessages() {
  return [
    {
      id: "welcome",
      role: "assistant",
      content: "你可以直接提问，系统会自动选择最相关的知识库候选并执行工作流。",
      citations: [],
      routeType: "",
      routeReason: "",
      selectedKnowledgeBases: [],
      selectedTool: "",
      selectedToolReason: "",
      humanReviewRequired: false,
      humanReviewReason: "",
      awaitingHumanReview: false,
      feedback: "",
      feedbackLoading: false,
      agentRunId: null,
    },
  ];
}

function resetMessages() {
  messages.value = buildWelcomeMessages();
}

async function loadKnowledgeBases() {
  try {
    const { data } = await apiClient.get("/knowledge-bases");
    knowledgeBases.value = data;
    pageMessage.value =
      data.length === 0 ? "当前还没有知识库，请先去知识库页面创建并上传文档。" : "";
  } catch {
    pageMessage.value = "加载知识库失败，请刷新页面后重试。";
  }
}

async function loadConversations() {
  const { data } = await apiClient.get("/conversations");
  conversations.value = data;
}

async function selectConversation(conversationId) {
  activeConversationId.value = conversationId;
  const { data } = await apiClient.get(`/conversations/${conversationId}/messages`);
  messages.value = data.map((item) => normalizeMessage(item));
}

function startNewConversation() {
  activeConversationId.value = null;
  resetMessages();
}

async function askQuestion() {
  const currentQuestion = question.value.trim();
  if (!currentQuestion) return;

  if (knowledgeBases.value.length === 0) {
    pageMessage.value = "当前没有可用知识库，无法发起问答。";
    return;
  }

  pageMessage.value = "";

  const userMessage = buildUserMessage(currentQuestion);
  const assistantMessage = buildAssistantMessage();
  messages.value.push(userMessage);
  messages.value.push(assistantMessage);

  loading.value = true;
  question.value = "";

  try {
    await streamAsk(currentQuestion, assistantMessage);
    await loadConversations();
  } catch {
    assistantMessage.content = "流式问答失败，正在尝试普通问答。";
    await askQuestionFallback(currentQuestion, assistantMessage);
  } finally {
    loading.value = false;
  }
}

function buildUserMessage(content) {
  return {
    id: `user-${Date.now()}`,
    role: "user",
    content,
    citations: [],
    routeType: "",
    routeReason: "",
    selectedKnowledgeBases: [],
    selectedTool: "",
    selectedToolReason: "",
    humanReviewRequired: false,
    humanReviewReason: "",
    awaitingHumanReview: false,
    feedback: "",
    feedbackLoading: false,
    agentRunId: null,
  };
}

function buildAssistantMessage() {
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: "",
    citations: [],
    routeType: "",
    routeReason: "",
    selectedKnowledgeBases: [],
    selectedTool: "",
    selectedToolReason: "",
    humanReviewRequired: false,
    humanReviewReason: "",
    awaitingHumanReview: false,
    feedback: "",
    feedbackLoading: false,
    agentRunId: null,
  };
}

function normalizeMessage(item) {
  return {
    id: item.id,
    role: item.role,
    content: item.content,
    citations: item.citations_json || [],
    routeType: item.route_type || "",
    routeReason: item.route_reason || "",
    selectedKnowledgeBases: normalizeKnowledgeBases(item.selected_knowledge_bases),
    selectedTool: item.selected_tool || "",
    selectedToolReason: item.selected_tool_reason || "",
    humanReviewRequired: item.human_review_required || false,
    humanReviewReason: item.human_review_reason || "",
    awaitingHumanReview: item.awaiting_human_review || false,
    feedback: item.feedback_rating || "",
    feedbackLoading: false,
    agentRunId: item.agent_run_id || null,
  };
}

async function streamAsk(currentQuestion, assistantMessage) {
  const payload = { question: currentQuestion, top_k: 4 };
  if (selectedKnowledgeBaseId.value) payload.knowledge_base_id = Number(selectedKnowledgeBaseId.value);
  if (activeConversationId.value) payload.conversation_id = activeConversationId.value;

  const response = await fetch(`${apiBaseUrl}/chat/ask/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error("流式接口调用失败。");
  if (!response.body) throw new Error("流式响应为空。");

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const rawEvent of events) {
      handleSseEvent(rawEvent, assistantMessage);
    }
  }

  if (buffer.trim()) handleSseEvent(buffer, assistantMessage);
}

function handleSseEvent(rawEvent, assistantMessage) {
  const lines = rawEvent.split("\n");
  let eventName = "";
  let dataText = "";

  for (const line of lines) {
    if (line.startsWith("event: ")) eventName = line.slice(7).trim();
    if (line.startsWith("data: ")) dataText += line.slice(6);
  }

  if (!dataText) return;
  const payload = JSON.parse(dataText);

  if (eventName === "meta") {
    activeConversationId.value = payload.conversation_id;
    assistantMessage.agentRunId = payload.agent_run_id || null;
    assistantMessage.routeType = payload.route_type || "";
    assistantMessage.routeReason = payload.route_reason || "";
    assistantMessage.selectedTool = payload.selected_tool || "";
    assistantMessage.selectedToolReason = payload.selected_tool_reason || "";
    assistantMessage.humanReviewRequired = payload.human_review_required || false;
    assistantMessage.humanReviewReason = payload.human_review_reason || "";
    assistantMessage.selectedKnowledgeBases = normalizeKnowledgeBases(payload.selected_knowledge_bases);
    return;
  }

  if (eventName === "chunk") {
    assistantMessage.content += payload.content;
    return;
  }

  if (eventName === "done") {
    assistantMessage.agentRunId = payload.agent_run_id || assistantMessage.agentRunId;
    assistantMessage.citations = payload.citations || [];
    assistantMessage.routeType = payload.route_type || assistantMessage.routeType;
    assistantMessage.routeReason = payload.route_reason || assistantMessage.routeReason;
    assistantMessage.selectedTool = payload.selected_tool || assistantMessage.selectedTool;
    assistantMessage.selectedToolReason = payload.selected_tool_reason || assistantMessage.selectedToolReason;
    assistantMessage.humanReviewRequired = payload.human_review_required || assistantMessage.humanReviewRequired;
    assistantMessage.humanReviewReason = payload.human_review_reason || assistantMessage.humanReviewReason;
    assistantMessage.awaitingHumanReview = payload.awaiting_human_review || false;
    assistantMessage.selectedKnowledgeBases =
      normalizeKnowledgeBases(payload.selected_knowledge_bases) || assistantMessage.selectedKnowledgeBases;
  }
}

async function askQuestionFallback(currentQuestion, assistantMessage) {
  try {
    const payload = { question: currentQuestion, top_k: 4 };
    if (selectedKnowledgeBaseId.value) payload.knowledge_base_id = Number(selectedKnowledgeBaseId.value);
    if (activeConversationId.value) payload.conversation_id = activeConversationId.value;

    const { data } = await apiClient.post("/chat/ask", payload);
    activeConversationId.value = data.conversation_id;
    assistantMessage.agentRunId = data.agent_run_id || null;
    assistantMessage.content = data.answer;
    assistantMessage.citations = data.citations;
    assistantMessage.routeType = data.route_type || "";
    assistantMessage.routeReason = data.route_reason || "";
    assistantMessage.selectedTool = data.selected_tool || "";
    assistantMessage.selectedToolReason = data.selected_tool_reason || "";
    assistantMessage.humanReviewRequired = data.human_review_required || false;
    assistantMessage.humanReviewReason = data.human_review_reason || "";
    assistantMessage.awaitingHumanReview = data.awaiting_human_review || false;
    assistantMessage.selectedKnowledgeBases = normalizeKnowledgeBases(data.selected_knowledge_bases);
  } catch (error) {
    assistantMessage.content = formatRequestError(error);
    assistantMessage.citations = [];
    assistantMessage.routeType = "";
    assistantMessage.routeReason = "";
    assistantMessage.selectedKnowledgeBases = [];
    assistantMessage.selectedTool = "";
    assistantMessage.selectedToolReason = "";
    assistantMessage.humanReviewRequired = false;
    assistantMessage.humanReviewReason = "";
    assistantMessage.awaitingHumanReview = false;
    assistantMessage.agentRunId = null;
  }
}

async function submitFeedback(message, rating) {
  if (!message.agentRunId || message.feedbackLoading) return;
  message.feedbackLoading = true;
  try {
    await apiClient.post("/feedback", {
      agent_run_id: message.agentRunId,
      conversation_id: activeConversationId.value,
      rating,
    });
    message.feedback = rating;
  } catch (error) {
    pageMessage.value = error.response?.data?.detail || "提交反馈失败，请稍后重试。";
  } finally {
    message.feedbackLoading = false;
  }
}

function normalizeKnowledgeBases(items) {
  if (!Array.isArray(items)) return [];
  return items.map((item) => ({
    id: item.id,
    name: item.name,
    description: item.description,
    selectionReason: item.selection_reason,
    score: item.score,
  }));
}

function formatRequestError(error) {
  const detail = error.response?.data?.detail;
  if (Array.isArray(detail)) return "请求参数校验失败，请检查输入内容。";
  return detail || "问答请求失败，请稍后重试。";
}

onMounted(async () => {
  await loadKnowledgeBases();
  await loadConversations();
});
</script>
