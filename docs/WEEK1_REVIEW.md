# 第一周验收｜FastAPI + MySQL + 模拟业务数据

## 周目标

完成 FastAPI 后端、MySQL 数据库连接与迁移、核心数据表、演示账号与虚构订单，以及对象级订单权限。

## 交付结果

| 开发日 | 交付 | 验收 |
|---|---|---|
| Day 1 | Python 3.11、uv、FastAPI、`/health`、Git | 通过 |
| Day 2 | 配置、日志、统一异常、API/Service/Schema 分层 | 通过 |
| Day 3 | SQLAlchemy 2、MySQL 连接、Alembic 初始迁移 | 通过 |
| Day 4 | 六张核心表、5 条虚构订单、演示账号 | 通过 |
| Day 5 | 登录、Bearer Token、本人订单查询、越权测试 | 通过 |

## 数据库验收

```text
MySQL 8.0.40
当前迁移：6dcf03460220 (head)
users=3
products=5
orders=5
外键约束=6
```

核心表：

- `users`
- `products`
- `orders`
- `chat_sessions`
- `chat_messages`
- `handoffs`

## 接口验收

| 接口 | 正常结果 | 异常结果 |
|---|---|---|
| `GET /health` | `200 {"status":"ok"}` | 错误方法返回统一 405 |
| `POST /auth/login` | 正确账号返回 Bearer Token | 错误密码返回 401 |
| `GET /orders/{id}` | 本人订单返回 200 和商品信息 | 他人订单返回 404 |
| `GET /docs` | Swagger UI 正常 | - |

## 自动化验收

```text
21 passed, 1 warning
All Ruff checks passed
55 files already formatted
uv lock --check passed
Alembic model check passed: No new upgrade operations detected
```

唯一警告是 FastAPI 当前测试客户端对 `httpx` 的弃用提示，不影响接口、认证或数据库功能。

## 本周遗留与边界

- “已学习”需要开发者本人复习后确认，代码测试通过不代替代学习验收。
- 登录 Token 为演示阶段实现；刷新 Token、撤销列表和生产密钥轮换留待后续安全增强。
- 当前 MySQL 运行在独立 Docker 容器 `smartshop-mysql-dev`，映射端口为 `3308`，不改变本机已有 3306 实例。
- 下一周进入会话持久化与 RAG 基础，不提前实现 AI 功能。

## 周验收结论

第一周“FastAPI + MySQL + 模拟业务数据”目标已达到，可以进入 Day 6。工程自动测试、真实 MySQL 查询和越权保护均已实际验证。
