# 面试复习计划：从 RAG 开始

> **依据**：`docs/RAG_INTERVIEW_GUIDE.md`（主线，§19 给出复习顺序）、`docs/PROJECT_DEEP_DIVE.md`（全项目衔接）、`docs/INTERVIEW_GUIDE.md`、`docs/开发手册-售后闭环V2.md` V2.1、`docs/FINAL_ACCEPTANCE.md`
> **项目版本**：v1.0.0｜**核心定位**：面向消费电子售后的可信决策系统：证据约束 RAG + 受控业务工作流 + 人在回路
> **假设**：每天 90 分钟，共 10 天（两个工作周）。时间不足见文末「5 天压缩版」。
> **范围说明**：Day 1～7 是 RAG 主线；Day 8～10 延伸到受控工作流、有限 Tool Calling、状态机、权限与项目叙事。项目不是自主多步 Agent。

---

## 0. 怎么用

每个单元固定三段，**不要只看文档**：

| 段 | 时长 | 做什么 |
|---|---|---|
| 读 | 25 min | 读指定章节 + 对应源码（只看下面点名的函数，不逐行通读全仓） |
| 说 | 35 min | 合上文档，对着当天的「通关自测」大声口述；卡住的地方标记后回查 |
| 记 | 30 min | 填「一页纸速查卡」对应区块 + 在复习记录表打勾，写 1 条「今天还没讲清的点」 |

**通关标准**：不查资料能在 90 秒内讲完 §1 的一分钟回答；能手画两条链路；24 道题能脱稿答出要点。**只识别 ≠ 会讲**，面试考的是口述。

**四个交付物**（10 天后应该存在于你的笔记里）：
1. 一张手绘「离线入库 + 在线问答」双链路图；
2. 一张参数速查卡（见 §3）；
3. 一份 24 题自测勾选表（见 §4）；
4. 一段 3 分钟项目介绍 + 一份「必须诚实说明的边界」清单（见 §5）。

---

## 1. 每日安排

### 阶段 A｜RAG 主干（Day 1～5）

| Day | 主题 | 读（指南章节） | 看源码 | 当天产出 / 通关自测 |
|---|---|---|---|---|
| **1** | 建立全局图景 | §1 一分钟回答、§2 知识地图、§3 两条链路 | `data/docs/` 随便翻 2 份 | 手画两条链路（离线 10 步 / 在线 10 步）；**脱稿讲完 90 秒介绍**；能说清 12 个概念各解决什么问题 |
| **2** | 离线入库上半段：解析与分块 | §4 文档解析、§5 分块策略 | `rag/parsing.py::parse_document`、`rag/chunking.py::chunk_sections` | 写出 500/80 的含义与 chunk 边界；答 **Q4**、§4.5「为什么解析就存标题页码」、§5.6「overlap 越大越好吗」；**必须说"配置起点，不是最优参数"** |
| **3** | 离线入库下半段：向量与索引 | §6 Embedding、§7 Chroma 与 Metadata | `rag/embeddings.py::BgeEmbeddingProvider`、`rag/vector_store.py::ChromaVectorStore` | 默写 `product_id IN [当前商品, 0]`、`similarity = 1 - distance`、BGE 查询侧指令、归一化理由；答 **Q5/Q6**、§6.7「换模型旧向量怎么办」、§7.7「为何同时存 MySQL」 |
| **4** | 在线问答：召回、证据、拒答 | §8 Top-K 与阈值、§9 Evidence/Citation、§11 无依据与降级 | `services/rag.py::RAGService.retrieve_sync`、`services/rules.py`、`services/llm.py::SYSTEM_PROMPT` | 能画出「问题 → 阈值过滤 → [1][2] 编号 → 生成」；答 **Q7/Q9/Q11**、§8.5「为什么没 Rerank」、§11.3「四层防幻觉」；能区分"有引用"与"引用支持结论" |
| **5** | Prompt 与安全 | §10 Prompt 设计、§12 Prompt Injection 防线 | `services/llm.py::AGENT_SYSTEM_PROMPT`、`agent/tools.py`、`api/dependencies.py` | 写出订单事实与政策证据分开的 4 条理由；列出 5 层注入防线；答 **Q10**、§12.5「当前防护边界」；**不要说"绝对安全"** |

