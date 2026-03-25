# 阶段 4：Agent 工作流与可观测性

## 目标

在已经完成的 RAG 系统基础上，引入 Agent Tools、LangGraph 工作流和运行记录，让系统开始具备真正的工作流感和可观察性。

## 本阶段主要完成内容

### Agent Tools

当前已抽出的工具：

- `search_knowledge`
- `summarize_context`
- `compare_contexts`
- `build_qa_context`
- `build_citations`

这些工具的作用是把原本散落在服务层里的逻辑收拢成可复用能力。

### LangGraph 工作流

当前最小工作流节点：

- `route_question`
- `search_knowledge`
- `prepare_context`
- `generate_answer`

这意味着系统内部的问答编排已经不是简单的 if/else，而是进入了图工作流结构。

### 可观测性

当前已经新增：

- `agent_runs` 表
- 运行记录查询接口
- 前端运行记录页

每次新问答都会：

- 创建一条运行记录
- 保存工作流轨迹
- 提供按会话筛选和详情查看

## 本阶段的意义

这一阶段最重要的变化不是“多了一个页面”，而是：

`系统开始具备工作流执行痕迹`

这对后续继续做：

- ReAct
- 多工具执行
- 节点扩展
- 运行调试
- 评测

都很关键。

## 当前阶段结论

经过阶段 4，系统已经从：

`RAG 系统`

进一步升级为：

`带最小 Agent 工作流和运行记录的企业知识库智能体系统`
