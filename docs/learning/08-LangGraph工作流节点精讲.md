# LangGraph 工作流节点精讲

## 文档目标

这份文档专门讲整个项目里最难的一部分：

`LangGraph 工作流`

它回答的问题不是“LangGraph 是什么”，而是：

- 它在这个项目里到底承担什么角色
- 状态对象里都放了什么
- 每个节点负责什么
- 节点之间为什么这样连接
- 工作流是怎么从普通 RAG 演化成现在这套 Agent 流程的

如果你能把这份文档读懂，这个项目的 Agent 部分你就真正吃透了。

---

## 1. 先用一句话理解 LangGraph 在本项目里的角色

在这个项目里，LangGraph 不是用来“生成内容”的，也不是用来“存知识”的。

它的角色是：

`Agent 工作流编排器 / 有状态流程控制器`

也就是说，它负责：

- 组织步骤
- 管理状态
- 决定先做什么后做什么
- 根据条件走不同分支
- 让整个 Agent 过程可追踪

没有 LangGraph 时，这些逻辑会散在 service 里，变成一长串 if/else。

有了 LangGraph 后，流程变成：

`显式的节点 + 显式的状态 + 显式的路径`

---

## 2. 工作流入口在哪里

文件：
[workflow.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\agent\workflow.py)

整个 Agent 工作流的核心都在这个文件里。

你读这个文件时，最先要看的是三类内容：

1. `AgentState`
2. 每个 `_node` 函数
3. 图的构建和编译

---

## 3. `AgentState` 是什么

`AgentState` 是一个 `TypedDict`，代表：

`一次问答在工作流里共享的全部状态`

你可以把它想成一块“共享黑板”。

每个节点都从这块黑板上读数据，再写回新数据。

### 它为什么重要

因为没有统一状态对象，工作流就无法真正多步流转。

### 它里面有哪些关键字段

#### 基础输入

- `db`
- `question`
- `knowledge_base_id`
- `top_k`

这部分是这次问答的初始输入。

#### 改写相关

- `rewritten_query`
- `rewrite_reason`
- `rewrite_accepted`
- `rewrite_assessment_reason`

这部分描述：

- 是否改写了问题
- 为什么改写
- 改写值不值得用

#### 路由和工具选择

- `route_type`
- `route_reason`
- `selected_tool`
- `selected_tool_reason`

这部分描述：

- 这题是 qa / summary / comparison 哪一种
- 为什么这样判断
- 接下来该用哪个工具

#### 检索相关

- `selected_knowledge_bases`
- `retrieved_items`
- `retrieval_queries`
- `retrieval_quality`
- `retrieval_quality_reason`
- `need_more_context`
- `need_more_context_reason`
- `search_round`
- `rerank_applied`
- `rerank_reason`

这部分是工作流中最典型的 RAG 状态。

#### 回答相关

- `organized_items`
- `context_lines`
- `answer`
- `citations`
- `citations_json`
- `context_count`

这部分用于把候选内容整理成最终回答所需上下文。

#### HITL 相关

- `human_review_required`
- `human_review_reason`

#### 可观测性相关

- `trace_steps`

这部分记录每个节点的执行轨迹。

### 为什么状态字段这么多

因为这个系统已经不是：

`问一下 -> 检索一下 -> 回答一下`

而是一个真正多步 Agent。

---

## 4. 节点一：`route_question`

对应函数：

- `_route_question`

### 它做什么

调用：

- `classify_query`

把当前问题判断成：

- `qa`
- `summary`
- `comparison`

### 为什么第一步先做这个

因为很多后续行为都依赖任务类型：

- 要不要明显改写
- 选哪个工具
- 怎么重排
- 如何组织上下文

所以这是工作流的第一层分流。

### 它往状态里写什么

- `route_type`
- `route_reason`
- 一条 trace 记录

---

## 5. 节点二：`rewrite_query`

对应函数：

- `_rewrite_query`

### 它做什么

调用：

- `llm_service.rewrite_query`

把原始问题改写成更适合检索的形式。

### 为什么不是所有问题都明显改写

因为项目采用的是“保守改写”策略：

- `qa` 以稳为主
- `summary` / `comparison` 允许更明显改写

### 它写入什么

- `rewritten_query`
- `rewrite_reason`

---

## 6. 节点三：`assess_rewrite`

对应函数：

- `_assess_rewrite`

### 它做什么

调用：

- `assess_query_rewrite`

评估本次改写值不值得参与检索。

### 为什么要有这个节点

因为改写不总是好的。

如果改写：

- 没有新增价值
- 太空
- 太模板化
- 偏离原意

那就不应该参与检索。

### 它写入什么

- `rewrite_accepted`
- `rewrite_assessment_reason`

这一步让系统有了：

`改写后的风险控制`

---

## 7. 节点四：`tool_select`

对应函数：

- `_select_tool`

### 它做什么

调用：

- `select_tool`

根据问题和 route 决定后续更适合使用哪个上下文工具，例如：

- `build_qa_context`
- `summarize_context`
- `compare_contexts`

### 为什么要把 route 和 tool 分开

因为“问题类型”和“具体工具选择”虽然相关，但不是完全同一层概念。

route 更像：

- 任务分类

tool 更像：

- 具体执行单元选择

### 它写入什么

- `selected_tool`
- `selected_tool_reason`

---

## 8. 节点五：`search_knowledge`

对应函数：

- `_search_knowledge`

### 它做什么

调用：

- `search_knowledge`

这个工具内部又会做几件事：

1. 自动知识库路由
2. 根据原问题和改写问题做检索
3. 返回候选知识库和候选分块

### 为什么这一步很关键

因为这是从“问问题”真正进入“拿知识”的第一步。

### 它写入什么

