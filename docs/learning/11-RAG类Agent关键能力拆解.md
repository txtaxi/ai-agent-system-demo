# RAG 类 Agent 关键能力拆解

## 文档目标

这份文档专门回答一个核心问题：

`在 RAG 类 Agent 里，到底哪些部分最关键？`

很多人一提到 Agent，就先想到：

- 大模型
- Prompt
- LangGraph
- Tool Calling

但如果项目是以知识库问答为主的 `RAG 类 Agent`，真正决定效果的，往往不是最后一步生成，而是：

`知识怎么进入系统、怎么被找到、怎么被组织、怎么被验证`

这份文档会把这些关键能力拆开讲，并结合当前项目说明：

- 哪些已经做了
- 哪些还只是基础版
- 哪些是后续最值得升级的点

---

## 一、先给结论

对大多数 `RAG 类 Agent` 来说，最关键的不是“模型会不会说”，而是下面这条链：

1. 文档解析
2. 文本切分
3. 向量化
4. 检索
5. 查询改写
6. 重排
7. 上下文组织
8. 评估与反馈

你可以把它理解成：

`RAG Agent 的核心，是把知识正确地送到模型面前，而不是只盯着模型输出。`

---

## 二、关键能力 1：文档解析

### 它是什么

把原始文件里的文本正确抽出来。

常见输入包括：

- `txt`
- `md`
- `pdf`
- `docx`

### 为什么关键

如果这一步就坏了，后面所有能力都会建立在脏数据上。

常见问题：

- PDF 提取乱码
- 页眉页脚混进正文
- 表格内容丢失
- 换行结构混乱

### 在当前项目里的体现

当前项目已经支持：

- `txt`
- `md`
- `pdf`
- `docx`

相关代码在：

- [document_service.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\services\document_service.py)

### 当前项目状态

- 已做：基础解析能力
- 未做：更高级的版面恢复、OCR、表格结构理解

---

## 三、关键能力 2：文本切分 / Chunking

### 它是什么

把长文档切成适合检索的片段。

### 为什么关键

检索的最小单位不是整篇 document，而是 chunk。

如果 chunk 切得不好，会出现：

- 语义被切断
- 标题和正文分离
- 检索命中但信息不完整
- 引用显示很乱

所以 chunking 往往是 RAG 效果的核心影响因素之一。

### 在当前项目里的体现

项目已经从最初的简单切分进化到了多策略切分：

- `paragraph_chunker`
- `section_chunker`
- `policy_chunker`
- `chunk router`

相关代码在：

- [base.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\rag\chunking\base.py)
- [paragraph_chunker.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\rag\chunking\paragraph_chunker.py)
- [section_chunker.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\rag\chunking\section_chunker.py)
- [policy_chunker.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\rag\chunking\policy_chunker.py)
- [router.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\rag\chunking\router.py)

### 当前项目状态

- 已做：结构感知的规则型分块
- 未做：真正的语义切分模型、版面结构模型

### 关键判断

当前项目已经不是“最简单硬切字符”，但也还不是“专业模型级切分”。

---

## 四、关键能力 3：Embedding / 向量化

### 它是什么

把文本片段转换成向量，使系统可以按语义相似度检索。

### 为什么关键

如果 embedding 差，系统就会出现：

- 同义表达召回差
- 语义相近内容找不到
- 检索结果噪声高

所以：

`embedding 质量决定语义召回上限`

### 在当前项目里的体现

当前项目有 embedding 这一步，但还没有接入真实专业 embedding model。

当前实现是：

- 本地确定性哈希向量

相关代码在：

- [embedding_service.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\services\embedding_service.py)

### 当前项目状态

- 已做：开发版向量化流程
- 未做：真实 embedding model

### 影响

这是当前项目效果不够强的一个核心原因。

---

## 五、关键能力 4：向量数据库与检索层

### 它是什么

把向量存进去，并支持相似度查询、过滤和召回。

### 为什么关键

embedding 再好，如果检索策略差，也会影响结果。

这部分通常包含：

- 向量存储
- 相似度计算
- metadata 过滤
- 多知识库检索
- top-k 策略

### 在当前项目里的体现

项目当前采用：

- `PostgreSQL + pgvector`

相关代码在：

- [retrieval_service.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\services\retrieval_service.py)

### 当前项目状态

- 已做：单库 / 多库相似度检索
- 已做：自动选库后的跨库检索
- 未做：更复杂的 hybrid search 或专业 reranker 接入

---

## 六、关键能力 5：Query Rewrite / 查询改写

### 它是什么

把用户自然语言问题改写成更适合检索的查询表达。

### 为什么关键

用户问法往往：

- 很口语化
- 很模糊
- 带上下文省略
- 更适合人理解，不适合检索

查询改写的目标是：

`不改变意图，但让检索更容易命中`

### 在当前项目里的体现

当前项目已经做了：

- 查询改写
- 改写评估
- 双路检索
- 改写回退策略

相关代码在：

- [llm_service.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\services\llm_service.py)
- [workflow.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\agent\workflow.py)

### 当前项目状态

- 已做：规则优先 + 可选模型辅助
- 未做：真正强模型驱动的稳定改写

### 关键判断

改写不是越激进越好，专业系统往往强调：

`保守改写 + 原问题兜底`

---

## 七、关键能力 6：Rerank / 重排

### 它是什么

对检索出来的候选结果再做一次排序。

### 为什么关键

