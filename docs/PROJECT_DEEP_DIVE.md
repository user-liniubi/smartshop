# SmartShop AI 项目深挖与复习手册

> 项目版本：`v1.0.0`
> 当前定位：面向消费电子产品的单商家售后高级 RAG 应用，采用受控业务工作流和有限 Tool Calling
> 核心商品：头戴式无线降噪耳机，知识库同时覆盖键盘、显示器、笔记本和鼠标
> 文档用途：项目讲解、源码阅读、面试深挖、演示前复习
> 最后更新：2026-11-13

> 技术边界：模型参与意图、槽位、有限订单工具候选和答案生成；追问、状态流转、权限、并发和异常由后端控制。项目没有多工具自主规划和循环，不是完整的 RAG + Agent。

---

## 0. 如何使用这份手册

### 0.1 30 分钟快速复习

适合面试前或演示前快速恢复记忆：

1. 阅读第 1～4 节，明确项目定位、业务边界和技术栈；
2. 能手画第 6 节的“消费者售后主链路”；
3. 阅读第 8～13 节，记住状态机、权限、并发和失败降级；
4. 背熟第 19 节的 3 分钟项目介绍；
5. 浏览第 20 节“不能说错的边界”。

### 0.2 两小时源码复习

适合真正理解代码：

1. 阅读第 5～7 节，建立系统结构和数据模型；
2. 按第 18 节顺序阅读源码；
3. 运行第 17节的演示流程；
4. 用第 21 节问题自测；
5. 对回答不出的条目回到源码和测试。

### 0.3 手册之间的关系

| 文档 | 用途 |
|---|---|
| `README.md` | 启动、接口、配置和功能总览 |
| `docs/开发手册-售后闭环V2.md` | V2 实施过程、设计和验收标准 |
| `docs/ARCHITECTURE.md` | 架构图、状态机图和时序图 |
| `docs/FINAL_ACCEPTANCE.md` | 最终验收、测试和真实闭环证据 |
| `docs/RAG_INTERVIEW_GUIDE.md` | RAG 参数和面试追问深入版 |
| `docs/PROJECT_DEEP_DIVE.md` | 当前这份总复习手册 |

---

## 1. 一句话项目定位

> SmartShop AI 是一个面向消费电子产品的单商家售后高级 RAG 系统，采用受控业务工作流和有限 Tool Calling。消费者可以用自然语言完成售后咨询，系统通过受控订单工具查询本人订单，通过 RAG 检索售后政策与商品说明，生成带来源建议，并在复杂或风险场景下转交人工客服。

项目从“消费者已经拥有订单”开始，不覆盖购物车、下单、支付和真实物流。

---

## 2. 业务背景

### 2.1 目标用户

| 用户 | 核心诉求 |
|---|---|
| 消费电子消费者 | 咨询耳机无声、连接、电池、退货、换货、保修、配送和产品使用方法 |
| 商家客服 | 查看待处理会话、订单上下文和对话历史，接管并回复复杂问题 |

商家是业务主体，不作为单独登录角色。当前实现消费者和客服两个操作角色。

### 2.2 需要解决的问题

- 订单事实在业务数据库中；
- 售后政策、质保规则和商品说明分散在文档中；
- 普通搜索无法稳定理解自然语言；
- 大模型可能编造订单状态、退款资格或已完成操作；
- 消费者不能查询他人订单；
- 多轮信息可能丢失或被错误覆盖；
- 复杂问题需要从 AI 平滑转到人工。

### 2.3 最终业务闭环

```text
消费者提问
→ 识别售后意图
→ 多轮补齐订单号和故障描述
→ 查询当前用户订单
→ 检索商品政策和商品说明
→ 组合订单事实与证据生成回答
→ 安全规则复核
→ 可解决则结束
→ 需要人工则客服接管、回复和关闭
```

---

## 3. 当前完成状态

### 3.1 已完成能力

- FastAPI 后端和统一异常处理；
- MySQL、SQLAlchemy 2、Alembic；
- 登录与 Token 校验；
- 订单和会话对象级权限；
- 消费者会话、消息和历史；
- DeepSeek 意图、槽位、有限订单工具候选和回答生成；
- Tool Calling 白名单、参数校验和审计；
- 多轮槽位收集；
- 后端权威工作流状态机；
- MySQL 订单事实 + RAG 政策组合；
- 确定性售后安全规则；
- 退换货申请自动生成待审批工单；
- 客服通过/拒绝工单及原子审批；
- 转人工、客服原子接管、回复和关闭；
- 消费者 Streamlit 页面；
- 客服 Streamlit 工作台；
- Markdown、TXT、PDF 知识解析；
- BGE + Chroma 检索；
- 来源引用和无依据拒答；
- Redis + Celery 异步文档索引；
- MySQL/Chroma 双存储删除；
- 请求 ID、阶段耗时和安全日志；
- 31 条固定评测；
- 101 项自动化测试。