- `selected_knowledge_bases`
- `retrieved_items`
- `retrieval_queries`

这一步之后，系统第一次拿到了“候选知识材料”。

---

## 9. 节点六：`analyze_retrieval`

对应函数：

- `_analyze_retrieval`

### 它做什么

调用：

- `analyze_retrieval_quality`

评估这次检索质量怎么样。

### 为什么要评估检索质量

因为系统不能默认“检索到了就够好”。

如果：

- 数量太少
- 主题覆盖差
- 候选知识库偏斜

那后面的回答质量大概率也不好。

### 它写入什么

- `retrieval_quality`
- `retrieval_quality_reason`

---

## 10. 节点七：`decide_more_context`

对应函数：

- `_decide_more_context`

### 它做什么

调用：

- `decide_need_more_context`

判断当前检索结果够不够，如果不够，是否应该再扩一次搜索。

### 为什么这一步很像 Agent

因为它体现了：

`系统不是机械执行固定步骤，而是在看了结果后决定下一步`

这就是多步决策的核心。

### 它写入什么

- `need_more_context`
- `need_more_context_reason`

---

## 11. 节点八：`expand_search`

对应函数：

- `_expand_search`

### 它做什么

在认为上下文不足时，扩大检索范围再搜一次。

### 它通常怎么变

- `top_k` 增大
- `search_round` 增加

### 为什么这一轮搜索重要

它让系统具备：

`第一次搜索不够好时，自我补救`

这比单次检索更接近真实 Agent 的行为。

---

## 12. 节点九：`rerank_results`

对应函数：

- `_rerank_results`

### 它做什么

调用：

- `rerank_retrieved_items`

对候选内容再排序。

### 为什么要有重排

因为原始检索顺序未必最适合回答。

不同任务更适合不同排序策略：

- `qa`：相关度优先
- `summary`：覆盖面更均衡
- `comparison`：不同知识库更平衡

### 它写入什么

- 更新后的 `retrieved_items`
- `rerank_applied`
- `rerank_reason`

---

## 13. 节点十：`assess_human_review`

对应函数：

- `_assess_human_review`

### 它做什么

调用：

- `assess_human_review_need`

判断本次问答是否应该进入人工审核。

### 为什么这个节点重要

因为它让系统从“全自动回答”进化成：

`高风险问题可以停下来等人确认`

### 它写入什么

- `human_review_required`
- `human_review_reason`

这一步是 HITL 的入口。

---

## 14. 节点十一：`prepare_*_context`

包括：

- `_prepare_qa_context`
- `_prepare_summary_context`
- `_prepare_comparison_context`

### 它们做什么

根据工具选择和任务类型，把候选内容整理成真正给大模型用的上下文。

### 为什么要分三种

因为：

- QA 需要精确短路径上下文
- Summary 需要更有覆盖度的内容
- Comparison 需要按对比对象组织上下文

这一步很关键，因为它把：

`检索结果`

变成：

`可用于回答的上下文`

### 它写入什么

- `organized_items`
- `context_lines`
- `citations`
- `citations_json`
- `context_count`

---

## 15. 节点十二：`generate_answer`

这是最后一个回答节点。

### 它做什么

调用：

- `llm_service.generate_answer`

把问题和上下文交给模型，生成最终回答。

### 为什么它不是工作流里最核心的节点

因为在这个项目里，真正体现 Agent 价值的不是“最后怎么生成”，而是：

`前面如何决定拿什么知识、怎么组织、是否继续搜、是否需要人工审核`

回答生成只是最后一步。

---

## 16. trace 是怎么记录的

工作流里每个节点都会调用 `_append_trace`。

这意味着每个节点都会留下：

- `node`
- `detail`
- `meta`

这些最终进入：

- `state.trace_steps`
- `agent_run.trace_json`

这也是为什么运行记录页能显示：

- route
- tool
- queries_used
- retrieval_quality
- human_review_reason

因为这些信息都是在节点执行时逐步写进去的。

---

## 17. 这个工作流和普通 RAG 的区别

普通 RAG 往往是：

1. 问题
2. 检索
3. 回答

而这个项目的工作流已经变成：

1. 问题分类
2. 查询改写
3. 改写评估
4. 工具选择
5. 自动选库
6. 检索
7. 检索质量判断
8. 必要时补充检索
9. 重排
10. 人工审核判断
11. 上下文整理
12. 回答生成

这说明它已经明显不是“简单 RAG”。

---

## 18. 为什么这个工作流能代表 Agent

因为 Agent 的关键不是“会聊天”，而是：

- 有状态
- 有工具
- 会决策
- 会根据中间结果改变后续路径

这个工作流已经具备这些特点：

### 有状态

通过 `AgentState`

### 有工具

通过 `tools.py`

### 会决策

通过：

- route
- tool_select
- assess_rewrite
- analyze_retrieval
- decide_more_context
- assess_human_review

### 会改变路径

通过：

- 是否继续扩展搜索
- 走哪种上下文整理分支
- 是否进入人工审核

---

## 19. 你应该怎么精读这个文件

推荐顺序：

1. 先读 `AgentState`
2. 再读 `run_agent_workflow`
3. 再读各节点函数
4. 最后看图的构建逻辑

不要一开始就盯着所有节点的实现细节，而是先看：

`状态怎么流`

因为工作流本质上就是：

`状态在节点间流动`

---

## 20. 最后一句话总结

如果你要用一句话记住本项目的 LangGraph 工作流，可以记成：

`这个 LangGraph 工作流把问题分类、查询改写、工具选择、自动选库、检索质量判断、补充搜索、重排、人工审核和回答生成组织成了一个有状态、可分支、可追踪的 Agent 流程，它是整个系统从普通 RAG 升级成 Agent 的核心。`
