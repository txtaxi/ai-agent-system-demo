# 阶段 09：Eval 聚合增强

## 本阶段目标

在已有反馈统计和负反馈样本回放的基础上，把反馈分析从“按路由统计”扩展到更多与 Agent 执行质量直接相关的维度。

本阶段重点关注：

- 按工具统计
- 按检索质量统计
- 按人工确认建议统计
- 按知识库统计

## 为什么要做

只看 `route` 还不够。

如果系统已经开始具备：

- 工具选择
- 检索质量判断
- 人工确认建议
- 自动选库 / 多知识库检索

那么反馈分析也应该能回答这些问题：

- 哪个工具路径更容易收到负反馈
- 低检索质量是否和差评强相关
- 哪些问题本来就更适合人工确认
- 哪些知识库更容易产出差评

## 设计思路

### 1. 不直接在 SQL 中做复杂 JSON 聚合

`agent_runs.trace_json` 中已经存有大量执行摘要字段，例如：

- `selected_tool`
- `retrieval_quality`
- `human_review_required`
- `selected_knowledge_bases`

如果继续在数据库层做复杂 JSON 聚合，SQL 会变得难维护、难调试。

因此本阶段采用更稳的做法：

- 先查询 `feedback + agent_runs`
- 再在 Python 服务层按摘要字段做聚合

这样更适合当前项目阶段，也更利于后续继续扩展维度。

### 2. 聚合维度

当前增加的维度包括：

- `by_route`
- `by_tool`
- `by_retrieval_quality`
- `by_human_review`
- `by_knowledge_base`

### 3. 保留负反馈样本回放

统计面板继续保留“负反馈样本”区块，支持从统计分析直接进入具体失败案例回放。

## 涉及文件

### 后端

- `backend/app/schemas/feedback.py`
- `backend/app/services/feedback_service.py`

### 前端

- `frontend/src/views/FeedbackView.vue`

### 文档

- `docs/phases/阶段09-Eval聚合增强.md`
- `docs/开发日志.md`
- `docs/当前状态与下一步.md`

## 本阶段价值

- 系统从“能看反馈总量”升级到“能按执行维度分析反馈”
- 让反馈真正开始服务于 Agent 质量定位
- 为后续更细粒度的评测、回归分析和失败案例复盘提供基础
