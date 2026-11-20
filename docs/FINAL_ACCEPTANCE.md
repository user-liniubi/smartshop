# SmartShop AfterSales 最终验收报告

| 项目 | 内容 |
|---|---|
| 验收日期 | 2026-11-06 |
| 项目定位 | 面向消费电子售后的可信决策本地技术原型：证据约束 RAG + 受控业务工作流 + 人在回路 |
| 发布版本 | `v1.0.0` |
| 代码基线 | `e8eff02` 加最终验收文档与版本号变更 |

## 验收结论

售后主闭环、消费者端、客服工作台、固定评测、请求级观测、异步文档索引和双存储删除均已实际运行通过。当前版本可以作为个人项目演示和面试材料交付。

本报告只记录实际执行结果，不将本地固定场景结果解释为生产环境准确率。

## 自动化检查

| 检查项 | 命令 | 实际结果 |
|---|---|---|
| 全量测试 | `uv run pytest -q` | `101 passed` |
| 静态检查 | `uv run ruff check .` | `All checks passed!` |
| 格式检查 | `uv run ruff format --check .` | `163 files already formatted` |
| 锁文件 | `uv lock --check` | 通过 |
| 迁移版本 | `uv run alembic current` | `4f8c2d7a1b90 (head)` |
| 模型迁移差异 | `uv run alembic check` | `No new upgrade operations detected` |

## 固定评测

执行命令：

```powershell
uv run python -m scripts.run_eval
```

| 指标 | 本次结果 |
|---|---:|
| 场景数 | 31 |
| 意图准确率 | 1.0 |
| 订单号提取准确率 | 1.0 |
| 工作流动作准确率 | 1.0 |
| 工具行为准确率 | 1.0 |
| RAG Hit@3 | 1.0 |
| RAG Hit@5 | 1.0 |
| 无依据拒答率 | 1.0 |
| 任务成功率 | 1.0 |
| P50 延迟 | 954.93 ms |
| P95 延迟 | 1315.19 ms |

评测期间出现过非法意图结构化输出，系统按设计降级后仍完成全部场景。31 条样本是自建固定场景，不能代表开放用户和生产流量上的泛化准确率。

## 真实售后闭环

通过运行中的 FastAPI、真实 MySQL 和 DeepSeek 完成：

```text
消费者创建会话
→ “耳机坏了，想退货”：ask_more_info / collecting_info
→ “订单号 A10086”：ask_more_info / collecting_info
→ “左耳没有声音”：answer / resolved
→ 申请人工：pending
→ 客服接管：claimed
→ 人工回复：claimed
→ 消费者读取到 sender_type=agent
→ 客服关闭：closed，closed_at 已写入
```

验收会话 ID：`12`。

## 服务与页面

| 项目 | 地址或检查 | 结果 |
|---|---|---|
| 健康检查 | `GET /health` | 200，返回 `X-Request-ID=01a279e9224041e3b3e7d568a71b0b3f` |
| Swagger | <http://127.0.0.1:8000/docs> | 200 |
| 消费者端 | <http://127.0.0.1:8501> | 200 |
| 客服工作台 | <http://127.0.0.1:8502> | 200 |
| Celery | `celery inspect ping` | 1 node online / pong |
| Redis | `redis-cli ping` | PONG |

## 异步索引与删除

真实异步任务结果：

```text
task_id: 41bc5ac173d5419dba4e0e503874a84d
initial_status: pending
final_status: success
progress: 100
document_id: 12
```

随后调用 `DELETE /knowledge/documents/12`：

- HTTP 状态：204；
- MySQL 文档列表：已移除；
- Chroma 剩余向量：0。

该验收同时验证了 Redis -> Celery -> MySQL `ingestion_jobs`、BGE 向量写入和双存储删除链路。

## 自动售后工单

使用真实 FastAPI、DeepSeek、MySQL 和 Chroma 提交“订单号 A10086，左耳没有声音，我想申请退货”：

```text
session_id: 15
chat_action: ticket_created
ticket_no: AS-E479065982FD
initial_status: pending_approval
review_status: approved
reviewer_id: 3
```

