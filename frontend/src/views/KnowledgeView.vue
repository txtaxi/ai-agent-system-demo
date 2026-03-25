<template>
  <section class="panel">
    <p class="panel-label">知识库模块</p>
    <h2>知识库管理</h2>
    <p class="section-intro">
      当前页面支持知识库创建、文档上传、文档处理和分块查看，适合做数据入库与检索前调试。
    </p>

    <div v-if="message.text" :class="['message-banner', message.type]">
      {{ message.text }}
    </div>

    <div class="knowledge-layout">
      <section class="card">
        <h3>创建知识库</h3>
        <div class="form-grid">
          <input v-model="knowledgeBaseForm.name" placeholder="请输入知识库名称" />
          <textarea
            v-model="knowledgeBaseForm.description"
            rows="3"
            placeholder="请输入知识库描述"
          />
          <button type="button" @click="createKnowledgeBase" :disabled="loading.createKb">
            {{ loading.createKb ? "创建中..." : "创建知识库" }}
          </button>
        </div>
      </section>

      <section class="card">
        <h3>上传文档</h3>
        <div class="form-grid">
          <select v-model="selectedKnowledgeBaseId">
            <option value="">请选择知识库</option>
            <option v-for="item in knowledgeBases" :key="item.id" :value="String(item.id)">
              {{ item.name }}
            </option>
          </select>
          <input type="file" @change="handleFileChange" />
          <button type="button" @click="uploadDocument" :disabled="loading.upload">
            {{ loading.upload ? "上传中..." : "上传文档" }}
          </button>
        </div>
      </section>
    </div>

    <section class="card list-card compact-scroll">
      <div class="list-header">
        <h3>知识库列表</h3>
        <button type="button" @click="loadKnowledgeBases" :disabled="loading.loadKb">
          {{ loading.loadKb ? "刷新中..." : "刷新" }}
        </button>
      </div>

      <div v-if="knowledgeBases.length === 0" class="empty-state">暂无知识库。</div>
      <ul v-else class="simple-list">
        <li v-for="item in knowledgeBases" :key="item.id">
          <strong>{{ item.name }}</strong>
          <span>{{ item.description || "暂无描述" }}</span>
        </li>
      </ul>
    </section>

    <section class="card list-card compact-scroll">
      <div class="list-header">
        <h3>文档列表</h3>
        <button type="button" @click="loadDocuments" :disabled="loading.loadDocs">
          {{ loading.loadDocs ? "刷新中..." : "刷新" }}
        </button>
      </div>

      <div v-if="documents.length === 0" class="empty-state">暂无文档。</div>
      <div v-else class="document-list">
        <article v-for="doc in documents" :key="doc.id" class="document-item">
          <div class="document-meta">
            <strong>{{ doc.filename }}</strong>
            <span>状态：{{ doc.status }}</span>
            <span>类型：{{ doc.file_type }}</span>
            <span v-if="doc.error_message">错误：{{ doc.error_message }}</span>
          </div>
          <div class="document-actions">
            <button type="button" @click="processCurrentDocument(doc.id)">处理文档</button>
            <button type="button" @click="loadChunks(doc.id)">查看分块</button>
          </div>
        </article>
      </div>
    </section>

    <section class="card list-card compact-scroll">
      <div class="list-header">
        <h3>文档分块</h3>
        <span v-if="activeDocumentId">当前文档 ID：{{ activeDocumentId }}</span>
      </div>

      <div v-if="chunks.length === 0" class="empty-state">暂无分块数据。</div>
      <div v-else class="chunk-list">
        <article v-for="chunk in chunks" :key="chunk.id" class="chunk-item">
          <strong>分块 {{ chunk.chunk_index }}</strong>
          <p>{{ chunk.content }}</p>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from "vue";

import apiClient from "../api/client";

const knowledgeBases = ref([]);
const documents = ref([]);
const chunks = ref([]);
const activeDocumentId = ref(null);
const selectedKnowledgeBaseId = ref("");
const selectedFile = ref(null);

const knowledgeBaseForm = reactive({
  name: "",
  description: "",
});

const loading = reactive({
  createKb: false,
  loadKb: false,
  upload: false,
  loadDocs: false,
});

const message = reactive({
  text: "",
  type: "info",
});

function setMessage(text, type = "info") {
  message.text = text;
  message.type = type;
}

async function loadKnowledgeBases() {
  loading.loadKb = true;
  try {
    const { data } = await apiClient.get("/knowledge-bases");
    knowledgeBases.value = data;
    if (!selectedKnowledgeBaseId.value && data.length > 0) {
      selectedKnowledgeBaseId.value = String(data[0].id);
    }
  } catch (error) {
    setMessage(error.response?.data?.detail || "获取知识库失败。", "error");
  } finally {
    loading.loadKb = false;
  }
}

async function createKnowledgeBase() {
  if (!knowledgeBaseForm.name.trim()) {
    setMessage("请先输入知识库名称。", "error");
    return;
  }

  loading.createKb = true;
  try {
    await apiClient.post("/knowledge-bases", {
      name: knowledgeBaseForm.name,
      description: knowledgeBaseForm.description,
    });
    knowledgeBaseForm.name = "";
    knowledgeBaseForm.description = "";
    setMessage("知识库创建成功。", "success");
    await loadKnowledgeBases();
    await loadDocuments();
  } catch (error) {
    setMessage(error.response?.data?.detail || "创建知识库失败。", "error");
  } finally {
    loading.createKb = false;
  }
}

function handleFileChange(event) {
  selectedFile.value = event.target.files?.[0] || null;
}

async function uploadDocument() {
  if (!selectedKnowledgeBaseId.value) {
    setMessage("请先选择知识库。", "error");
    return;
  }
  if (!selectedFile.value) {
    setMessage("请先选择文件。", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", selectedFile.value);

  loading.upload = true;
  try {
    await apiClient.post(`/documents/upload?knowledge_base_id=${selectedKnowledgeBaseId.value}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    setMessage("文档上传成功。", "success");
    selectedFile.value = null;
    await loadDocuments();
  } catch (error) {
    setMessage(error.response?.data?.detail || "文档上传失败。", "error");
  } finally {
    loading.upload = false;
  }
}

async function loadDocuments() {
  loading.loadDocs = true;
  try {
    const query = selectedKnowledgeBaseId.value
      ? `/documents?knowledge_base_id=${selectedKnowledgeBaseId.value}`
      : "/documents";
    const { data } = await apiClient.get(query);
    documents.value = data;
  } catch (error) {
    setMessage(error.response?.data?.detail || "获取文档列表失败。", "error");
  } finally {
    loading.loadDocs = false;
  }
}

async function processCurrentDocument(documentId) {
  try {
    const { data } = await apiClient.post(`/documents/${documentId}/process`);
    setMessage(data.message, "success");
    await loadDocuments();
    await loadChunks(documentId);
  } catch (error) {
    setMessage(error.response?.data?.detail || "文档处理失败。", "error");
  }
}

async function loadChunks(documentId) {
  activeDocumentId.value = documentId;
  try {
    const { data } = await apiClient.get(`/documents/${documentId}/chunks`);
    chunks.value = data;
  } catch (error) {
    setMessage(error.response?.data?.detail || "获取文档分块失败。", "error");
  }
}

watch(selectedKnowledgeBaseId, async () => {
  await loadDocuments();
});

onMounted(async () => {
  await loadKnowledgeBases();
  await loadDocuments();
});
</script>