### 阶段 B｜RAG 的工程面与评测（Day 6～7）

| Day | 主题 | 读（指南章节） | 看源码 | 当天产出 / 通关自测 |
|---|---|---|---|---|
| **6** | 去重、事务、异步、故障定位 | §14 去重事务异步索引、§16 故障定位 | `services/knowledge.py::KnowledgeService`、`workers/tasks.py::ingest_document_task` | 画出 `pending → started → success/failure`；讲清 SHA-256 文件级去重、双写顺序与重试收敛；答 **Q12～Q15**；按 §16.1 的 7 步顺序复述「问耳机保修却没结果」的排查路径 |
| **7** | 评测、题目前半、四个区分 | §15 评测与指标、§17 Q1～Q12、§18 四件事 | `scripts/run_eval.py`、`data/eval/after_sales_questions.jsonl`、`data/eval/latest_report.md` | 默写 Hit@K 与任务成功率定义；答 **Q1～Q12**、§15.6「为什么全是 1.0」；**能主动说出 §18 的四件不能混淆的事** |

> **Day 7 结束时自测**：合上所有文档，用 2 分钟讲「从用户问『耳机保修多久』到返回带引用答案」的完整链路，中间要提到 4 个具体参数（500/80、Top-4、0.5、BGE 归一化）和 3 个源码文件。讲不出就回到 Day 1～4 补。

### 阶段 C｜从 RAG 延伸到全项目（Day 8～10）

| Day | 主题 | 读 | 看源码 | 当天产出 / 通关自测 |
|---|---|---|---|---|
| **8** | RAG、受控工作流与 Agent 的边界（最容易被追问） | RAG 指南 §13；`PROJECT_DEEP_DIVE.md` §9 受控售后工作流与 Tool Calling、§11 订单事实与规则；`INTERVIEW_GUIDE.md` §1/§2 | `agent/service.py::AfterSalesAgentService`、`agent/orchestrator.py`、`agent/tools.py` | 默写 §13.2 的 7 行职责划分表；能讲「为什么先查订单再检索政策」「为什么订单不进向量库」；答 **Q8/Q16～Q19**；说清当前只有有限工具候选、没有多工具自主循环，不是完整 Agent |
| **9** | 状态机、权限、并发、可观测 | `PROJECT_DEEP_DIVE.md` §7 数据模型、§8 状态机与槽位、§12 安全、§13 并发幂等、§14 可观测性、§15 测试评测；V2.1 §13.3～13.6 | `models/enums.py`、`repositories/orders.py`、`services/handoffs.py`、`core/middleware.py` | 能区分 `SessionStatus` 与 `WorkflowState` 两套状态；画出 `collecting_info → … → resolved / need_human`；讲清原子接管用带 `status='pending'` 的条件 UPDATE、AI 入库前复查状态；答 V2.1 §13.5 并发题 |
| **10** | 全真模拟 | `PROJECT_DEEP_DIVE.md` §19 三分钟介绍、§20 不能说错的边界、§21 题库；`INTERVIEW_GUIDE.md` §建议面试顺序；`docs/DEMO.md` | 不再读新代码 | ① 录一段 3 分钟项目介绍并回听；② 24 题随机抽 10 题口述；③ 按 §5 过一遍边界清单；④ 按 `DEMO.md` 完整跑一次演示流程，确认能边操作边讲 |

---

## 2. 源码阅读顺序（贴在编辑器旁边）

指南 §19 / §20 给的顺序，按天切分：

```text
Day1  data/docs 示例文档
Day2  parsing.py  →  chunking.py
Day3  embeddings.py  →  vector_store.py
Day4  rag.py  →  rules.py  →  llm.py
Day5  llm.py (AGENT_SYSTEM_PROMPT)  →  tools.py  →  dependencies.py
Day6  knowledge.py  →  workers/tasks.py
Day7  scripts/run_eval.py  →  data/eval/latest_report.md
Day8  agent/service.py  →  agent/orchestrator.py
Day9  models/enums.py  →  repositories/orders.py  →  services/handoffs.py
```

