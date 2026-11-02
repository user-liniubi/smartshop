# 第五周复盘｜人工协同、双端与评测：V2 Day 11～15

## 周目标

完成客服原子接管、人工回复与关闭、消费者端、客服工作台、真实端到端回归和固定 Agent/RAG 评测。

## 完成结果

| V2 开发日 | 完成内容 | 验收 |
|---|---|---|
| Day 11 | 条件更新原子接管、上下文、回复、关闭 | 通过 |
| Day 12 | 消费者 Streamlit 页面 | AppTest 通过 |
| Day 13 | 客服 Streamlit 工作台 | AppTest 通过 |
| Day 14 | 真实消费者—客服—关闭闭环 | 真实 MySQL 通过 |
| Day 15 | 31 条固定场景评测 | 真实指标已生成 |

## 客服接管与并发

- 接管使用 `UPDATE handoffs ... WHERE status='pending'` 条件更新；
- 只有影响行数为 1 的客服接管成功；
- 接管和会话状态更新在同一事务中；
- 其他客服无法读取或回复已接管会话；
- 关闭后继续回复返回 `handoff_closed`；
- AI 保存回复前重新读取会话状态，人工接管后的迟到回复会被丢弃。

真实 MySQL 结果：

```text
session.status=closed
session.workflow_state=resolved
handoff.status=closed
handoff.agent_id=3
claimed_at / closed_at 均已写入
```

## 双端页面

消费者端：

- 账号登录；
- 新建和选择会话；
- 消息历史；
- 工作流状态；
- 来源引用；
- 申请人工；
- 显示的 Token 只存在 Streamlit Session State。

客服工作台：

- 客服账号登录；
- pending 队列与自己的已接管会话；
- 会话历史和订单摘要；
- 接管；
- 人工回复；
- 关闭会话。

双端均使用 Streamlit 1.66.1 原生组件，没有自定义 CSS 或旧版组件。`AppTest` 覆盖登录页、消费者历史页和客服待接管页。

最终自动化回归：

```text
88 passed
All Ruff checks passed
125 files already formatted
```

## 真实端到端结果

```text
消费者创建会话并完成 AI 售后回答
→ 申请人工
→ 客服接管
→ 查看订单 A10086 上下文
→ 人工回复
→ 消费者看到人工消息
→ 消费者后续消息仅保存，AI 不回复
→ 客服关闭
```

消费者历史最后两条发送方为：

```text
agent, consumer
```

消费者关闭后的待处理消息没有生成 assistant 消息，证明人工接管后 AI 停止自动答复。

## 固定评测结果

评测集：`data/eval/after_sales_questions.jsonl`  
场景数：31

```text
intent_accuracy=1.0
order_no_extraction_accuracy=1.0
action_accuracy=1.0
tool_behavior_accuracy=1.0
rag_hit_at_3=1.0
rag_hit_at_5=1.0
no_evidence_refusal_rate=1.0
task_success_rate=1.0
p50_latency_ms=1203.76
p95_latency_ms=4261.63
```

报告文件：

- `data/eval/latest_report.json`
- `data/eval/latest_report.md`

口径边界：

- 这是 31 条自建固定场景上的结果，不代表生产泛化准确率；
- 任务成功率要求意图、订单号、工作流动作、工具行为以及适用的检索/拒答均正确；
- P50/P95 是当前本地环境的小样本耗时；
- 尚未进行最终回答正确率和引用支持度的人工抽检。

## 评测中发现并修复的问题

1. 模型偶尔返回非法 JSON，最初统一降级为 `unknown`；
2. 产品使用问题如“支持扩展内存”“如何清洁”“续航多少”被模型判成未知或换货；
3. 增加确定性关键词兜底后，同一 31 条评测集从 87.1% 提升至 100%，未修改评测标签。

## 仍待完成

- 请求 ID、各阶段结构化耗时和监控；
- 文件上传、提示注入、消息长度的进一步安全回归；
- 测试目录按 unit/integration/e2e 拆分；
- README、架构图、状态图和源码讲解最终整理；
- 可选 Redis + Celery 异步索引与向量删除；
- 更多真实用户样本、引用支持度人工抽检和独立测试集。

## 验收结论

V2 Day 11～15 功能、双端页面、真实 MySQL 人工协同闭环和固定评测均已通过。

## Git 提交

提交信息：`feat: add human handoff workbench and agent evaluation`  
提交哈希：`282c67d`
