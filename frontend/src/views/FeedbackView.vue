<template>
  <section class="panel">
    <p class="panel-label">反馈统计</p>
    <h2>Eval 面板</h2>
    <p class="section-intro">
      这里用于查看当前系统的用户反馈，帮助定位哪类任务、工具或检索质量更容易出现问题。
    </p>

    <div v-if="message" class="message-banner error">
      {{ message }}
    </div>

    <div class="card-grid">
      <article class="card">
        <h3>反馈总量</h3>
        <p>{{ stats.total }}</p>
      </article>
      <article class="card">
        <h3>有帮助</h3>
        <p>{{ stats.positive }} / {{ formatRate(stats.positive_rate) }}</p>
      </article>
      <article class="card">
        <h3>没帮助</h3>
        <p>{{ stats.negative }} / {{ formatRate(stats.negative_rate) }}</p>
      </article>
    </div>

    <section class="card list-card compact-scroll">
      <div class="list-header">
        <h3>统计概览</h3>
        <button type="button" @click="loadAll" :disabled="loading">
          {{ loading ? "加载中..." : "刷新统计" }}
        </button>
      </div>

      <div class="analytics-grid">
        <article class="analytics-card" v-for="block in analyticsBlocks" :key="block.key">
          <h4>{{ block.title }}</h4>
          <div v-if="block.items.length" class="document-list">
            <article v-for="item in block.items" :key="`${block.key}-${item.label}`" class="document-item">
              <div class="document-meta">
                <strong>{{ item.label }}</strong>
                <span>总反馈：{{ item.total }}</span>
                <span>有帮助：{{ item.positive }}</span>
                <span>没帮助：{{ item.negative }}</span>
              </div>
            </article>
          </div>
          <div v-else class="empty-state">暂无数据。</div>
        </article>
      </div>
    </section>

    <section class="card list-card compact-scroll">
      <div class="list-header">
        <h3>负反馈样本</h3>
        <span class="section-tip">用于回放失败案例并查看对应执行链路。</span>
      </div>

      <div class="form-grid compact-grid">
        <select v-model="filters.route">
          <option value="">全部路由</option>
          <option v-for="item in routeOptions" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="filters.tool">
          <option value="">全部工具</option>
          <option v-for="item in toolOptions" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="filters.knowledgeBase">
          <option value="">全部知识库</option>
          <option v-for="item in knowledgeBaseOptions" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="filters.humanReview">
          <option value="">全部人工确认状态</option>
          <option value="required">建议人工确认</option>
          <option value="not_required">无需人工确认</option>
          <option value="unknown">未知</option>
        </select>
      </div>

      <div v-if="filteredNegativeSamples.length === 0" class="empty-state">
        当前筛选条件下没有负反馈样本。
      </div>
      <div v-else class="document-list">
        <article v-for="item in filteredNegativeSamples" :key="item.feedback_id" class="document-item">
          <div class="document-meta">
            <strong>{{ item.user_query }}</strong>
            <span>路由：{{ item.route }}</span>
            <span>工具：{{ item.selected_tool }}</span>
            <span>检索质量：{{ item.retrieval_quality }}</span>
            <span>人工确认：{{ formatHumanReview(item.human_review_required) }}</span>
            <span>知识库：{{ item.knowledge_base_names.length ? item.knowledge_base_names.join(" / ") : "未知" }}</span>
            <span>运行记录：{{ item.agent_run_id }}</span>
            <span>反馈时间：{{ formatDate(item.created_at) }}</span>
            <span v-if="item.comment">备注：{{ item.comment }}</span>
          </div>
          <RouterLink class="secondary-link" :to="`/runs?agent_run_id=${item.agent_run_id}`">
            查看对应运行记录
          </RouterLink>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import apiClient from "../api/client";

const loading = ref(false);
const message = ref("");
const stats = ref({
  total: 0,
  positive: 0,
  negative: 0,
  positive_rate: 0,
  negative_rate: 0,
  by_route: [],
  by_tool: [],
  by_retrieval_quality: [],
  by_human_review: [],
  by_knowledge_base: [],
});
const negativeSamples = ref([]);
const filters = reactive({
  route: "",
  tool: "",
  knowledgeBase: "",
  humanReview: "",
});

const analyticsBlocks = computed(() => [
  { key: "route", title: "按路由统计", items: stats.value.by_route },
  { key: "tool", title: "按工具统计", items: stats.value.by_tool },
  { key: "quality", title: "按检索质量统计", items: stats.value.by_retrieval_quality },
  { key: "review", title: "按人工确认统计", items: stats.value.by_human_review },
  { key: "kb", title: "按知识库统计", items: stats.value.by_knowledge_base },
]);

const routeOptions = computed(() => uniqueOptions(negativeSamples.value.map((item) => item.route)));
const toolOptions = computed(() => uniqueOptions(negativeSamples.value.map((item) => item.selected_tool)));
const knowledgeBaseOptions = computed(() =>
  uniqueOptions(negativeSamples.value.flatMap((item) => item.knowledge_base_names || []))
);

const filteredNegativeSamples = computed(() =>
  negativeSamples.value.filter((item) => {
    if (filters.route && item.route !== filters.route) return false;
    if (filters.tool && item.selected_tool !== filters.tool) return false;
    if (filters.knowledgeBase && !(item.knowledge_base_names || []).includes(filters.knowledgeBase)) {
      return false;
    }
    if (filters.humanReview === "required" && item.human_review_required !== true) return false;
    if (filters.humanReview === "not_required" && item.human_review_required !== false) return false;
    if (filters.humanReview === "unknown" && item.human_review_required != null) return false;
    return true;
  })
);

async function loadAll() {
  loading.value = true;
  message.value = "";
  try {
    const [statsResponse, samplesResponse] = await Promise.all([
      apiClient.get("/feedback/stats"),
      apiClient.get("/feedback/negative-samples"),
    ]);
    stats.value = statsResponse.data;
    negativeSamples.value = samplesResponse.data;
  } catch (error) {
    message.value = error.response?.data?.detail || "加载反馈统计失败。";
  } finally {
    loading.value = false;
  }
}

function uniqueOptions(items) {
  return [...new Set(items.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b)));
}

function formatRate(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "-";
}

function formatHumanReview(value) {
  if (value === true) return "建议人工确认";
  if (value === false) return "无需人工确认";
  return "未知";
}

onMounted(loadAll);
</script>
