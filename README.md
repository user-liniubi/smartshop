# SmartShop AI

SmartShop AI 是一个面向 AI 应用开发求职的智能电商项目。当前完成第一阶段第二周：会话持久化、DeepSeek 客户端、售后知识文档、BGE + Chroma 检索和带来源引用的 RAG 接口。

## 环境要求

- Python 3.11
- uv
- Git

项目固定使用 Python 3.11，依赖由 `pyproject.toml` 与 `uv.lock` 管理。不要使用全局 `pip` 安装项目依赖。

## 初始化

```powershell
uv python install 3.11
uv sync
Copy-Item .env.example .env
```

`.env` 只保存本地配置，已被 Git 忽略。

## 启动后端

```powershell
uv run uvicorn backend.app.main:app --reload
```

启动后可访问：

- 健康检查：<http://127.0.0.1:8000/health>
- OpenAPI 文档：<http://127.0.0.1:8000/docs>

验证健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

预期响应：

```json
{"status":"ok"}
```

## 配置

运行配置来自环境变量或本地 `.env`。可用字段如下：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_NAME` | `SmartShop AI` | 应用显示名称，不能为空 |
| `APP_ENV` | `development` | `development`、`test` 或 `production` |
| `DEBUG` | `false` | 是否开启 FastAPI 调试模式 |
| `LOG_LEVEL` | `INFO` | `DEBUG`、`INFO`、`WARNING`、`ERROR` 或 `CRITICAL` |
| `DATABASE_URL` | - | SQLAlchemy 数据库连接地址 |
| `DATABASE_ECHO` | `false` | 是否输出 SQL 调试日志 |
| `DEEPSEEK_API_KEY` | - | DeepSeek API Key，仅保存在本地 `.env` |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 对话模型 |
| `CHROMA_PATH` | `./data/chroma` | Chroma 持久化目录 |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 中文嵌入模型 |
| `RAG_TOP_K` | `4` | 默认检索数量 |
| `RAG_MIN_SIMILARITY` | `0.5` | 无依据拒答的相似度阈值 |

环境名称和日志级别会自动规范化大小写；非法值会在应用启动前导致配置校验失败。

DeepSeek Key 需要写入本地 `.env`：

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
```

不要提交 `.env`，也不要将 Key 写入源码或 README。

## 数据库迁移

```powershell
uv run alembic upgrade head
```

当前开发环境使用独立 MySQL 8 容器，默认映射到本机 `3308` 端口。迁移通过 `.env` 中的 `DATABASE_URL` 读取连接信息。

查看当前迁移版本：

```powershell
uv run alembic current
```

## 演示数据

首次运行或需要补齐演示数据时执行：

```powershell
uv run python -m sample_data.seed
```

脚本可重复运行，不会重复创建已有账号、商品和订单。

| 账号 | 密码 | 角色 | 说明 |
|---|---|---|---|
| `consumer_demo` | `Demo123!` | consumer | 主演示消费者，拥有 3 条虚构订单 |
| `consumer_other` | `Demo123!` | consumer | 越权测试消费者，拥有 2 条虚构订单 |
| `agent_demo` | `Agent123!` | agent | 后续人工客服阶段使用 |

这些账号和订单仅用于本地演示，不代表真实交易数据。

核心表：

- `users`：消费者与客服账号
- `products`：演示商品
- `orders`：带用户归属的虚构订单
- `chat_sessions`：会话状态与槽位
- `chat_messages`：对话消息
- `handoffs`：人工接管记录
- `documents`：知识文件与索引状态
- `document_chunks`：Chunk 文本、页码、标题和向量 ID 映射

## 登录与订单接口

登录并获取 Bearer Token：

```powershell
$login = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/auth/login `
  -ContentType "application/json" `
  -Body '{"username":"consumer_demo","password":"Demo123!"}'
```

查询本人订单：

```powershell
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Uri http://127.0.0.1:8000/orders/1 -Headers $headers
```

订单查询同时按订单 ID 和认证用户 ID 过滤。其他消费者访问 `consumer_demo` 的订单时返回 `404 order_not_found`，不泄露订单是否存在。Token 具有签名和过期时间，用户被删除或角色变化后，旧 Token 也会失效。

## 知识库与 RAG

首次使用 BGE 模型时会下载约一百多 MB 的权重。当前开发环境已缓存，后续可设置：

```dotenv
EMBEDDING_LOCAL_FILES_ONLY=true
```

导入演示知识文档：

```powershell
uv run python -m scripts.ingest_demo_docs
```

知识文件位于 `data/docs/`，包含退换货政策、质保规则、配送 FAQ、五个商品说明和一份 PDF 售后 FAQ。脚本可重复运行，重复文档会通过 SHA-256 去重。

客服可以使用 `POST /knowledge/upload` 上传 Markdown、TXT 或 PDF，也可以通过 `GET /knowledge/documents` 查看已索引文档。上传与首次模型加载为同步操作，后续阶段再改为 Redis/Celery 异步任务。

RAG 问答需要使用消费者或客服 Bearer Token：

```http
POST /api/v1/rag/ask
```

```json
{
  "question": "降噪耳机保修多久？",
  "product_id": 1,
  "top_k": 4
}
```

响应包含 `answer`、`grounded`、`citations` 和 `model`。没有达到相似度阈值时直接拒答，不调用模型；有证据时 DeepSeek 只依据检索片段回答并标注来源。

## 会话接口

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/chat/sessions` | 创建当前用户的会话 |
| POST | `/chat/sessions/{id}/messages` | 保存用户问题，执行 RAG 并保存 AI 回复 |
| GET | `/chat/sessions/{id}/messages` | 读取本人会话历史 |

会话和消息保存到 MySQL，后端重启后不会丢失。其他消费者读取会话时返回 404。

## 测试与检查

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

统一错误响应结构：

```json
{
  "error": {
    "code": "http_404",
    "message": "Not Found"
  }
}
```

参数校验失败返回 `validation_error`，未处理异常统一返回 `internal_server_error`，且不会把内部异常详情暴露给客户端。

## 当前目录

```text
backend/app/
├── api/             # HTTP 路由与依赖组装
├── core/            # 配置、日志与统一异常处理
├── db/              # SQLAlchemy Engine 与 Session
├── models/          # 用户、订单、会话和知识库模型
├── rag/             # 文档解析、分块、BGE 和 Chroma
├── repositories/    # 数据访问
├── schemas/         # 接口请求与响应模型
├── services/        # 业务服务
└── main.py          # 应用工厂与 FastAPI 入口
data/docs/           # 可提交的演示知识文件
data/chroma/         # 本地向量索引，不提交
scripts/             # 数据导入和 PDF 生成脚本
tests/               # 接口测试
docs/                # 每日复盘
```

请求从 `api` 层进入，经 `services` 层处理，并由 `schemas` 层约束输入输出。Agent Tool Calling、多轮状态机、人工客服前端和异步索引尚未实现。