---

## 3. 一页纸速查卡（每天填一点，Day 7 填满）

**关键参数**

| 项 | 值 | 面试口径 |
|---|---|---|
| 分块 | `RAG_CHUNK_SIZE=500` / `OVERLAP=80` | 字符级切分，配置起点，**未做消融实验** |
| Embedding | `BAAI/bge-small-zh-v1.5`，512 维，归一化 | 文档与查询同一模型；查询加中文检索指令 |
| 向量库 | Chroma `knowledge_chunks`，HNSW cosine | `similarity = 1 - distance`，别拿 distance 直接比阈值 |
| 过滤 | `product_id IN [商品ID, 0]` | `0` = 全局政策；不传 product_id 则全库检索 |
| 召回 | `RAG_TOP_K=4`，`RAG_MIN_SIMILARITY=0.5` | Top-K 一定返回结果，阈值才决定有无依据；评测按 Top-5 算 Hit@3/5 |
| 规模 | 19 documents / 74 chunks / 74 向量 / 5 商品 | 全为虚构消费电子售后演示资料 |
| 评测 | 31 条固定场景，Hit@3/5=1.0，P50 954.93ms / P95 1315.19ms | **只证明固定集回归稳定**，不是生产准确率 |

**两条链路的一句话**

- 离线：校验 → 解析清洗 → 保留标题/页码 → 分块 → SHA-256 去重 → BGE 批量向量化 → Chroma + MySQL 双写 → `indexed`。
- 在线：问题向量化 → 商品过滤 Top-K → 阈值过滤 → `[1][2]` 证据编排 → 与订单事实拼装 → DeepSeek 生成 → 确定性规则复核 → 保存引用。

**四件不能混淆的事**（指南 §18）：检索到了 ≠ 回答正确；有引用 ≠ 引用支持结论；自动化测试通过 ≠ 语义效果通过；固定集 1.0 ≠ 生产准确率 100%。

---

## 4. 24 题自测勾选表

题目在 `RAG_INTERVIEW_GUIDE.md` §17，**答案不要抄写，只勾"能脱稿讲"**：

| 题号 | 主题 | 安排 | 能讲 |
|---|---|---|---|
| Q1 | 为什么用 RAG 而不是直接问模型 | D7 | ☐ |
| Q2 | 为什么不用微调 | D7 | ☐ |
| Q3 | 完整 RAG 链路 | D7 | ☐ |
| Q4 | Chunk 怎么切 | D2 | ☐ |
| Q5 | 为什么 BGE-small-zh | D3 | ☐ |
| Q6 | 文档与问题向量是否一致 | D3 | ☐ |
| Q7 | Top-K 和阈值怎么定 | D4 | ☐ |
| Q8 | 为什么订单不放进向量库 | D8 | ☐ |
| Q9 | 检索不到怎么办 | D4 | ☐ |
| Q10 | 如何防文档提示注入 | D5 | ☐ |
| Q11 | 引用准确率怎么保证 | D4 | ☐ |
| Q12 | 为什么做 SHA-256 去重 | D6 | ☐ |
| Q13 | 为什么用 Celery 异步索引 | D6 | ☐ |
| Q14 | 异步任务如何幂等 | D6 | ☐ |
| Q15 | 删除文档后为什么仍可能答得出来 | D6 | ☐ |
| Q16 | 证据约束 RAG、受控工作流与 Agent 的边界 | D8 | ☐ |
| Q17 | 为什么不让模型自由选所有工具 | D8 | ☐ |
| Q18 | 为什么先查订单再检索政策 | D8 | ☐ |
| Q19 | 如何防止相似商品串资料 | D8 | ☐ |
| Q20 | 如何评价 RAG | D7 | ☐ |
| Q21 | 100% 是否说明效果很好 | D7 | ☐ |
| Q22 | 如何优化召回效果 | D7 | ☐ |
| Q23 | 如何降低延迟 | D7 | ☐ |
| Q24 | 上生产最大缺口 | D10 | ☐ |

