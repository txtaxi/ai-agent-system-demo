<template>
  <section class="panel">
    <p class="panel-label">项目总览</p>
    <h2>企业知识库智能体系统</h2>
    <p class="section-intro">
      当前版本已经完成 Agent 主链路收口，适合用于项目演示、求职讲解和后续企业级扩展。
    </p>

    <div class="summary-strip">
      <article class="summary-box">
        <span class="summary-title">当前定位</span>
        <strong>完整 Agent 项目</strong>
      </article>
      <article class="summary-box">
        <span class="summary-title">核心编排</span>
        <strong>LangGraph</strong>
      </article>
      <article class="summary-box">
        <span class="summary-title">核心场景</span>
        <strong>企业知识库问答</strong>
      </article>
      <article class="summary-box">
        <span class="summary-title">下一阶段</span>
        <strong>企业级扩展</strong>
      </article>
    </div>

    <div class="card-grid">
      <article class="card">
        <h3>知识与检索</h3>
        <p>支持文档上传、解析、分块、向量化、自动选库、跨库检索和引用返回。</p>
      </article>
      <article class="card">
        <h3>智能体工作流</h3>
        <p>支持任务路由、查询改写、工具选择、重排、补充检索和 LangGraph 编排。</p>
      </article>
      <article class="card">
        <h3>可观测与闭环</h3>
        <p>支持运行记录、反馈统计、负反馈样本回放和人工审核暂停恢复。</p>
      </article>
    </div>

    <section class="card list-card">
      <div class="list-header">
        <h3>当前系统能力</h3>
      </div>
      <div class="capability-grid">
        <span class="route-chip">知识库管理</span>
        <span class="route-chip">多格式文档处理</span>
        <span class="route-chip">多策略分块</span>
        <span class="route-chip">RAG 问答</span>
        <span class="route-chip">自动选库</span>
        <span class="route-chip">跨库检索</span>
        <span class="route-chip">任务路由</span>
        <span class="route-chip">查询改写</span>
        <span class="route-chip">工具选择</span>
        <span class="route-chip">LangGraph</span>
        <span class="route-chip">运行记录</span>
        <span class="route-chip">反馈闭环</span>
        <span class="route-chip">HITL</span>
      </div>
    </section>
  </section>
</template>

<script setup>
</script>
