# 第三周复盘｜售后闭环 V2：Day 1～5

## 周目标

从已有的“订单权限 + 会话持久化 + RAG 问答”继续向单商家售后 Agent 闭环推进。本周不接前端、不创建转人工接口，也不提前实现后续多轮订单政策组合。

## 本周结果

| V2 开发日 | 完成内容 | 主要技术 | 验收 |
|---|---|---|---|
| Day 1 | 统一项目范围，建立 V2 开发手册 | Markdown、需求边界分析 | 完成 |
| Day 2 | 按业务订单号查询本人订单 | FastAPI、SQLAlchemy、对象级授权 | 完成 |
| Day 3 | 工具白名单、受控订单工具和调用审计 | Pydantic、SQLAlchemy、Alembic | 完成 |
| Day 4 | 结构化意图、槽位提取与安全合并 | DeepSeek JSON 输出、Pydantic、正则 | 完成 |
| Day 5 | 后端权威售后工作流状态机 | 状态机、SQLAlchemy、Alembic | 完成 |

本周结束时：

```text
全量测试：62 passed
Ruff 检查：All checks passed
Ruff 格式：108 files already formatted
真实 MySQL 迁移：c3e6f2a9b715 (head)
Alembic 模型检查：No new upgrade operations detected
```

## Day 1｜统一项目范围与开发路线

### 当天完成什么

- 确认项目为“单商家电商售后智能客服”；
- 明确业务从消费者已有订单后的售后咨询开始；
- 不再把项目描述成完整商城或四角色平台；
- 创建 `docs/开发手册-售后闭环V2.md`，作为后续执行路线；
- 在 README 中同步真实项目定位。

### 实际实现

- V2 手册定义业务范围、用户角色、目标闭环、数据模型、接口、状态机、测试矩阵和面试问题；
- README 说明当前只覆盖售后场景，不包含购物、支付、物流和多商家经营；
- 旧开发手册保留为历史材料，不再作为后续开发路线。

### 使用技术

- 需求分析、业务边界设计、Markdown 文档、Git 历史审计。

### 遇到的问题

仓库同时存在“智能导购商城”和“单商家售后客服”两套冲突方案，容易导致实现目标不清晰。

### 怎么解决

根据现有代码、每日任务、用户数据和后续开发计划，确认实际项目是单商家售后客服。将 V2 手册设为唯一执行路线，并明确商城经营角色不在当前范围。

### 验收

- README 与 V2 手册业务定位一致；
- 明确列出已实现、未实现和不做的功能；
- 后续开发不需要再次猜测项目是导购商城还是售后客服。

## Day 2｜按业务订单号查询本人订单

### 当天完成什么

- 新增 `GET /orders/by-number/{order_no}`；
- 支持售后聊天需要的 `A10086` 这类业务订单号；
- 查询同时匹配订单号和当前认证用户 ID；
- 保留原有 `GET /orders/{order_id}`，接口保持兼容。

### 实际实现

- Repository 增加 `get_order_owned_by_user_and_no()`；
- Service 增加 `get_order_for_user_by_no()`；
- 路径参数增加长度和字符集校验；
- 他人订单、未知订单统一返回 `404 order_not_found`；
- 非法订单号格式返回 422。

### 使用技术

- FastAPI 路径参数、Pydantic 校验、SQLAlchemy `select`、`selectinload`、对象级授权。

### 遇到的问题

聊天用户提供的是业务订单号，而原有订单接口只接受数据库内部 ID。模型或聊天编排不能依赖内部 ID。

### 怎么解决

增加业务订单号查询，并在 SQL 的 `WHERE` 条件中同时放置 `order_no` 和 `user_id`。不采用“先查订单再在 Python 中比较归属”的方式。

### 验收

- 本人 `A10086` 查询成功；
- 他人 `A10088` 查询返回 404；
- 不存在订单和非法格式有测试；
- 订单专项测试新增后全部通过。

## Day 3｜受控订单工具与调用审计

### 当天完成什么

- 建立 `backend/app/agent/tools.py`；
- 定义工具白名单，只开放 `get_my_order`；
- 工具参数禁止额外字段，不接受模型传入 `user_id`；
- 当前用户身份由服务端运行时上下文注入；
- 新增 `tool_invocations` 审计表；
- 在真实 MySQL 中完成迁移和一次真实工具调用。

### 实际实现

- `ToolRegistry` 负责工具查找、参数校验、执行和错误映射；
- `GetMyOrderArguments` 只允许 `order_no`；
- 查询工具返回订单号、状态、商品 ID 和商品名；
- 审计记录参数、结果摘要、状态、错误码和耗时；
- 未知工具和非法参数记录为 `blocked`；
- 越权订单记录为 `error`。

### 使用技术

- Pydantic、SQLAlchemy、Alembic、FastAPI 依赖边界思想、工具白名单、调用审计。

### 遇到的问题与解决

1. 一开始本机 Docker 未运行，真实 MySQL 无法连接。后续启动 `smartshop-mysql-dev` 容器并执行迁移。
2. 临时 SQLite 无法执行旧迁移中的 MySQL `ALTER COLUMN` 语法。改用 MySQL 离线模式验证迁移链，之后在真实 MySQL 执行。
3. 审计内容不能保存密码、Token 或敏感身份参数。非法参数只保存 `{"redacted": true}`，成功调用由服务端注入身份。