### 3.2 不是本项目的内容

- 商品浏览、购物车、下单和支付；
- 真实退款、真实物流和库存扣减；
- 多商家经营和平台管理员；
- 大规模生产部署和高可用；
- 复杂多 Agent 协作；
- 模型训练或微调。

---

## 4. 技术栈

| 层 | 技术 | 在本项目中的作用 |
|---|---|---|
| 语言 | Python 3.11 | 后端、Worker、脚本和 Streamlit |
| 依赖 | uv | 锁定环境与依赖 |
| API | FastAPI + Uvicorn | 路由、依赖注入、Swagger |
| 校验 | Pydantic v2 | 请求、槽位、工具参数和结构化输出 |
| 数据 | MySQL 8 | 订单、会话、接管、文档和任务状态 |
| ORM | SQLAlchemy 2 | 数据模型、查询和关系 |
| 迁移 | Alembic | 数据库版本管理 |
| 模型 | DeepSeek Chat API | 意图、槽位、有限订单工具候选、回答生成 |
| 文档 | PyMuPDF | PDF 文本和页码提取 |
| Embedding | BGE-small-zh-v1.5 | 中文语义向量 |
| 向量库 | Chroma | 本地持久化向量检索 |
| 异步 | Redis + Celery | 文档异步索引 |
| 前端 | Streamlit | 消费者端和客服工作台 |
| 测试 | pytest + httpx | 单元、集成、页面和端到端测试 |
| 质量 | Ruff | 静态检查和格式化 |

---

## 5. 系统架构

```text
消费者 Streamlit                  客服 Streamlit
       │                               │
       └──────────── HTTP ─────────────┘
                       │
                    FastAPI
                       │
        ┌──────────────┼───────────────┐
        │              │               │
     认证/权限     售后受控工作流     知识库 API
                       │               │
        ┌──────────────┼──────────┐    │
        │              │          │    │
   意图/槽位        订单工具      RAG   │
        │              │          │    │
   后端状态机        MySQL      Chroma  │
        │                         │     │
    安全规则                   BGE/DeepSeek
        │
   人工接管 ──────────────── MySQL
   售后工单审批 ───────────── MySQL

知识异步索引：FastAPI → Redis → Celery Worker → BGE → Chroma + MySQL
```

### 5.1 分层职责

| 层 | 主要职责 |
|---|---|
| API | 认证依赖、参数校验、HTTP 响应 |
| 售后工作流 | 多轮状态、意图、有限工具调用和工单审批 |
| Service | RAG、回答、规则、人工接管等业务 |
| Repository | SQL 查询与持久化 |
| Model | 表、状态、关系和约束 |
| RAG | 解析、分块、Embedding、向量检索 |
| Worker | 异步索引、任务状态和失败处理 |
| Frontend | 消费者和客服操作界面 |

---

## 6. 核心调用链

### 6.1 登录与身份

```text
POST /auth/login
→ AuthService.login
→ 按用户名查 User
→ scrypt 校验密码
→ 签发带过期时间和角色声明的签名 Token
→ 后续请求由 HTTPBearer 解析
→ 按 Token 中的 user_id 重新查询数据库
→ 校验数据库角色与 Token 角色一致
```

源码：

- `backend/app/api/routes/auth.py`
- `backend/app/services/auth.py`
- `backend/app/core/security.py`
- `backend/app/api/dependencies.py`

为什么角色要回数据库检查：

- Token 只应作为身份声明；
- 用户被删除或角色被修改后，旧 Token 不应继续拥有旧权限。

### 6.2 订单查询

```text
GET /orders/by-number/{order_no}
→ CurrentUser
→ OrderService
→ Repository 查询 order_no AND user_id
→ selectinload 商品
→ 不存在时统一 order_not_found
```

源码：

- `backend/app/api/routes/orders.py`
- `backend/app/services/orders.py`
- `backend/app/repositories/orders.py`

关键点：

- 用户 ID 来自认证，不来自路径或模型；
- 查询条件同时包含业务订单号和用户 ID；
- 不先查订单再在 Python 中比较 owner；
- 他人订单返回 404，降低订单枚举风险。

### 6.3 消费者发送售后消息