原始检索结果并不总是最适合直接送给模型。

不同任务会需要不同的排序逻辑：

- `qa`：优先最相关
- `summary`：优先覆盖面
- `comparison`：优先平衡对比对象

### 在当前项目里的体现

项目已经支持按任务类型重排：

- `qa`
- `summary`
- `comparison`

相关代码在：

- [tools.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\agent\tools.py)
- [workflow.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\agent\workflow.py)

### 当前项目状态

- 已做：规则型任务重排
- 未做：更强的模型重排器 / reranker model

---

## 八、关键能力 7：Context Building / 上下文组织

### 它是什么

把检索结果整理成真正送给模型的上下文。

### 为什么关键

即使你检索得不错，如果上下文组织得差，回答仍然会差。

你需要决定：

- 哪些 chunk 放进去
- 放几个
- 按什么顺序
- 是否分组
- 是否保留来源结构

### 在当前项目里的体现

项目已经把上下文组织拆成不同工具：

- `build_qa_context`
- `summarize_context`
- `compare_contexts`

相关代码在：

- [tools.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\agent\tools.py)

### 当前项目状态

- 已做：任务感知的上下文组织
- 未做：更高级的主题聚合、层级摘要、多轮上下文压缩

---

## 九、关键能力 8：Route / Tool / Workflow 决策

### 它是什么

系统不是每次都走同一条路径，而是先判断：

- 当前是什么问题类型
- 应该选什么工具
- 是否需要补充上下文
- 是否需要人工审核

### 为什么关键

这正是 RAG Agent 与普通 RAG App 的分界线之一。

普通 RAG：

- 检索一次
- 回答一次

RAG Agent：

- 路由
- 改写
- 检索
- 评估
- 决策
- 再执行

### 在当前项目里的体现

项目已经有：

- `query_router_service`
- `knowledge_base_router_service`
- `select_tool`
- `analyze_retrieval_quality`
- `decide_need_more_context`
- `assess_human_review_need`
- `LangGraph workflow`

相关代码在：

- [query_router_service.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\services\query_router_service.py)
- [knowledge_base_router_service.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\services\knowledge_base_router_service.py)
- [workflow.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\agent\workflow.py)

### 当前项目状态

- 已做：规则主导的工作流决策
- 未做：强模型深度参与的多轮工具决策

---

## 十、关键能力 9：评估与反馈闭环

### 它是什么

知道系统答得好不好，以及为什么不好。

### 为什么关键

没有评估闭环，你只能凭感觉优化系统。

有了闭环后，你才能知道：

- 哪类问题容易失败
- 哪种 route 最差
- 哪个工具路径最容易出负反馈
- 哪个知识库质量更差

### 在当前项目里的体现

项目已经具备：

- `agent_runs`
- `feedback`
- 反馈统计
- 负反馈样本
- 按 route / tool / retrieval_quality / knowledge_base 聚合

相关代码在：

- [agent_run_service.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\services\agent_run_service.py)
- [feedback_service.py](D:\Study\Agent\StudyPlan\enterprise-ai-agent-system\backend\app\services\feedback_service.py)

### 当前项目状态

- 已做：最小评测闭环
- 未做：固定标准评测集、自动回归评测

---

## 十一、哪些是当前项目里最关键的几个点

如果只从“当前项目最值得关注的 RAG Agent 核心能力”来排，我会这样排序：

1. `Chunking`
2. `Embedding`
3. `检索与跨库召回`
4. `Query Rewrite`
5. `Rerank`
6. `Context Building`
7. `Route / Tool 决策`
8. `Eval / Feedback`

为什么这么排：

- 前 6 项决定“知识能不能被正确送到模型面前”
- 后 2 项决定“系统能不能自我纠偏和成长”

---

## 十二、当前项目里哪些已经做了，哪些还偏弱

### 已经做得不错的

- 工作流编排
- 工具层拆分
- 自动选库
- 多任务路由
- 查询改写机制
- 检索质量判断
- 重排
- 运行记录
- 反馈闭环

### 还明显偏弱的

- 真实 embedding
- 强模型驱动的回答生成
- 强模型驱动的工具选择与评估
- 更高级的 rerank

这就是为什么当前项目：

- 工程骨架很完整
- 但真实效果还不算强

---

## 十三、为什么说这个项目现在“骨架强，效果层还弱”

因为你已经搭好了：

- 知识库
- RAG
- Agent workflow
- LangGraph
- 可观测性
- HITL
- Eval 雏形

这些是工程上最费脑力、最费组织的部分。

而目前弱的主要集中在：

- 向量质量
- 生成质量
- 强模型参与程度

这也是为什么后面如果升级：

- 真实 embedding
- 真实 LLM

效果通常会比较快提升。

---

## 十四、后续升级最该优先补什么

如果你以后要把这个项目从“求职版 Agent”升级到“更像真实效果版”，优先级建议是：

1. 接入真实 embedding model
2. 稳定接入真实 LLM 作为回答模型
3. 让工具选择更多依赖模型辅助
4. 引入更强的 reranker
5. 做固定评测集

这里面最关键的前两步是：

- `embedding`
- `LLM`

---

## 十五、最后一句话总结

如果你要用一句话记住 `RAG 类 Agent` 的关键能力，我会建议你记成：

`最关键的不是最后那一步生成，而是文档怎么被解析、切分、向量化、召回、改写、重排、组织成上下文，并在整个流程里被持续验证。`
