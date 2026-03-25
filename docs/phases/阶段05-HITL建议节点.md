# 阶段05-HITL建议节点

## 阶段目标

在当前企业知识库 Agent 系统中加入最小版 `HITL` 能力。

本阶段不追求真正的“暂停 -> 人工审核 -> 恢复执行”，而是先完成下面三件事：

- 识别哪些问题属于高风险问题
- 在工作流中增加人工确认需求评估节点
- 将人工确认建议写入问答响应和运行记录

## 为什么先做建议，而不是直接做暂停恢复

原因有三点：

1. 当前系统已经具备完整的主链路，但还没有“恢复执行”所需的持久状态机设计。
2. 对求职项目来说，先体现“系统有风险意识”比一开始把完整审批系统做重更划算。
3. 先把“识别高风险分支”落地，后面再扩展成真正的人工审核节点会更稳。

## 本阶段核心设计

### 1. 新增人工确认评估工具

新增工具：

- `assess_human_review_need`

职责：

- 判断当前问题是否需要人工确认
- 返回：
  - `human_review_required`
  - `human_review_reason`

当前判断依据：

- 问题是否包含高风险关键词
- 当前检索质量是否不足
- 当前工具类型是否说明证据还不充分

### 2. 在 LangGraph 中增加节点

新增节点：

- `assess_human_review`

位置：

```text
route_question
  ->
rewrite_query
  ->
assess_rewrite
  ->
tool_select
  ->
search_knowledge
  ->
analyze_retrieval
  ->
decide_more_context
  ->
rerank_results
  ->
assess_human_review
  ->
prepare_*_context
  ->
generate_answer
```

这个位置的考虑是：

- 已经拿到了检索质量和重排结果
- 能更合理地判断当前证据是否足够
- 不会过早触发人工确认

### 3. 回答层面的最小反馈

如果命中人工确认建议，当前系统会：

- 在最终回答前加一条提示
- 在运行记录摘要中明确记录建议原因

这意味着用户和开发者都能知道：

- 这次不是单纯自动回答
- 系统认为这类问题风险较高

## 本阶段涉及文件

### 后端

- `backend/app/agent/tools.py`
  - 新增 `assess_human_review_need`

- `backend/app/agent/__init__.py`
  - 导出人工确认评估工具

- `backend/app/agent/workflow.py`
  - 新增 `assess_human_review` 节点
  - 增加 `human_review_required`
  - 增加 `human_review_reason`
  - 将人工确认建议写入 trace payload

- `backend/app/schemas/chat.py`
  - 问答响应新增人工确认字段

- `backend/app/schemas/agent_run.py`
  - 运行记录摘要新增人工确认字段

- `backend/app/api/routes/agent_runs.py`
  - 运行记录详情返回人工确认字段

- `backend/app/services/chat_service.py`
  - 流式与普通问答响应补齐人工确认字段

### 前端

- `frontend/src/views/RunsView.vue`
  - 新增：
    - 是否建议人工确认
    - 人工确认原因

## 当前能力边界

本阶段完成后，系统已经具备：

- 风险识别
- 人工确认建议
- 运行记录追踪

但暂时还不具备：

- 真正中断工作流
- 人工点击审核后恢复执行
- 多角色审批流

所以它目前更准确的定位是：

`最小版 HITL 建议能力`

而不是完整审批系统。

## 下一步建议

如果继续往下做，最自然的两个方向是：

1. `真正的人工审核节点`
- 工作流暂停
- 写入待审核状态
- 人工确认后恢复

2. `反馈与评测`
- 记录用户是否接受回答
- 为后续优化风险判断和检索策略提供数据

当前阶段更建议先做第 2 个，再做第 1 个。