```text
POST /chat/sessions/{session_id}/messages
→ 校验会话属于当前用户
→ 先保存消费者消息到 MySQL
→ 如果会话正在等待人工或已关闭，只保存消息
→ IntentService 提取意图和槽位
→ AfterSalesOrchestrator 合并槽位并决定动作
→ 缺信息：生成追问
→ 订单任务：规划并执行 get_my_order
→ 根据订单 product_id 检索政策
→ AnswerService 生成回答
→ AfterSalesRuleService 复核
→ 明确的退换货申请：幂等创建 pending_approval 工单
→ 保存 AI 消息和 citations
→ 返回 action、workflow_state、tool_results
```

源码：

- `backend/app/api/routes/chat.py`
- `backend/app/agent/service.py`
- `backend/app/agent/intent.py`
- `backend/app/agent/orchestrator.py`
- `backend/app/agent/tools.py`
- `backend/app/services/answers.py`
- `backend/app/services/rules.py`

### 6.4 三类核心分支

#### 缺少信息

```text
退货请求 + 没有订单号/故障描述
→ collecting_info
→ ask_more_info
→ 返回 missing_slots
```

下一轮只追问仍缺少的字段。补充订单号时保留已有退货/换货意图，避免模型把任务改成普通订单查询。

#### 订单售后

```text
退货/换货意图 + 信息齐全
→ checking_order
→ get_my_order(order_no)
→ MySQL 查询本人订单
→ product_id 写入 slots
→ checking_policy
→ 检索商品专属资料 + 全局政策
→ 明确申请退换货且规则通过
→ 创建 pending_approval 工单
→ answer_ready
→ 保存回答
→ resolved
```

#### 普通政策问题

```text
保修/政策意图
→ 不要求订单号
→ 直接检索政策
→ 有证据时生成回答
→ 无证据时转人工
```

### 6.5 转人工与客服接管

```text
消费者申请 / 用户请求人工 / 模型失败 / 无依据 / 规则升级
→ Handoff pending
→ session.status=need_human
→ 客服查看待接管队列
→ 条件 UPDATE handoff SET claimed WHERE status=pending
→ rowcount=1 才成功
→ 同一事务更新 session.status=human_active
→ 客服读取会话、消息和订单上下文
→ 客服回复
→ 客服关闭
```

源码：

- `backend/app/api/routes/agent.py`
- `backend/app/services/handoffs.py`
- `backend/app/repositories/handoffs.py`

### 6.6 防止 AI 与人工双答

AI 调用可能持续数秒。客服可能在模型返回前完成接管。

项目在保存 AI 消息前重新读取会话状态：

- 如果还是 `open`，允许保存 AI 回复；
- 如果已经 `need_human`、`human_active` 或 `closed`，丢弃迟到的 AI 回复；
- 消费者消息已经先保存，不会因为人工接管或模型失败丢失。

源码证据：

- `backend/app/agent/service.py::AfterSalesAgentService._ai_reply_allowed`
- `tests/integration/test_late_ai_response.py`

### 6.7 知识同步入库

```text
客服上传文件
→ 校验客服角色、扩展名、大小和路径
→ 保存上传文件
→ 计算文件 SHA-256
→ 若重复直接返回已有 Document
→ 解析 Markdown/TXT/PDF
→ 清洗并按标题或页面得到 Section
→ 500 字符分块，80 字符 overlap
→ BGE 批量生成归一化向量
→ 写入 Chroma
→ 写入 documents 和 document_chunks
→ MySQL 提交，状态 indexed
```

### 6.8 知识异步入库

```text
POST /knowledge/upload-async
→ 保存文件
→ MySQL 创建 ingestion_jobs(pending)
→ Redis/Celery 投递 task_id
→ 返回 202 + task_id
→ Worker 读取任务
→ started / progress=10
→ 解析和 Embedding / progress=30
→ Chroma + MySQL
→ success / progress=100
```

`GET /knowledge/jobs/{task_id}` 查询状态。

### 6.9 文档删除

```text
DELETE /knowledge/documents/{id}
→ 从 MySQL 读取所有 vector_id
→ 删除 Chroma 向量
→ 删除 documents
→ 级联删除 document_chunks
→ 返回 204
```

当前删除顺序存在短暂一致性窗口：向量已删除但 MySQL 尚未提交。操作可重试，向量删除是幂等的。

---

## 7. 数据模型

