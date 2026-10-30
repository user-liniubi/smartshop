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

## 按日执行记录

### Day 1｜项目初始化

**完成什么**

- 确认 Python `3.11.16` 和 uv 环境；
- 创建 FastAPI 应用与 `GET /health`；
- 开放 Swagger `GET /docs`；
- 初始化 Git，并忽略 `.env`、`.venv`、日志和本地数据；
- 建立 pytest 与 Ruff 基础检查。

**实际实现**

- 应用入口：`backend/app/main.py`；
- 配置：`backend/app/core/config.py`；
- 日志：`backend/app/core/logging.py`；
- 统一异常：`backend/app/core/exceptions.py`；
- 健康检查正常返回 `200 {"status":"ok"}`；未知路由和不支持的方法返回结构化 404/405。

**使用技术**

- Python 3.11、uv、FastAPI、Uvicorn、pytest、Ruff、Git。

**问题与解决**

- 本机默认 Python 是 3.10，不符合手册要求。使用 uv 创建 Python 3.11 独立环境。
- pytest 首次无法识别项目根包。在 pytest 配置中加入 `pythonpath = ["."]`。

**验收**

- `3 passed`；
- Ruff 通过；
- 实际启动 Uvicorn 后 `/health` 和 `/docs` 均正常。

### Day 2｜配置与后端分层

**完成什么**

- 建立配置、日志、异常、API、Service、Schema、Model、Repository 分层；
- 新增 `create_app()` 应用工厂；
- 配置统一错误响应；
- 完成配置合法值校验。

**实际实现**

- Pydantic Settings 从环境变量和 `.env` 读取配置；
- 环境名和日志级别自动规范化；
- HTTP 错误、参数错误、业务错误和未知错误使用统一 JSON 外壳；
- 健康检查拆成 Route、Service 和 Schema。

**使用技术**

- Pydantic Settings、FastAPI 依赖注入与 lifespan、Python logging、pytest。

**问题与解决**

- 第一天的配置只声明类型，非法环境可能进入运行期。增加 Literal 和字段校验器。
- 健康检查原先写在入口中。拆分到独立路由和服务，后续接口沿用相同结构。

**验收**

- `10 passed`；
- 非法环境、非法日志级别和空应用名均有测试；
- 未知错误返回统一 500，不泄露内部异常。

### Day 3｜MySQL 数据库接入

**完成什么**

- 建立 SQLAlchemy 2 Engine、Session 工厂和声明式 Base；
- 连接独立 MySQL 8 容器；
- 初始化 Alembic，并创建 `0001` 迁移基线。

**实际实现**

- `backend/app/db/session.py` 管理 Engine 和请求级 Session；
- 命名约定集中在 `backend/app/db/base.py`；
- Alembic 从项目 Settings 读取数据库地址；
- 非 SQLite 连接启用 `pool_pre_ping`。

**使用技术**

- SQLAlchemy 2、MySQL 8、PyMySQL、Alembic、Docker。

**问题与解决**

- 本机已有 3306 MySQL 实例。项目使用独立容器并映射到 3308，避免影响已有环境。
- 自动化测试使用内存 SQLite，真实 MySQL 通过迁移和手工联调验收。

**验收**

- `11 passed`；
- 初始迁移成功执行；
- MySQL 中生成 `alembic_version`。

### Day 4｜核心数据表与演示数据

**完成什么**

- 创建 `users`、`products`、`orders`、`chat_sessions`、`chat_messages`、`handoffs`；
- 配置主外键、唯一约束、CHECK 约束和复合索引；
- 写入 3 个演示账号、5 个商品和 5 条虚构订单；
- 实现 scrypt 密码哈希和幂等种子脚本。

**实际实现**

- SQLAlchemy 关系模型位于 `backend/app/models/entities.py`；
- 订单按 `user_id + created_at` 建立复合索引；
- 订单号、用户名和商品名有唯一约束；
- 种子脚本先查询再插入，可重复执行；
- 密码只保存随机盐 scrypt 哈希。

**使用技术**

- SQLAlchemy Mapped、Alembic、MySQL JSON/CHECK 约束、scrypt。

**问题与解决**

- 需要兼容真实 MySQL 和测试 SQLite。状态使用字符串列并在模型与数据库层增加 CHECK 约束。
- 种子脚本重复执行可能插入重复数据。通过用户名、商品名和订单号做存在性检查。

**验收**

- `13 passed`；
- 数据库数量为 users=3、products=5、orders=5；
- 二次执行种子脚本不增加重复记录。

### Day 5｜登录与订单权限

**完成什么**

- 实现 `POST /auth/login`；
- 签发带过期时间的 HMAC 签名 Token；
- 实现 `GET /orders/{order_id}`；
- 查询订单时同时校验订单 ID 和当前用户 ID；
- 访问他人订单统一返回 404。

**实际实现**

- 当前用户依赖位于 `backend/app/api/dependencies.py`；
- Token 签名和 scrypt 密码校验位于 `backend/app/core/security.py`；
- 订单 Repository 把 `user_id` 放入 SQL 条件，不在查询后做权限判断；
- 登录不存在用户时也执行一次密码校验，降低时序侧信道风险。

**使用技术**

- FastAPI HTTPBearer、HMAC-SHA256、scrypt、依赖注入、pytest 依赖覆盖。

**问题与解决**

- 登录测试最初使用空数据库夹具，导致正常账号也返回 401。改为演示数据夹具后通过。
- 越权返回 403 会暴露订单存在性。统一返回 404，避免订单枚举。

**验收**

- `21 passed`；
- 正确账号登录、本人订单查询、错误密码、无效 Token、过期 Token 和越权测试通过；
- 真实 MySQL 联调通过。
