# SmartShop AfterSales 技术亮点与源码证据

> 项目定位：面向消费电子售后的可信决策系统，采用证据约束 RAG、受控业务工作流、有限 Tool Calling 和人在回路。核心演示商品为头戴式无线降噪耳机，知识库同时覆盖键盘、显示器、笔记本和鼠标。
>
> 边界：模型参与意图、槽位、工具候选和答案生成；流程、权限、并发与异常由后端控制。项目没有多工具自主规划和循环，不应表述为完整 RAG + Agent。

## 1. 受控 Tool Calling

**事实**：模型只选择白名单工具和业务参数；用户身份由服务端注入。

**源码证据**：

- `backend/app/agent/tools.py`
- `backend/app/services/llm.py`
- `tests/unit/test_llm.py`
- `tests/integration/test_tools.py`

**可讲重点**：参数使用 Pydantic 严格校验，`user_id` 不是工具参数，所有调用写入审计表。

## 2. 订单事实与 RAG 分离

**事实**：订单状态只查 MySQL，售后政策只查 Chroma，再把两类信息组合给模型。

**源码证据**：

- `backend/app/agent/service.py`
- `backend/app/services/rag.py`
- `backend/app/services/answers.py`
- `tests/integration/test_after_sales_agent.py`

**可讲重点**：价格、库存和订单状态是可变化、强权限数据，不能放入向量库。

## 3. 多轮槽位与后端状态机

**事实**：意图和槽位由模型提取，但合并、缺失校验和工作流状态由后端控制。

**源码证据**：

- `backend/app/agent/intent.py`
- `backend/app/agent/orchestrator.py`
- `tests/unit/test_intent.py`
- `tests/integration/test_orchestrator.py`

**真实问题**：模型补充订单号时曾把 `return` 覆盖成 `order_query`，导致跳过故障追问；修复为保留进行中的退货/换货任务。

## 4. 对象级权限与提示注入防护

**事实**：订单和会话查询都同时过滤业务 ID 与认证用户身份；文档内容只作为不可信证据。

**源码证据**：

- `backend/app/api/dependencies.py`
- `backend/app/repositories/orders.py`
- `backend/app/repositories/chat.py`
- `tests/integration/test_orders.py`
- `tests/integration/test_handoffs.py`
- `tests/unit/test_llm.py`

**可讲重点**：其他用户订单统一返回 `order_not_found`，避免通过 403 判断订单存在性。

## 5. 人工接管事务与双重回复防护

**事实**：客服接管使用带 `status='pending'` 条件的单条 UPDATE；AI 回复保存前再次检查会话状态。

**源码证据**：

- `backend/app/repositories/handoffs.py`
- `backend/app/services/handoffs.py`
- `backend/app/agent/service.py`
- `tests/integration/test_handoffs.py`
- `tests/integration/test_late_ai_response.py`

**可讲重点**：不使用进程内存锁；并发接管依赖数据库原子性。

## 6. 固定评测与可观测性

**事实**：31 条固定场景覆盖意图、工具、RAG、越权和提示注入；每个请求有 request ID 和阶段耗时。

**源码证据**：

- `data/eval/after_sales_questions.jsonl`
- `scripts/run_eval.py`
- `data/eval/latest_report.md`
- `backend/app/core/middleware.py`
- `docs/ARCHITECTURE.md`

**边界**：31 条自建样本不能代表生产泛化准确率，最终回答和引用支持度仍需人工抽检。

## 建议面试顺序

1. 用 60 秒介绍业务闭环和技术栈。
2. 明确这是证据约束 RAG + 受控工作流 + 人在回路，而不是自主 Agent。
3. 讲受控工具和对象级权限。
4. 讲多轮槽位与状态机。
5. 讲订单事实和 RAG 的职责分离。
6. 讲人工接管并发和迟到 AI 响应。
7. 最后给真实评测数字、测试范围和未完成边界。

## 7. 退换货自动建单与审批

**事实**：明确申请退换货且订单、政策校验通过时，后端幂等创建待审批工单；客服通过或拒绝。

**源码证据**：

- `backend/app/services/after_sales_tickets.py`
- `backend/app/repositories/after_sales_tickets.py`
- `backend/app/api/routes/after_sales_agent.py`
- `tests/integration/test_after_sales_tickets.py`

**边界**：工单存放在本项目 MySQL，不执行真实退款、换货或物流操作。
