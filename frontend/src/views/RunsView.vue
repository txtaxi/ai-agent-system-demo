<template>
  <section class="panel">
    <p class="panel-label">运行记录</p>
    <h2>工作流追踪</h2>
    <p class="section-intro">
      这里用于查看 LangGraph 工作流的运行记录，也支持对待人工审核的运行记录执行通过或驳回。
    </p>

    <div v-if="message" class="message-banner error">
      {{ message }}
    </div>

    <div class="knowledge-layout">
      <section class="card">
        <h3>过滤条件</h3>
        <div class="form-grid">
          <select v-model="selectedConversationId" @change="loadRuns">
            <option value="">全部会话</option>
            <option v-for="item in conversations" :key="item.id" :value="String(item.id)">
              {{ item.title }}
            </option>
          </select>
          <button type="button" @click="loadRuns" :disabled="loadingRuns">
            {{ loadingRuns ? "加载中..." : "刷新运行记录" }}
          </button>
        </div>
      </section>

      <section class="card">
        <h3>说明</h3>
        <ul class="simple-list">
          <li>
            <strong>状态</strong>
            <span>支持查看 running、pending_review、completed、rejected、failed。</span>
          </li>
          <li>
            <strong>人工审核</strong>
            <span>高风险问答会进入待审核状态，审核后再决定是否进入正式会话。</span>
          </li>
        </ul>
      </section>
    </div>

    <section class="card list-card compact-scroll">
      <div class="list-header">
        <h3>运行记录列表</h3>
        <span v-if="runs.length">共 {{ runs.length }} 条</span>
      </div>

      <div v-if="runs.length === 0" class="empty-state">暂无运行记录。</div>
      <div v-else class="document-list">
        <article v-for="run in runs" :key="run.id" class="document-item" @click="selectRun(run.id)">
          <div class="document-meta">
            <strong>#{{ run.id }} · {{ run.route || "未完成路由" }}</strong>
            <span>状态：{{ run.status }}</span>
            <span>会话：{{ run.conversation_id || "未关联" }}</span>
            <span>问题：{{ run.user_query }}</span>
          </div>
        </article>
      </div>
    </section>

    <section class="card list-card compact-scroll">
      <div class="list-header">
        <h3>运行详情</h3>
        <span v-if="activeRun">当前记录 ID：{{ activeRun.id }}</span>
      </div>

      <div v-if="!activeRun" class="empty-state">请选择一条运行记录查看详情。</div>
      <div v-else class="chunk-list">
        <article class="chunk-item">
          <strong>基础信息</strong>
          <p>问题：{{ activeRun.user_query }}</p>
          <p>路由：{{ activeRun.route || "未完成" }}</p>
          <p>状态：{{ activeRun.status }}</p>
          <p>开始时间：{{ formatDate(activeRun.started_at) }}</p>
          <p>结束时间：{{ activeRun.finished_at ? formatDate(activeRun.finished_at) : "运行中" }}</p>
        </article>

        <article class="chunk-item">
          <strong>执行摘要</strong>
          <p>任务路由：{{ activeRun.summary.route_type || "未知" }}</p>
          <p>路由原因：{{ activeRun.summary.route_reason || "暂无" }}</p>
          <p>改写查询：{{ activeRun.summary.rewritten_query || "未改写" }}</p>
          <p>改写评估：{{ activeRun.summary.rewrite_assessment_reason || "暂无" }}</p>
          <p>选中工具：{{ activeRun.summary.selected_tool || "暂无" }}</p>
          <p>工具原因：{{ activeRun.summary.selected_tool_reason || "暂无" }}</p>
          <p>检索质量：{{ activeRun.summary.retrieval_quality || "暂无" }}</p>
          <p>重排：{{ formatYesNo(activeRun.summary.rerank_applied) }}</p>
          <p>人工确认建议：{{ formatHumanReview(activeRun.summary.human_review_required) }}</p>
          <p>审核状态：{{ activeRun.summary.review_status || "暂无" }}</p>
          <p>审核备注：{{ activeRun.summary.review_comment || "暂无" }}</p>
          <p>上下文数量：{{ activeRun.summary.context_count }}</p>
        </article>

        <article v-if="activeRun.summary.retrieval_queries.length" class="chunk-item">
          <strong>检索查询</strong>
          <ul>
            <li v-for="item in activeRun.summary.retrieval_queries" :key="`${activeRun.id}-${item}`">
              {{ item }}
            </li>
          </ul>
        </article>

        <article v-if="activeRun.status === 'pending_review'" class="chunk-item">
          <strong>人工审核操作</strong>
          <div class="form-grid">
            <textarea v-model="reviewComment" rows="3" placeholder="可填写审核备注" />
            <div class="document-actions">
              <button type="button" @click="reviewRun('approve')" :disabled="reviewLoading">
                {{ reviewLoading ? "处理中..." : "审核通过" }}
              </button>
              <button type="button" @click="reviewRun('reject')" :disabled="reviewLoading">
                {{ reviewLoading ? "处理中..." : "审核驳回" }}
              </button>
            </div>
          </div>
        </article>

        <article v-if="activeRun.summary.selected_knowledge_bases.length" class="chunk-item">
          <strong>命中知识库</strong>
          <ul>
            <li
              v-for="item in activeRun.summary.selected_knowledge_bases"
              :key="`${activeRun.id}-${item.id}`"
            >
              {{ item.name }} / 得分 {{ formatScore(item.score) }} / {{ item.selection_reason }}
            </li>
          </ul>
        </article>

        <article v-for="(step, index) in activeRun.steps" :key="`${activeRun.id}-${index}`" class="chunk-item">
          <strong>{{ step.node }}</strong>
          <p>{{ step.detail }}</p>
          <pre v-if="step.meta">{{ formatMeta(step.meta) }}</pre>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import apiClient from "../api/client";

