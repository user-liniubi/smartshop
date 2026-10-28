# Day 3 复盘｜MySQL 数据库接入

## 今日知识点

- **SQLAlchemy Engine**：Engine 管理数据库连接池，应用不在每个请求中重复创建连接。
- **Session**：每个 HTTP 请求使用独立 Session，请求结束后自动关闭。
- **声明式模型**：模型继承 `DeclarativeBase`，后续通过统一 metadata 生成迁移。
- **Alembic**：迁移文件记录数据库结构版本，`alembic_version` 保存当前生效版本。
- **无密码泄漏配置**：连接地址由 `.env` 提供，`.env.example` 只保留占位符。

## 完成代码

- SQLAlchemy Engine 与 Session 工厂：`backend/app/db/session.py`
- 声明式 Base 与约束命名规则：`backend/app/db/base.py`
- Alembic 配置与运行环境：`alembic.ini`、`migrations/env.py`
- 初始迁移：`migrations/versions/0001_initialize_database.py`
- 配置新增 `DATABASE_URL`、`DATABASE_ECHO`

## 实际验收结果

开发数据库使用独立 MySQL 8 容器，不影响本机原有 3306 实例：

```text
MySQL 8.0.40
应用账号：smartshop@%
数据库：smartshop
容器端口：127.0.0.1:3308
```

执行迁移：

```text
uv run alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade -> 0001
```

迁移状态：

```text
0001 (head)
```

MySQL 中已生成 Alembic 版本表，当前版本值为 `0001`。SQLAlchemy 独立连接测试使用内存 SQLite，保证测试不依赖外部服务。

自动化检查结果：

```text
11 passed, 1 warning in 1.25s
All checks passed!
34 files already formatted
```

测试警告仍为 FastAPI 测试客户端对 `httpx` 的弃用提示，不影响数据库与接口结果。

## 设计取舍

- 开发和测试共享 SQLAlchemy 模型，但自动化单元测试使用内存 SQLite，真实 MySQL 验收通过 Alembic 和手工接口联调完成。
- 数据库连接池启用 `pool_pre_ping`，降低 MySQL 空闲连接失效造成的偶发错误。
- 初始迁移只建立迁移基线，核心业务表在 Day 4 通过下一条迁移创建，保持日计划边界清晰。

## 第三天验收

- [ ] 已学习（需本人完成知识复习并确认）
- [x] 已开发
- [x] 已测试
- [x] 已提交 Git
- [x] 工程验收通过

提交信息：`feat: connect MySQL and initialize Alembic`  
提交哈希：`11f256b`