---

## 5. 面试前必须能诚实说明的边界

这些不是"缺点清单"，是**面试官一追问就会暴露、主动说明反而加分**的地方。每条给出可直说的口径：

| # | 事实 | 建议说法 |
|---|---|---|
| 1 | 模型只对 `get_my_order` 提出有限候选调用，政策检索由后端直调；`search_after_sales_policy` 已注册但未接入主链 | 「政策触发条件在后端是确定的，所以直调更可预测、少一轮模型调用；当前没有多工具自主循环，不是完整 Agent」 |
| 2 | 31 条固定集全 1.0，但 `run_eval.py` 直接调 `orchestrator.decide()`，不走完整 HTTP 链路；`gold_files` 只覆盖 8 份 md，PDF FAQ 未被标注 | 「这是自建固定回归集，证明关键路径和异常场景稳定；独立盲测、Chunk 消融、答案正确率与引用支持度人工抽检都还没做」 |
| 3 | 引用只保证来自实际召回片段，未做 claim-to-citation | 「有引用不等于引用支持结论，下一步要做逐句支持度审查」（指南 §9.4 / §18.2） |
| 4 | 删除时先清 Chroma 再提交 MySQL，有短暂一致性窗口；磁盘上传文件未清理 | 「向量删除幂等，整单重试可收敛；生产需要 outbox 或补偿任务，当前原型没做」（指南 §14.7） |
| 5 | 知识库只有 10 份虚构文档，其中 `after_sales_faq_source.txt` 与 PDF 内容重复 | 「小型演示库，为讲清链路刻意保持规整；复杂版式、OCR、Rerank 都未覆盖」 |
| 6 | 会话回答后进入 `resolved`，当前状态机未开放回流，同会话继续提问会返回 409 | **面试前建议先修**（允许 `resolved → collecting_info` 并补回归用例）；若来不及，直说「会话任务结束后应新建会话，状态机回流是已记录的改进点」，不要假装没发生 |

> 另外记住三条**不能说错**的：项目不含购物车/下单/支付/物流；不执行真实退款；Streamlit 双端是演示界面，不是生产前端。

---

## 6. 5 天压缩版（临时抱佛脚）

| 天 | 合并内容 | 最低要求 |
|---|---|---|
| 1 | Day 1 + Day 2 | 手画双链路 + 讲清 500/80 |
| 2 | Day 3 + Day 4 | 默写过滤条件、阈值、citation 组成 |
| 3 | Day 5 + Day 6 | 注入防线 + 双写删除 + 异步状态机 |
| 4 | Day 7 + Day 8 | 24 题过一遍 + RAG/受控工作流职责表 |
| 5 | Day 9 + Day 10 | 状态机与并发 + 3 分钟介绍 + 演示跑通 |

压缩版**跳过源码逐函数阅读**，但 §3 速查卡、§4 的 24 题、§5 的边界清单一个都不能省 —— 这三样才是面试现场真正被追问的部分。

---

## 7. 复习记录模板

```text
Day：          日期：          实际用时：
读过的章节：
看过的源码符号：
今天能脱稿讲的题号：
今天卡住的点：
回查后补的一句话口径：
通关：[ ] 是  [ ] 否（否 → 第二天先补 10 分钟）
```

---

## 8. 文档索引（复习时不用来回翻）

| 用途 | 文件 |
|---|---|
| RAG 主线与 24 题 | `docs/RAG_INTERVIEW_GUIDE.md` |
| 全项目链路、状态机、题库 | `docs/PROJECT_DEEP_DIVE.md` |
| 6 个技术亮点与源码证据 | `docs/INTERVIEW_GUIDE.md` |
| 唯一权威开发手册、完成定义 | `docs/开发手册-售后闭环V2.md`（V2.1） |
| 实测指标与验收结论 | `docs/FINAL_ACCEPTANCE.md`、`data/eval/latest_report.md` |
| 演示脚本 | `docs/DEMO.md` |
| 架构图 | `docs/ARCHITECTURE.md` |
