# 第四周复盘｜售后 Agent 多轮闭环：V2 Day 6～10

## 周目标

把已有的意图、槽位、受控订单工具和状态机接入真实聊天主链路，完成：

- 三轮补齐订单号与具体故障；
- DeepSeek 选择白名单订单工具；
- MySQL 订单事实与 Chroma 政策证据组合；
- 确定性售后安全规则；
- 故障降级和人工待接管队列。

## 完成结果

| V2 开发日 | 完成内容 | 验收 |
|---|---|---|
| Day 6 | 多轮信息补齐，已有槽位不被误覆盖 | 三轮真实 API 通过 |
| Day 7 | 订单事实 + RAG 政策组合 | 真实 DeepSeek + MySQL + Chroma 通过 |
| Day 8 | 售后确定性规则与越权承诺拦截 | 规则测试通过 |
| Day 9 | 模型/检索失败降级为人工处理 | 用户消息保留且创建 handoff |
| Day 10 | 消费者申请人工、客服待接管队列 | 幂等、权限和 pending 队列通过 |

## 实现结构

- `backend/app/agent/service.py`：售后 Agent 编排入口；
- `backend/app/agent/intent.py`：意图和槽位提取、槽位安全合并；
- `backend/app/agent/tools.py`：订单与政策工具白名单、参数校验和审计；
- `backend/app/agent/orchestrator.py`：后端权威工作流状态转换；
- `backend/app/services/answers.py`：订单事实与政策证据的模型回答；
- `backend/app/services/rules.py`：退款承诺、异常订单和无证据安全规则；
- `backend/app/services/handoffs.py`：幂等人工申请和 pending 队列；
- `backend/app/api/routes/chat.py`：聊天、历史和人工申请 API；
- `backend/app/api/routes/agent.py`：客服待接管队列。

## 三轮真实 API 验收

| 用户输入 | 系统动作 | 工作流状态 | 缺失槽位 |
|---|---|---|---|
| 耳机坏了，想退货 | 追问订单号和具体问题 | `collecting_info` | `order_no, issue_description` |
| 订单号 A10086 | 只追问具体问题 | `collecting_info` | `issue_description` |
| 左耳没有声音 | 查询本人订单、检索政策并回答 | `resolved` | 无 |

第三轮回答同时包含：

- MySQL 订单事实：`A10086`、`delivered`、商品 `SmartShop 降噪耳机 Pro`；
- 政策来源：耳机提供十二个月质保、先重新配对充电、仍有问题安排售后检测；
- 明确业务边界：系统不能承诺真实退款或换货已经完成。

真实 DeepSeek Tool Calling 选择：

```json
{
  "name": "get_my_order",
  "arguments": {
    "order_no": "A10086"
  }
}
```

## 权限与异常验收

- `consumer_demo` 查询自己的 `A10086`：工具成功；
- `consumer_demo` 查询 `consumer_other` 的 `A10088`：返回 `order_not_found`；
- 越权回答不包含他人订单状态或商品信息；
- 取消订单触发规则并转人工；
- 无政策证据时不调用模型生成确定性退货结论；
- 模型故障时先保存用户消息，再创建人工 handoff；
- 会话进入 `need_human` 后，新消息保存但 AI 不再回复。

## 人工队列验收

真实 MySQL 中：

```text
handoffs.id = 1
status = pending
source = user
reason = 端到端人工验收
claimed_at = NULL
closed_at = NULL
```

消费者重复申请返回同一条 handoff；其他消费者不能操作该会话；消费者不能查看客服队列；客服可以读取 pending 队列。

## 数据库验收

```text
MySQL 8.0.40
迁移版本：e2b7a1c4d9f0 (head)
Alembic check：No new upgrade operations detected
```

真实会话槽位示例：

```json
{
  "order_no": "A10086",
  "issue_type": "return",
  "issue_description": "左耳没有声音",
  "product_id": 1
}
```

成功与越权工具调用均写入 `tool_invocations`，参数中不包含客户端或模型伪造的 `user_id`。

## 自动化验收

```text
80 passed
All Ruff checks passed
114 files already formatted
uv lock check passed
```

真实端到端冒烟脚本：

```powershell
uv run python -m scripts.smoke_after_sales
```

## 真实测试发现并修复的问题

1. 第二轮只输入订单号时，模型把 `issue_type` 从 `return` 改成 `order_query`，导致跳过故障描述和订单查询。修复为已有退货/换货任务在补充订单号时保留原类型。
2. “耳机坏了，想退货”被模型误判为足够具体的故障描述。增加确定性泛化描述规则，继续追问真实症状。
3. 旧聊天路由仍直接调用 RAG。已切换到完整 Agent 编排，并保留用户消息先落库的故障语义。

## 当前边界

本阶段完成到“人工申请 + 待接管队列”。以下仍未实现：

- 客服原子接管；
- 人工回复和关闭；
- 接管后迟到 AI 响应的最终丢弃测试；
- 消费者端与客服 Streamlit 页面；
- 端到端固定评测集和指标。

这些由 V2 Day 11 之后继续完成。
