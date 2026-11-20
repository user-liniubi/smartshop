# SmartShop AfterSales P0 售后能力增强报告

| 项目 | 内容 |
|---|---|
| 实施日期 | 2026-11-16 |
| 起始代码基线 | `b94c38ef1dc9f719c3f78e4d4de1688734ab9ed4` |
| 本轮范围 | P0-1 多订单、P0-2 售后资格、P0-3 工单生命周期、P0-4 控制权竞态 |
| 验证结果 | `126 passed`，Ruff 与格式检查通过 |
| 迁移链 head | `7f9b2d4c6e81` |

## 1. 本轮解决的问题

改造前系统已经具备订单查询、RAG、自动建单、人工审批和接管，但仍有四个业务缺口：

1. 只能处理明确订单号，不能安全处理多订单和模糊指代。
2. 订单状态、签收期限、质保期限和金额没有独立确定性服务。
3. 工单缺少跨会话幂等、消费者取消和操作时间线。
4. 人工接管后 AI 仍可能写入建单系统消息；模型失败还可能使合法诉求不落单。

本轮没有引入 Multi-Agent、自主循环、MCP、新向量库或消息中间件。

## 2. 新售后调用链

```text
消费者提出售后诉求
→ 服务端认证和会话归属校验
→ DeepSeek 提取意图、槽位和订单指代线索
→ 查询当前账号最近订单
→ 单候选自动关联，多候选等待用户选择
→ 白名单订单工具按 order_no + user_id 查询
→ BGE + Chroma 检索售后政策
→ AfterSalesEligibilityService 计算资格和金额快照
→ 控制权版本校验
→ 幂等创建待审批工单、事件和系统消息
→ DeepSeek 基于订单、资格和政策证据生成解释
→ 保存 AI 回答和引用
→ 客服审批或消费者取消
→ 消费者查询工单状态和处理时间线
```

工单创建已经移到回答模型之前。LLM 超时不会撤销已经通过确定性校验的工单；LLM 只能解释结果。

## 3. 多订单上下文

### 3.1 数据

`chat_sessions` 新增：

- `selected_order_id`：当前活动订单。
- `candidate_order_ids_json`：当前会话候选订单。
- `order_selection_state`：`none / awaiting_selection / selected`。

### 3.2 安全规则

- 候选订单只能来自当前认证消费者。
- 模型只提取“昨天那一笔”“另一笔”“第二个”等指代线索。
- 模型不能传 `user_id`，也不能指定未在当前候选中的订单。
- 精确订单号仍由 `get_my_order` 工具按 `order_no + user_id` 校验。
- 切换订单时清理旧 `product_id`，重新执行订单、政策和资格校验。

### 3.3 接口

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/orders/mine?limit=10` | 当前消费者最近订单 |
| POST | `/chat/sessions/{id}/order-selection` | 从候选订单中选择并继续原售后任务 |

## 4. 售后资格与金额

`AfterSalesEligibilityService` 输出：

- `eligible`
- `need_human_review`
- `not_eligible`

当前规则覆盖：

- 已取消订单。
- 未签收订单。
- 缺少签收时间。
- 签收后十五天质量问题窗口。
- 耳机、键盘、鼠标十二个月质保。
- 笔记本二十四个月质保。
- 显示器三十六个月质保。
- 进水、摔损、私自拆机、发热、鼓包等人工复核条件。
- 退货参考金额和换货零退款金额。

金额使用 `Decimal`，来自订单 `paid_amount` 快照，不使用浮点数和模型推断。

`orders` 新增：

- `delivered_at`
- `paid_amount`
- `shipping_amount`
- `currency`

`after_sales_tickets` 新增：

- `eligibility_result`
- `eligibility_reason`
- `refund_amount`
- `currency`
- `rule_version`

## 5. 工单生命周期

保留最小状态：

```text
pending_approval
→ approved
→ rejected
→ cancelled
```

暂不加入 `processing/completed`，因为当前没有真实退款、仓储或物流执行系统。

新增 `after_sales_ticket_events`：

- 创建。
- 审批通过。
- 审批驳回。
- 消费者取消。
- 系统记录。

状态更新、事件和消费者可见系统消息在同一事务提交。

新增：

- `active_dedup_key`：拦截同一用户、同一订单、同一申请类型的活动重复工单。
- `cancelled_at`
- `cancelled_by_id`

接口：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/after-sales/tickets/{id}` | 消费者读取本人工单 |
| GET | `/after-sales/tickets/{id}/events` | 消费者读取本人工单时间线 |
| POST | `/after-sales/tickets/{id}/cancel` | 取消自己的待审批工单 |