该验收证明系统能够自动完成退换货意图识别、订单归属校验、政策检索和待审批工单创建，并由客服完成审批。当前审批只更新内部工单状态，不执行真实退款、换货、支付或物流动作。

## 手工复验

1. 按 [DEMO.md](DEMO.md) 启动 MySQL、Redis、API、Worker 和双端页面。
2. 使用演示账号完成三轮售后、转人工、客服接管、回复和关闭。
3. 请求 `/health`，在响应头确认 `X-Request-ID`。
4. 通过客服账号上传一份临时知识文件并轮询任务状态。
5. 删除该文档，确认接口返回 204，并检查列表和向量均无残留。

## 当前边界

- 项目是面向消费电子产品的单商家售后技术原型，以头戴式无线降噪耳机为核心，同时覆盖键盘、显示器、笔记本和鼠标；不包含购物车、下单、支付、物流或多商家经营。
- 项目使用 LLM 辅助意图、槽位、有限订单工具选择和答案生成，但流程由后端状态机控制，不是自主多步 Agent。
- 退换货工单审批是项目内部流程，尚未对接企业真实退款、仓储或物流系统。
- 31 条固定评测结果不能等同于生产准确率。
- 尚未完成最终回答正确率和引用支持度的人工抽检。
- 没有生产级队列监控、告警、高可用和容量验证。
- 消费者端和客服端使用 Streamlit，不是 React/Vue 商业前端。

## 知识库扩充后补充验收

> 验收日期：2026-11-07

在 `v1.0.0` 基础上新增 9 份消费电子售后资料，知识库当前包含 19 份文档、74 个 Chunk 和 74 个向量。

实际回归结果：

```text
自动化测试：101 passed
Ruff 检查：All checks passed
Ruff 格式检查：163 files already formatted
MySQL documents：19
MySQL document_chunks：74
Chroma vectors：74
```

固定评测重新执行后：

```text
case_count=31
intent_accuracy=1.0
order_no_extraction_accuracy=1.0
action_accuracy=1.0
tool_behavior_accuracy=1.0
rag_hit_at_3=1.0
rag_hit_at_5=1.0
no_evidence_refusal_rate=1.0
task_success_rate=1.0
p50_latency_ms=954.93
p95_latency_ms=1315.19
```

新增资料经过真实 BGE + Chroma 检索抽样，键盘进液、显示器无信号、笔记本电池异常、外包装破损、送修数据备份和鼠标双击等问题均能命中对应资料。该结果仍是固定演示集验证，不代表生产泛化准确率。

## P0 售后能力增强补充验收

> 验收日期：2026-11-16
> 起始代码：`b94c38e`
> 详细说明：[P0_AFTER_SALES_ENHANCEMENT.md](P0_AFTER_SALES_ENHANCEMENT.md)

本轮新增多订单安全选择、订单切换重检、确定性售后资格和金额快照、跨会话活动工单幂等、消费者取消、工单事件、控制权版本与业务副作用竞态修复。

实际自动化结果：

```text
uv run pytest -q
126 passed in 79.83s

ruff check .
All checks passed!

ruff format --check .
171 files already formatted
```

新增迁移链：

```text
8b2d7f4c1a90 -> 2c4e6a8b1d30 -> 5e7a9c1d3b42 -> 7f9b2d4c6e81 (head)
```

P0 收尾后使用独立 SQLite、真实 DeepSeek 和本地 Chroma 重新执行 31 条固定评测：

```text
case_count=31
intent_accuracy=1.0
order_no_extraction_accuracy=1.0
action_accuracy=1.0
tool_behavior_accuracy=1.0
rag_hit_at_3=1.0
rag_hit_at_5=1.0
no_evidence_refusal_rate=1.0
task_success_rate=1.0
p50_latency_ms=1034.66
p95_latency_ms=1433.96
```

P0 收尾时使用独立 MySQL 8.0 临时实例实际执行了全部迁移和种子数据：

```text
alembic current: 7f9b2d4c6e81 (head)
alembic check: No new upgrade operations detected
seed: users=3, products=5, orders=5
```

已确认 `chat_sessions`、`orders`、`after_sales_tickets` 新字段以及 `after_sales_ticket_events` 表真实存在。
