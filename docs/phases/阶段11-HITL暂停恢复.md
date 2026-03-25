# 阶段 11：HITL 暂停与恢复

## 本阶段目标

把前一阶段的“人工确认建议”升级成真正可操作的人工审核闭环，让高风险问答可以先暂停，再由人工决定通过或驳回。

## 为什么要做

只有“建议人工确认”还不够。

企业 Agent 系统里，真正重要的是：

- 高风险问题不要直接落最终结果
- 工作流要能进入待审核状态
- 人工审核后要能改变最终结果

这一步解决的是从“提示”到“控制”的升级。

## 本阶段完成内容

### 1. 新增待审核状态

当工作流判断：

- `human_review_required = true`

时，运行记录不再直接标记为 `completed`，而是进入：

- `pending_review`

### 2. 审核通过后再写入会话

待审核运行记录会先保存：

- 草稿答案
- 引用
- 执行轨迹

只有人工审核通过后，才真正把回答写入对话消息。

### 3. 审核驳回

如果人工审核驳回：

- 运行记录状态会变成 `rejected`
- 对话中会追加一条驳回说明消息

### 4. 新增审核接口

新增接口：

- `POST /api/v1/agent-runs/{agent_run_id}/review`

请求内容：

- `action=approve`
- `action=reject`
- 可选 `comment`

### 5. 运行记录页新增审核操作

当运行记录状态为 `pending_review` 时，前端可直接：

- 审核通过
- 审核驳回
- 填写审核备注

## 涉及文件

### 后端

- `backend/app/schemas/chat.py`
- `backend/app/schemas/agent_run.py`
- `backend/app/services/agent_run_service.py`
- `backend/app/services/chat_service.py`
- `backend/app/api/routes/agent_runs.py`

### 前端

- `frontend/src/views/RunsView.vue`

### 文档

- `docs/phases/阶段11-HITL暂停恢复.md`
- `docs/开发日志.md`
- `docs/当前状态与下一步.md`

## 本阶段价值

- HITL 从“建议层”升级到“控制层”
- 高风险问答真正具备暂停与恢复能力
- 项目开始更接近企业 Agent 中常见的审批流形态