| 表 | 作用 | 关键约束 |
|---|---|---|
| `users` | 消费者和客服账号 | 用户名唯一、角色 CHECK |
| `products` | 消费电子产品 | 商品名唯一 |
| `orders` | 虚构订单 | 订单号唯一、user/product 外键、状态 CHECK |
| `chat_sessions` | 会话和任务状态 | 会话状态 CHECK、工作流状态 CHECK、用户外键 |
| `chat_messages` | 消息和引用 | sender_type CHECK、会话与时间索引 |
| `handoffs` | 转人工和接管 | session_id 唯一、pending/claimed/closed、来源 user/ai/rule |
| `after_sales_tickets` | 退换货审批工单 | session_id 唯一、request_type/status CHECK、审批人 |
| `tool_invocations` | 工具调用审计 | 状态 success/error/blocked |
| `documents` | 知识文档 | 文件 SHA-256 唯一、索引状态 |
| `document_chunks` | Chunk 与向量映射 | document_id + chunk_index 唯一、vector_id 唯一 |
| `ingestion_jobs` | 异步任务 | task_id 唯一、状态和进度 |

### 7.1 状态字段必须区分

`chat_sessions.status`：

```text
open
need_human
human_active
closed
```

表示当前由 AI 还是人工控制。

`chat_sessions.workflow_state`：

```text
collecting_info
checking_order
checking_policy
answer_ready
need_human
resolved
```

表示售后任务阶段。

### 7.2 为什么不使用一个状态字段

一个字段无法同时表达：

- 当前是 AI 在推进；
- 还是已经等待人工；
- 售后的信息收集进行到哪一步。

拆分后，状态可组合且转换逻辑更容易测试。

---

## 8. 状态机与槽位

### 8.1 槽位

```text
order_no
issue_type
issue_description
product_id
```

其中 `product_id` 由订单工具查询结果补充，不由模型猜测。

### 8.2 槽位合并原则

- 模型返回空值时保留已有槽位；
- 订单号统一转大写；
- 非法历史槽位忽略；
- 用户明确提供新订单号时可更新；
- 已有退货/换货任务不被后续补充订单号误改成普通订单查询；
- 泛化“坏了”不足以作为具体故障描述，继续追问。

### 8.3 必需槽位

| 意图 | 必需信息 |
|---|---|
| 查询订单 | 订单号 |
| 退货 | 订单号 + 具体故障 |
| 换货 | 订单号 + 具体故障 |
| 普通政策/保修 | 可无订单号 |
| 人工 | 无 |

---

## 9. 受控售后工作流与 Tool Calling

### 9.1 后端工作流的职责

- 决定当前售后任务的下一步；
- 判断是否缺信息；
- 是否需要查询订单；
- 是否需要调用 RAG；
- 是否应结束或转人工；
- 持久化状态和消息。

这里的“决定下一步”由后端状态机和固定业务分支完成，不是模型自由规划。

### 9.2 LLM 的职责

- 从自然语言提取意图和候选槽位；
- 对一个允许的订单工具提出候选调用及参数；
- 基于已验证事实和检索证据生成回答。

模型不能：

- 直接访问数据库；
- 生成任意 SQL；
- 传入可信用户 ID；
- 直接修改会话和订单状态；
- 承诺已完成真实退款或换货。

### 9.3 订单工具

```text
get_my_order(order_no)
```

服务端注入当前 `user_id`，SQL 同时过滤订单号和用户。

### 9.4 RAG 与工作流的位置

当前主聊天链路中：

- 模型可提出一个订单工具候选，后端完成校验和执行；
- 政策检索由后端根据意图直接执行；
- ToolRegistry 还注册了 `search_after_sales_policy`，但主聊天链路没有把政策检索完全交给模型自由决定。

这个边界面试时必须讲准确，避免说成“模型自由选择所有工具”。

当前没有多轮工具执行循环，也没有工具失败后的自主重新规划，因此不能称为自主多步 Agent。

### 9.5 工具失败

如果模型工具规划失败，后端使用已提取订单号确定性调用订单查询。

如果订单不存在，返回可重试提示，不暴露订单是否存在。

### 9.6 退换货自动建单

模型从用户消息中输出 `submit_requested`。只有用户明确表达申请或提交退货、换货时，后端才在以下条件全部满足后创建工单：

- 当前意图是退货或换货；
- 订单号和故障描述完整；
- 订单属于当前用户且状态允许；
- RAG 找到满足阈值的政策证据；
- 安全规则未触发人工复核；
- 当前会话尚无其他售后工单。

工单初始状态为 `pending_approval`。大模型不能决定审批结果，也不能直接执行退款或换货。

---

## 10. RAG 核心参数

完整复习见 `docs/RAG_INTERVIEW_GUIDE.md`。

