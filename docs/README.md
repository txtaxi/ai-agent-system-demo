# 文档索引

`docs/` 已经按用途分成 4 类，不再把所有文档平铺在根目录：

- `project/`
  项目交付、收口、验收、日志、截图与 mock 数据
- `architecture/`
  架构、数据库、接口、企业级扩展规划
- `learning/`
  面向学习的精读、调用链、数据库与 LangGraph 深入讲解
- `phases/`
  阶段性开发记录

---

## 一、项目文档 `project/`

- [00-项目总览.md](./project/00-项目总览.md)
- [当前状态与下一步.md](./project/当前状态与下一步.md)
- [完整开发进度.md](./project/完整开发进度.md)
- [Agent项目收口总结.md](./project/Agent项目收口总结.md)
- [求职版收口完成说明.md](./project/求职版收口完成说明.md)
- [验收清单.md](./project/验收清单.md)
- [开发流程.md](./project/开发流程.md)
- [开发日志.md](./project/开发日志.md)
- [mock-data/企业管理制度样例.md](./project/mock-data/企业管理制度样例.md)
- `project/screenshots/`
  项目页面截图与演示 GIF 资源目录

---

## 二、架构文档 `architecture/`

- [系统架构.md](./architecture/系统架构.md)
- [数据库设计.md](./architecture/数据库设计.md)
- [接口规范.md](./architecture/接口规范.md)
- [企业级扩展架构.md](./architecture/企业级扩展架构.md)
- [企业级拓展计划书.md](./architecture/企业级拓展计划书.md)

---

## 三、学习文档 `learning/`

这是最适合系统掌握项目的一组，已经按推荐顺序加了序号：

1. [01-从零理解整个项目.md](./learning/01-从零理解整个项目.md)
2. [02-项目演化历史详解.md](./learning/02-项目演化历史详解.md)
3. [03-后端逐文件精读.md](./learning/03-后端逐文件精读.md)
4. [04-前端逐文件精读.md](./learning/04-前端逐文件精读.md)
5. [05-后端调用链时序讲解.md](./learning/05-后端调用链时序讲解.md)
6. [06-前端页面交互流程讲解.md](./learning/06-前端页面交互流程讲解.md)
7. [07-数据库设计精读.md](./learning/07-数据库设计精读.md)
8. [08-LangGraph工作流节点精讲.md](./learning/08-LangGraph工作流节点精讲.md)
9. [09-能力演化与开发细节.md](./learning/09-能力演化与开发细节.md)
10. [10-Agent工程方法论.md](./learning/10-Agent工程方法论.md)
11. [11-RAG类Agent关键能力拆解.md](./learning/11-RAG类Agent关键能力拆解.md)

---

## 四、阶段记录 `phases/`

这一组更适合复盘项目演化过程，不适合第一次读项目时直接进入：

- [阶段01-项目骨架.md](./phases/阶段01-项目骨架.md)
- [阶段02-知识库模块.md](./phases/阶段02-知识库模块.md)
- [阶段02-知识库实现记录.md](./phases/阶段02-知识库实现记录.md)
- [阶段03-RAG问答与路由.md](./phases/阶段03-RAG问答与路由.md)
- [阶段04-Agent工作流与可观测性.md](./phases/阶段04-Agent工作流与可观测性.md)
- [阶段05-HITL建议节点.md](./phases/阶段05-HITL建议节点.md)
- [阶段06-反馈与评测闭环.md](./phases/阶段06-反馈与评测闭环.md)
- [阶段07-反馈统计面板.md](./phases/阶段07-反馈统计面板.md)
- [阶段08-负反馈样本回放.md](./phases/阶段08-负反馈样本回放.md)
- [阶段09-Eval聚合增强.md](./phases/阶段09-Eval聚合增强.md)
- [阶段10-负反馈筛选与摘要增强.md](./phases/阶段10-负反馈筛选与摘要增强.md)
- [阶段11-HITL暂停恢复.md](./phases/阶段11-HITL暂停恢复.md)
- [阶段12-项目收口与企业级规划.md](./phases/阶段12-项目收口与企业级规划.md)

---

## 文档同步说明

近期项目已补充以下内容，并已纳入当前文档索引：

- GitHub 展示版 README 收口
- 截图资源目录 `project/screenshots/`
- mock 测试数据 `project/mock-data/企业管理制度样例.md`
- 对话历史恢复 `agent_run` / 人工审核状态
- 反馈统计聚合修复
- 后端回归测试 `backend/tests/`

如果后续继续扩展功能，建议同步更新：

- 根目录 `README.md`
- 当前文件 `docs/README.md`
- `docs/project/00-项目总览.md`

避免出现“代码已更新，但学习路径和索引未同步”的情况。