审批仍使用带 `status='pending_approval'` 条件的 UPDATE。新增测试使用两个线程同时审批，验证只有一个成功。

## 6. 人工接管竞态

`chat_sessions` 新增 `control_version`。

- AI 在一轮开始时记录版本。
- 人工申请、客服接管和关闭会改变控制状态并递增版本。
- AI 在建单、追问和回答前重新读取状态和版本。
- 接管前已创建的合法工单保留，人工可以继续处理。
- 接管后 AI 不能再写消息或创建新工单。

## 7. 数据库迁移

按顺序新增：

1. `8b2d7f4c1a90_add_order_selection_context.py`
2. `2c4e6a8b1d30_add_after_sales_eligibility_data.py`
3. `5e7a9c1d3b42_add_ticket_lifecycle_events.py`
4. `7f9b2d4c6e81_add_session_control_version.py`

升序命令：

```powershell
uv run alembic upgrade head
uv run python -m sample_data.seed
```

迁移会为已有已签收订单补充 `delivered_at=created_at`，为演示商品回填金额，并为历史工单补充创建事件。

## 8. 测试报告

本轮实际执行：

```text
uv run pytest -q
126 passed in 79.83s

ruff check .
All checks passed!

ruff format --check .
171 files already formatted
```

P0 收尾后使用真实 DeepSeek 和本地 Chroma 重新执行 31 条固定评测：

```text
case_count=31
intent_accuracy=1.0
action_accuracy=1.0
tool_behavior_accuracy=1.0
rag_hit_at_3=1.0
rag_hit_at_5=1.0
no_evidence_refusal_rate=1.0
task_success_rate=1.0
p50_latency_ms=1034.66
p95_latency_ms=1433.96
```

新增覆盖：

- 当前账号订单列表和越权隔离。
- 商品提示唯一匹配。
- 多候选不自动猜测。
- 候选订单选择。
- 订单切换清理旧商品上下文。
- 七天/十五天/质保边界。
- 缺签收时间、未签收和人为损坏转人工。
- LLM 不参与退款金额判断。
- 跨会话重复申请拦截。
- 消费者取消和取消越权。
- 工单创建/审批/取消事件。
- 两个线程真正并发审批。
- 模型失败后工单仍保留。
- 接管后迟到 AI 回复被丢弃。
- 接管发生在建单前时禁止创建工单。
- 配送和产品使用意图覆盖错误模型输出。
- 系统工单消息不进入模型上下文，AI 回答不重复工单状态。

## 9. 验证边界

- 自动化测试主要使用内存或临时 SQLite。
- P0 收尾时在工作区启动独立 MySQL 8.0 临时实例，实际执行全部迁移、种子数据和 `alembic check`；head 为 `7f9b2d4c6e81`，无模型迁移差异。
- P0 收尾时使用真实 DeepSeek 和本地 Chroma 重新执行 31 条固定评测，结果为 `31/31`、任务成功率 `1.0`。
- 不应把 `126 passed` 解释为生产准确率。

## 10. 面试讲法

项目不是“让 Agent 自己管理订单”，而是：

> 用 LLM 理解和解释，用服务端上下文解析订单指代，用白名单工具读取真实订单，用确定性规则计算期限和金额，用数据库事务保证工单一致性，再用控制权版本解决人工接管竞态。

可继续深挖：

1. 多订单为什么不交给 LLM 直接选择？
2. 为什么 RAG 政策文本不能直接成为退款执行规则？
3. 为什么先建单再生成回答？
4. `control_version` 与数据库行锁有什么区别？
5. 为什么条件 UPDATE 能处理并发审批？
6. 为什么没有加入 `processing/completed`？

## 11. 后续 P1

- 政策文档生效时间和版本替代。
- 独立困难场景评测集。
- Query Rewrite、BM25、Hybrid Retrieval 和 Rerank 的有门槛实验。
- 引用支持度和最终回答正确率人工抽检。