| 项目 | 当前值 |
|---|---|
| 文档类型 | Markdown、TXT、PDF |
| Chunk Size | 500 字符 |
| Chunk Overlap | 80 字符 |
| Embedding | `BAAI/bge-small-zh-v1.5` |
| 向量维度 | 512 |
| 向量距离 | Cosine |
| 相似度 | `1 - distance` |
| Top-K | 默认 4 |
| 最低相似度 | 0.5 |
| 商品过滤 | `product_id IN [当前商品, 0]` |
| Rerank | 未实现 |
| OCR | 未实现 |
| Hybrid Search | 未实现 |
| 当前知识规模 | 19 份文档、74 个 Chunk/向量 |

无依据时：

- 普通 RAG 不调用生成模型，返回固定拒答；
- 售后工作流转人工。

---

## 11. 订单事实、政策与规则

### 11.1 数据来源

| 数据 | 唯一来源 |
|---|---|
| 身份 | Token + MySQL users |
| 订单号、状态、商品归属 | MySQL orders/products |
| 售后政策、质保、商品说明 | Chroma 检索 |
| 会话和工作流状态 | MySQL chat_sessions |
| 工具审计 | MySQL tool_invocations |

### 11.2 确定性规则

当前规则包括：

- 已取消订单不适合直接按普通退货流程判断，转人工；
- 非订单查询且没有政策证据，转人工；
- 模型输出“已经退款”“退款成功”“已完成退换货”等越权承诺，替换并转人工。
- 只有明确提交的合规退换货申请才自动生成待审批工单。

规则不是完整售后业务政策，只承担安全边界。

---

## 12. 安全与权限

### 12.1 认证

- 用户名密码登录；
- scrypt 随机盐密码哈希；
- Token 有签名和过期时间；
- 用户被删除或角色变化后，旧 Token 失效。

### 12.2 对象级权限

- 消费者只能读取自己的会话；
- 消费者只能查询自己的订单；
- 客服只能操作自己已接管的会话；
- 消费者只能查看自己的售后工单；
- 只有客服可以审批售后工单；
- 消费者不能访问客服队列；
- 非客服不能接管或回复。

### 12.3 文档安全

- 只允许客服上传；
- 只支持 `.md`、`.txt`、`.pdf`；
- 限制上传大小；
- 文件名取 basename，避免路径穿越；
- 扫描 PDF 明确不支持 OCR；
- 文档内容作为不可信 Evidence，不作为系统指令。

### 12.4 错误响应

- 401：未登录或 Token 无效；
- 403：角色无权或会话不属于当前客服；
- 404：订单/会话不存在或不属于当前消费者；
- 409：接管冲突或会话已关闭；
- 422：参数或模型结构不合法；
- 500：未处理异常，不泄露堆栈。

---

## 13. 并发、幂等与故障降级

### 13.1 接管并发

接管 SQL 带 `status='pending'` 条件。两个客服同时操作时，只有一个 UPDATE 的 `rowcount=1`。

工单审批同样使用状态条件更新，只有仍为 `pending_approval` 的工单可以被审批，重复审批返回冲突。

### 13.2 转人工幂等

`handoffs.session_id` 唯一；重复申请返回已有 handoff，不重复创建。

### 13.3 模型失败

意图模型失败或回答模型失败时：

- 用户消息已经保存；
- 创建人工 handoff；
- 返回明确提示；
- 不让会话丢失。

### 13.4 无依据

- 普通 RAG 固定拒答；
- 复杂售后工作流转人工；
- 不把知识缺失说成订单缺失。

### 13.5 文件去重

- 文件 SHA-256 去重；
- 每块保存文本哈希；
- Chroma vector ID 为 `document_id:chunk_index`。

### 13.6 异步重试

- 临时数据库错误最多重试 2 次；
- 文档解析和业务错误直接失败；
- 成功任务重复执行直接返回原结果。

---

## 14. 可观测性

每个 HTTP 响应返回 `X-Request-ID`。

日志记录：

- 请求方法、路径、状态码和总耗时；
- 售后工作流记录意图、编排、工具、检索和模型阶段耗时；
- 异步 task_id；
- 工具名、脱敏参数、结果摘要、状态和耗时。

日志不记录：

- Token；
- 密码；
- API Key；
- 完整 Prompt；
- 无必要的敏感订单内容。

排查问题时应先拿请求 ID，再按阶段定位，而不是只凭“接口慢”猜测。

---

## 15. 测试与评测

### 15.1 自动化测试

当前全量：

```text
101 passed
```

目录：

- `tests/unit`：配置、意图、LLM、RAG 组件和规则；
- `tests/integration`：数据库、API、权限、售后工作流、接管和竞态；
- `tests/e2e`：消费者端和客服工作台页面。

关键测试文件：