### 验收

- 工具专项测试 6 项通过；
- MySQL 存在 `tool_invocations` 表、索引和外键；
- 真实订单工具调用状态为 `success`；
- 临时验证数据已清理；
- Alembic 模型检查无差异。

## Day 4｜结构化意图与槽位提取

### 当天完成什么

- 定义售后意图枚举；
- 定义订单号、问题类型和问题描述槽位；
- DeepSeek 使用 JSON Object 模式返回结构化结果；
- Pydantic 严格校验意图、槽位和置信度；
- 订单号增加确定性正则兜底；
- 槽位合并时空值不覆盖已有信息；
- 非法模型 JSON 自动降级为 `unknown`。

### 实际实现

- 文件：`backend/app/agent/intent.py`、`backend/app/agent/schemas.py`；
- 意图包括政策、订单、退货、换货、保修、人工和未知；
- 订单号支持“订单 A10086”“订单号：A10086”和裸订单号；
- 模型返回代码块包裹的 JSON 也可解析；
- 模型上下文包含已有槽位，减少重复询问。

### 使用技术

- DeepSeek OpenAI 兼容接口、JSON Object 输出、Pydantic、正则、异步 Python。

### 遇到的问题

模型返回空字符串订单号时，Pydantic 最小长度校验会先报错，导致整个合法意图被降级为 `unknown`。

### 怎么解决

在 `SlotUpdate` 中加入 before 校验器，把空字符串规范成 `None`，再合并已有槽位。这样空模型输出不会覆盖历史订单号和故障描述。

### 验收

- 意图专项测试和模型测试共 17 项通过；
- 真实 DeepSeek 调用返回：

```text
intent=return_request
order_no=A10086
issue_type=return
confidence=0.95
```

- 非法 JSON、Markdown 包裹、空值和非法历史槽位都有测试。

## Day 5｜后端权威售后工作流状态机

### 当天完成什么

- 为 `chat_sessions` 增加 `workflow_state`；
- 定义收集信息、查订单、查政策、答案就绪、转人工和已解决状态；
- 创建 `AfterSalesOrchestrator`；
- 后端根据意图和槽位完整性决定下一步动作；
- 会话意图、槽位和工作流状态持久化；
- 禁止非法状态转换。

### 实际实现

- 状态定义在 `backend/app/models/enums.py`；
- 编排器位于 `backend/app/agent/orchestrator.py`；
- 状态迁移位于 Alembic `c3e6f2a9b715`；
- 渠道会话状态和工作流状态分开保存；
- 缺失信息返回 `ask_more_info`；
- 订单类任务进入 `checking_order`；
- 普通政策问题进入 `checking_policy`；
- 人工请求进入 `need_human`；
- 非法状态转换返回 409。

### 使用技术

- 后端权威状态机、Pydantic 决策模型、SQLAlchemy 持久化、Alembic、pytest。

### 遇到的问题

如果把流程决定全部交给 Prompt，模型可能跳状态、重复追问或直接声称已经处理。仅用一个状态字段也无法同时表示“当前任务阶段”和“会话是否由人工接管”。

### 怎么解决

- 意图和槽位作为输入，状态转换由后端代码决定；
- 拆分 `chat_sessions.status` 与 `workflow_state`；
- 每次转换使用允许集合校验；
- 会话更新通过 Repository 和 Service 完成；
- 新状态持久化后由独立数据库会话重新读取验证。

### 验收

- Day 5 状态机、意图和会话专项测试 16 项通过；
- 缺两个槽位时一次返回完整缺失项；
- 第二轮只追问剩余槽位；
- 完整退货请求进入 `checking_order`；
- 售后政策问题进入 `checking_policy`；
- 人工请求进入 `need_human`；
- 非法转换返回 `invalid_workflow_transition`；
- 真实 MySQL 中存在 `workflow_state` 字段和 CHECK 约束；
- 全量测试 `62 passed`。

## 本周技术总结

- 业务订单访问使用 `order_no + user_id` 双条件授权；
- Agent 工具只接受业务参数，系统身份不进入模型参数；
- 工具调用必须可审计，失败内容要脱敏；
- 模型只负责意图和槽位提取，后端负责流程和状态；
- 确定性规则与模型输出组合，减少模型漏提取和空值覆盖；
- 状态必须持久化，并通过数据库约束和允许转换集合保护；
- 每个开发阶段都包含正常、异常和权限测试。

## 当前边界

- 意图、工具和状态机已经有独立服务和测试；
- `/chat/sessions/{id}/messages` 仍使用原有 RAG 路径，尚未接入新编排器；
- 还没有真正查询订单后组合政策回答；
- 还没有创建 handoff 记录、客服接管接口和前端；
- Day 6 将实现多轮信息补齐并开始接入编排流程。

## 本周复盘文档调整

- 从本周开始不再创建每日复盘文件；
- 每周只维护 `docs/WEEK{周数}_REVIEW.md`；
- 每个开发日统一记录：完成内容、实际实现、使用技术、遇到的问题、解决方式和验收结果；
- 原有 Day 1～10 内容已合并到 Week 1 和 Week 2。