const route = useRoute();
const conversations = ref([]);
const runs = ref([]);
const activeRun = ref(null);
const selectedConversationId = ref("");
const loadingRuns = ref(false);
const reviewLoading = ref(false);
const reviewComment = ref("");
const message = ref("");

async function loadConversations() {
  try {
    const { data } = await apiClient.get("/conversations");
    conversations.value = data;
  } catch {
    message.value = "加载会话列表失败。";
  }
}

async function loadRuns() {
  loadingRuns.value = true;
  message.value = "";
  activeRun.value = null;
  try {
    const query = selectedConversationId.value
      ? `/agent-runs?conversation_id=${selectedConversationId.value}`
      : "/agent-runs";
    const { data } = await apiClient.get(query);
    runs.value = data;
  } catch (error) {
    message.value = error.response?.data?.detail || "加载运行记录失败。";
  } finally {
    loadingRuns.value = false;
  }
}

async function selectRun(runId) {
  try {
    const { data } = await apiClient.get(`/agent-runs/${runId}`);
    activeRun.value = data;
    reviewComment.value = data.summary.review_comment || "";
  } catch (error) {
    message.value = error.response?.data?.detail || "加载运行详情失败。";
  }
}

async function reviewRun(action) {
  if (!activeRun.value) return;
  reviewLoading.value = true;
  message.value = "";
  try {
    const { data } = await apiClient.post(`/agent-runs/${activeRun.value.id}/review`, {
      action,
      comment: reviewComment.value || null,
    });
    activeRun.value = data;
    await loadRuns();
    message.value = action === "approve" ? "已审核通过。" : "已审核驳回。";
  } catch (error) {
    message.value = error.response?.data?.detail || "人工审核操作失败。";
  } finally {
    reviewLoading.value = false;
  }
}

function formatMeta(meta) {
  return JSON.stringify(meta, null, 2);
}

function formatScore(score) {
  return Number(score || 0).toFixed(3);
}

function formatYesNo(value) {
  if (value === true) return "已执行";
  if (value === false) return "未执行";
  return "暂无";
}

function formatHumanReview(value) {
  if (value === true) return "建议人工确认";
  if (value === false) return "无需人工确认";
  return "暂无";
}

function formatDate(value) {
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

onMounted(async () => {
  await loadConversations();
  await loadRuns();
  const runId = route.query.agent_run_id;
  if (runId) {
    await selectRun(Number(runId));
  }
});
</script>
