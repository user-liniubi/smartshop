# SmartService AI 架构说明

> 当前定位：单商家售后智能客服的本地可运行技术原型，不是生产部署。
> `开发手册-售后闭环V2.md` 是唯一执行路线；根目录旧手册仅作为历史材料。

## 系统架构

```mermaid
graph TB
    Consumer[消费者 Streamlit] --> API[FastAPI]
    AgentUI[客服 Streamlit] --> API

    API --> Request[请求 ID / 日志中间件]
    Request --> Auth[认证与对象级权限]
    Auth --> Chat[Chat / Agent API]
    Auth --> Knowledge[知识库 API]
    Auth --> Handoff[人工接管 API]

    Chat --> Orchestrator[售后编排器]
    Orchestrator --> Intent[DeepSeek 意图与槽位]
    Orchestrator --> Tools[工具白名单]
    Orchestrator --> RAG[BGE + Chroma]
    Orchestrator --> Rules[确定性规则]

    Tools --> MySQL[(MySQL)]
    Handoff --> MySQL
    Knowledge --> MySQL
    Knowledge --> Chroma[(Chroma)]
    RAG --> Chroma
    Intent --> DeepSeek[DeepSeek API]
    RAG --> DeepSeek
```

## 售后请求时序

```mermaid
sequenceDiagram
    participant U as 消费者
    participant API as FastAPI
    participant A as AgentService
    participant I as IntentService
    participant T as ToolRegistry
    participant DB as MySQL
    participant R as RAG
    participant L as DeepSeek
    participant H as Handoff

    U->>API: 发送售后消息
    API->>API: 校验 Token 和会话归属
    API->>DB: 先保存用户消息
    API->>A: 进入售后编排
    A->>I: 提取意图与槽位
    I->>L: 结构化 JSON 请求
    L-->>I: intent + slots
    A->>A: 合并槽位并校验状态
    alt 信息不完整
        A->>DB: 保存追问
        A-->>U: ask_more_info
    else 需要订单
        A->>L: 请求工具选择
        A->>T: 执行 get_my_order
        T->>DB: order_no + user_id 查询
        A->>R: 检索商品售后政策
        R-->>A: evidence + citations
        A->>L: 订单事实 + 政策证据
        A->>A: 确定性安全规则
        A->>DB: 保存回答、引用和审计
        A-->>U: answer
    end
```

## 任务状态机

```mermaid
stateDiagram-v2
    [*] --> collecting_info
    collecting_info --> collecting_info: 信息仍缺失
    collecting_info --> checking_order: 槽位完整
    checking_order --> checking_policy: 订单查询成功
    checking_order --> collecting_info: 订单无效
    checking_policy --> answer_ready: 找到有效证据
    checking_policy --> need_human: 无依据或风险较高
    answer_ready --> resolved: 保存回答
    collecting_info --> need_human: 用户主动转人工
    checking_order --> need_human: 订单异常或工具失败
```

`chat_sessions.status` 表示渠道由 AI 还是人工控制；`workflow_state` 表示售后任务阶段，两者不能合并。

## 人工接管时序

```mermaid
sequenceDiagram
    participant U as 消费者
    participant API as Chat API
    participant H as Handoff
    participant A as 客服工作台
    participant DB as MySQL

    U->>API: 申请人工
    API->>H: 幂等创建 handoff
    H->>DB: status=pending
    A->>API: 查看待接管队列
    A->>API: 接管 handoff
    API->>DB: UPDATE WHERE status=pending
    DB-->>API: affected_rows=1
    API->>DB: session.status=human_active
    A->>API: 人工回复
    API->>DB: 保存 sender_type=agent
    U->>API: 继续发送消息
    API->>DB: 保存消息，不调用 AI
    A->>API: 关闭会话
    API->>DB: 写入 closed_at
```

## 异步文档索引时序

```mermaid
sequenceDiagram
    participant A as 客服
    participant API as FastAPI
    participant FS as 上传目录
    participant DB as MySQL
    participant Q as Redis / Celery
    participant W as Celery Worker
    participant V as Chroma

    A->>API: POST /knowledge/upload-async
    API->>API: 校验角色、扩展名与文件大小
    API->>FS: 保存内容哈希命名的文件
    API->>DB: 创建 ingestion_jobs(status=pending)
    API->>Q: 投递 task_id
    API-->>A: 202 + task_id
    Q->>W: 消费索引任务
    W->>DB: status=started, progress=10
    W->>FS: 解析文档并分块
    W->>V: 写入 BGE 向量
    W->>DB: 保存文档与 chunks
    W->>DB: status=success, progress=100
    A->>API: GET /knowledge/jobs/{task_id}
    API->>DB: 读取任务状态
    API-->>A: pending / started / success / failure
```

任务状态以 MySQL `ingestion_jobs` 为准，Redis 只承担任务投递。成功任务重复执行时直接返回原结果；临时数据库错误有限重试，解析或业务错误直接标记失败。

## 文档删除时序

删除接口先按 MySQL 中的 `vector_id` 清理 Chroma，再在同一数据库事务中删除 `documents` 及其级联 `document_chunks`。两次操作之间是短暂一致性窗口；若数据库提交失败，可重新发起删除，向量删除本身是幂等的。

## 数据边界

| 数据 | 唯一可信来源 | 不允许的行为 |
|---|---|---|
| 用户身份 | Bearer Token + `users` | 信任模型或前端传入的 `user_id` |
| 订单事实 | MySQL `orders + products` | 从向量库或模型常识猜测订单状态 |
| 售后政策 | Chroma 检索片段 + 来源文档 | 无证据时编造退款资格 |
| 会话状态 | 后端状态机 | 模型直接写数据库状态 |
| 工具调用 | ToolRegistry + `tool_invocations` | 任意 SQL 或未注册工具 |

## 可观测性

- 每个请求生成 32 位 `X-Request-ID`；
- 请求日志包含方法、路径、状态和总耗时；
- Agent 记录意图、编排、工具、检索和模型耗时；
- 日志不记录 Token、API Key、密码或完整 Prompt；
- 工具审计表记录工具名、脱敏参数、结果摘要、状态和耗时。
