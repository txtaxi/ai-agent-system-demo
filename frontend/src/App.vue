<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-top">
        <p class="eyebrow">企业知识库智能体</p>
        <h1>Agent 项目工作台</h1>
        <p class="subtitle">
          当前版本已完成知识库、RAG、自动选库、LangGraph、运行记录、反馈闭环和 HITL。
        </p>
      </div>

      <nav class="nav">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/knowledge">知识库</RouterLink>
        <RouterLink to="/chat">对话</RouterLink>
        <RouterLink to="/runs">运行记录</RouterLink>
        <RouterLink to="/feedback">反馈统计</RouterLink>
      </nav>

      <div class="sidebar-footer">
        <span class="sidebar-tag">求职版收口</span>
        <span class="sidebar-tag sidebar-tag-muted">企业级可扩展</span>
      </div>
    </aside>

    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
</script>