| 文件 | 覆盖 |
|---|---|
| `tests/integration/test_after_sales_agent.py` | 三轮售后、订单越权、模型失败、转人工 |
| `tests/integration/test_handoffs.py` | 幂等申请、权限、接管、回复、关闭 |
| `tests/integration/test_late_ai_response.py` | 人工接管后迟到 AI 响应 |
| `tests/integration/test_tools.py` | 白名单、身份注入和审计 |
| `tests/unit/test_intent.py` | 意图、槽位遗漏和覆盖问题 |
| `tests/unit/test_rag_components.py` | 解析、分块、引用和阈值拒答 |
| `tests/e2e/test_streamlit_apps.py` | 双端页面关键视图 |

### 15.2 固定评测

数据集：

```text
data/eval/after_sales_questions.jsonl
```

31 条场景：

- 政策：8
- 相似商品干扰：4
- 无关问题：4
- 缺失信息：4
- 订单事实：3
- 提示注入：3
- 越权：2
- 退货、换货、保修：各 1

当前指标：

```text
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

### 15.3 必须正确解释

这些是全量固定回归集结果，不是：

- 生产环境准确率；
- 开放问题泛化能力；
- 最终回答正确率；
- 引用支持度；
- 高并发压测结果。

当前尚未完成最终回答正确率和引用支持度的大规模人工抽检。

---

## 16. 关键设计取舍

| 决策 | 选择 | 原因 | 代价/边界 |
|---|---|---|---|
| 业务范围 | 消费电子售后纵向切片 | 做深高级 RAG/受控工作流/人机协同 | 不覆盖完整购物交易 |
| 订单访问 | MySQL 精确查询 | 实时、强权限、结构化 | 需要对象级授权 |
| 政策知识 | RAG | 可更新、可引用 | 依赖文档和检索质量 |
| 工具调用 | 白名单 | 防任意 SQL/工具 | 能力受注册工具限制 |
| 用户身份 | 服务端注入 | 防模型伪造 | 工具不能接受 user_id |
| 工作流 | 后端状态机 | 可测试、可控制 | 需要维护状态转换 |
| 人工抢单 | 数据库条件更新 | 多进程有效、原子 | 需要处理冲突和重试 |
| 延迟 AI | 保存前复核状态 | 防 AI/人工双答 | 可能丢弃已消耗的模型结果 |
| 知识入库 | 同步 + 异步 | 兼容简单和长任务 | 两套链路增加维护成本 |
| 向量库 | Chroma | 本地简单、够用 | 非生产高可用方案 |

---

## 17. 本地运行与演示

### 17.1 启动

```powershell
docker start smartshop-mysql-dev
docker start redis
uv run alembic upgrade head
uv run uvicorn backend.app.main:app --reload
```

另开终端：

```powershell
uv run celery -A backend.app.workers.celery_app:celery_app worker --loglevel=INFO --pool=solo
uv run streamlit run frontend/consumer_app.py --server.port 8501
uv run streamlit run frontend/agent_app.py --server.port 8502
```

访问：

```text
消费者端：http://127.0.0.1:8501
客服端：http://127.0.0.1:8502
Swagger：http://127.0.0.1:8000/docs
```

### 17.2 演示对话

消费者：

```text
consumer_demo / Demo123!
```

输入：

```text
耳机坏了，想退货
订单号 A10086
左耳没有声音
```

客服：

```text
agent_demo / Agent123!
```

申请人工后接管、回复、关闭。

---

## 18. 源码阅读顺序

### 第 1 步：应用入口与分层

阅读：

- `backend/app/main.py`
- `backend/app/api/router.py`
- `backend/app/core/config.py`
- `backend/app/core/exceptions.py`

目标：能说明应用工厂、路由注册、配置和统一错误。

### 第 2 步：数据模型

阅读：

- `backend/app/models/entities.py`
- `backend/app/models/enums.py`
- `backend/app/models/__init__.py`

目标：能解释 10 张表、关系、约束和两种状态字段。

### 第 3 步：认证与订单权限

阅读：

- `backend/app/api/dependencies.py`
- `backend/app/core/security.py`
- `backend/app/services/orders.py`
- `backend/app/repositories/orders.py`

目标：能用 SQL 条件解释对象级授权。

### 第 4 步：意图、槽位和状态机

阅读：

- `backend/app/agent/schemas.py`
- `backend/app/agent/intent.py`
- `backend/app/agent/orchestrator.py`
- `backend/app/agent/service.py`

目标：能说清模型输出与后端权威状态的边界。

### 第 5 步：工具调用

阅读：

- `backend/app/agent/tools.py`
- `backend/app/repositories/tool_invocations.py`
- `backend/app/services/llm.py`

目标：能完整讲出工具 Schema、参数校验、身份注入、执行和审计。

### 第 6 步：RAG

阅读：

- `backend/app/rag/parsing.py`
- `backend/app/rag/chunking.py`
- `backend/app/rag/embeddings.py`
- `backend/app/rag/vector_store.py`
- `backend/app/services/rag.py`
- `backend/app/services/knowledge.py`

目标：能画出入库和在线问答两条链路，讲清参数。

### 第 7 步：人工接管

阅读：

- `backend/app/services/handoffs.py`
- `backend/app/repositories/handoffs.py`
- `backend/app/api/routes/agent.py`
- `tests/integration/test_handoffs.py`
- `tests/integration/test_late_ai_response.py`

目标：能解释条件更新、事务、权限和迟到回复。

### 第 8 步：异步索引与观测

阅读：

- `backend/app/workers/celery_app.py`
- `backend/app/workers/tasks.py`
- `backend/app/core/middleware.py`
- `backend/app/core/request_context.py`

目标：能讲清 Redis、Celery、MySQL 任务状态和请求 ID。

### 第 9 步：测试和评测

阅读：

- `tests/integration/test_after_sales_agent.py`
- `tests/unit/test_intent.py`
- `tests/unit/test_rag_components.py`
- `scripts/run_eval.py`
- `data/eval/latest_report.md`

目标：能解释质量证据和指标边界。

---

## 19. 三分钟项目介绍

> SmartShop AI 是一个面向消费电子产品的单商家售后高级 RAG 系统，核心场景是头戴式无线降噪耳机，同时覆盖键盘、显示器、笔记本和鼠标。消费者遇到退货、换货、保修、连接或产品使用问题时，可以直接用自然语言咨询。LLM 辅助提取意图和槽位，后端工作流在缺少订单号或故障描述时继续追问；信息齐全后，通过受控订单工具查询当前消费者本人的订单，订单事实只来自 MySQL。随后系统根据订单中的商品 ID，从 BGE + Chroma 知识库检索对应商品说明和全局售后政策，再由 DeepSeek 结合订单事实与政策证据生成带来源建议。用户明确申请退换货且订单、政策校验通过时，系统自动创建待审批工单，客服在工作台通过或拒绝。无依据、订单异常或规则不允许时，系统转人工处理。项目目前完成了消费者端、客服端、异步文档索引、双存储删除和 31 条固定评测，全量自动化测试 101 项通过。需要明确的是，审批工单目前只写入本项目数据库，不执行真实退款、换货或物流操作。

---

## 20. 不能说错的边界

- 不是完整电商商城；
- 不执行真实支付、退款和物流；
- 不是多商家 SaaS；
- 不是生产级高可用系统；
- Streamlit 不是商业级 React/Vue 前端；
- 31 条固定集 100% 不是生产准确率；
- Citation 存在不等于引用严格支持每个结论；
- 当前没有 Rerank、Hybrid Search 和 OCR；
- 主聊天链路不是让模型完全自由选择所有工具；
- 不是完整 RAG + Agent，没有多工具自主规划和循环；
- 工单审批是内部模拟流程，尚未对接真实企业售后、退款和物流系统；
- Celery 当前是单机 Worker，没有生产级队列监控和死信处理；
- 删除向量和提交 MySQL 之间有短暂一致性窗口。

---

## 21. 面试深挖题库

### 21.1 项目与业务

1. 为什么只做消费电子售后，不做完整商城？
2. 为什么只有消费者和客服两个操作角色？
3. 消费者、客服、LLM、后端工作流、规则和 RAG 分别负责什么？
4. 为什么从已有订单开始？
5. 这个项目的真正技术难点是什么？

### 21.2 数据与权限

6. 为什么订单查询要同时匹配订单号和用户 ID？
7. 为什么返回 404 而不是 403？
8. Token 中的角色为什么要和数据库复核？
9. 客服如何证明自己有权读取某个会话？
10. 为什么不信任模型传入的 user_id？

### 21.3 受控工作流与 Tool Calling

11. 售后受控工作流主链路是什么？
12. 槽位为什么存数据库而不是只放 Prompt？
13. 模型把退货意图误改成订单查询时怎么处理？
14. 如何避免模型执行任意工具或 SQL？
15. 工具调用失败后如何继续？
16. 为什么后端控制状态转换？

### 21.4 RAG

17. 为什么订单状态不放进向量库？
18. Chunk 和 overlap 如何设置？
19. Cosine distance 如何转成 similarity？
20. Top-K 和阈值分别控制什么？
21. 如何避免不同商品资料串在一起？
22. 没有检索证据时怎么办？
23. 引用是如何生成的，能证明什么？
24. 如何定位召回错误和生成错误？

### 21.5 人机协同与可靠性

25. 两个客服同时接管会发生什么？
26. 为什么不用进程内锁？
27. 人工接管后迟到的 AI 回复怎么处理？
28. 模型超时或工具失败会丢失用户消息吗？
29. 异步索引重复执行怎么办？
30. 删除文档时 MySQL 和 Chroma 如何保持一致？

### 21.6 测试与边界

31. 101 项测试覆盖了什么？
32. 31 条固定评测为什么都是 1.0？
33. Hit@3 和最终回答正确率有什么区别？
34. 如果上线生产，最需要补什么？
35. 你能亲自解释哪些代码，哪些只是参考实现？

每个问题都应至少能回答：

```text
业务问题是什么
→ 为什么这样设计
→ 真实代码在哪里
→ 怎么测试或验证
→ 目前还有什么边界
```

---

## 22. 复习检查表

### 业务

- [ ] 能说明项目为谁解决什么问题
- [ ] 能说明为什么不做购物和支付
- [ ] 能说明耳机核心场景和五类商品范围

### 架构

- [ ] 能画出消费者、FastAPI、售后工作流、MySQL、Chroma、DeepSeek、客服端
- [ ] 能画出同步与异步文档入库
- [ ] 能区分 API、Service、Repository、Model 职责

### 受控工作流与 Tool Calling

- [ ] 能讲清意图、槽位、动作和工作流状态
- [ ] 能讲清工具白名单和身份注入
- [ ] 能讲清订单事实与政策证据组合
- [ ] 能讲清退换货自动建单和客服审批

### RAG

- [ ] 能讲清解析、分块、Embedding、Top-K、阈值
- [ ] 能解释 `similarity=1-distance`
- [ ] 能解释商品 metadata 过滤
- [ ] 能说明引用和拒答边界

### 并发与可靠性

- [ ] 能解释条件更新抢占
- [ ] 能解释 AI 回复前状态复核
- [ ] 能解释异步任务幂等和有限重试
- [ ] 能解释双存储删除的一致性窗口

### 质量

- [ ] 能解释 101 项测试的范围
- [ ] 能解释 31 条固定评测及指标
- [ ] 能主动说明 100% 不是生产准确率
- [ ] 能说明缺引用支持度人工抽检

---

## 23. 源码证据总索引

| 主题 | 路径与符号 |
|---|---|
| 应用入口 | `backend/app/main.py::create_app` |
| 路由注册 | `backend/app/api/router.py::api_router` |
| 认证 | `backend/app/api/dependencies.py::get_current_user` |
| 订单权限 | `backend/app/repositories/orders.py::get_order_owned_by_user_and_no` |
| 聊天入口 | `backend/app/api/routes/chat.py::send_message` |
| 售后工作流编排 | `backend/app/agent/service.py::AfterSalesAgentService.handle_message` |
| 意图 | `backend/app/agent/intent.py::IntentService.extract` |
| 状态机 | `backend/app/agent/orchestrator.py::AfterSalesOrchestrator` |
| 工具 | `backend/app/agent/tools.py::ToolRegistry` |
| 工单创建 | `backend/app/services/after_sales_tickets.py::AfterSalesTicketService` |
| 工单审批 | `backend/app/api/routes/after_sales_agent.py` |
| 回答 | `backend/app/services/answers.py::AnswerService.generate` |
| 规则 | `backend/app/services/rules.py::AfterSalesRuleService` |
| RAG | `backend/app/services/rag.py::RAGService` |
| 入库 | `backend/app/services/knowledge.py::KnowledgeService` |
| 人工接管 | `backend/app/services/handoffs.py::HandoffService` |
| 原子抢占 | `backend/app/repositories/handoffs.py::claim_handoff_atomic` |
| 异步 Worker | `backend/app/workers/tasks.py::ingest_document_task` |
| 请求 ID | `backend/app/core/middleware.py` |
| 模型调用 | `backend/app/services/llm.py::DeepSeekClient` |
| 数据模型 | `backend/app/models/entities.py` |
| 固定评测 | `scripts/run_eval.py` |
| 架构文档 | `docs/ARCHITECTURE.md` |
| RAG 深入版 | `docs/RAG_INTERVIEW_GUIDE.md` |

---

## 24. 自学提醒

如果某个文件或原理看不懂，请继续围绕具体文件、函数和调用链追问。这份手册提供学习路径、源码证据和面试边界，不替代逐行阅读实现。
