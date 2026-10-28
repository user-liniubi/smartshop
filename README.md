# SmartShop AI

SmartShop AI 是一个面向 AI 应用开发求职的智能电商项目。当前完成第一阶段 Day 2：可运行的 FastAPI 后端骨架、分层目录、环境配置、基础日志、统一错误响应和接口测试。

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

环境名称和日志级别会自动规范化大小写；非法值会在应用启动前导致配置校验失败。

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
├── models/          # 后续阶段的数据模型
├── repositories/    # 后续阶段的数据访问
├── schemas/         # 接口请求与响应模型
├── services/        # 业务服务
└── main.py          # 应用工厂与 FastAPI 入口
tests/               # 接口测试
docs/                # 每日复盘
```

请求从 `api` 层进入，经 `services` 层处理，并由 `schemas` 层约束输入输出。数据库模型和仓储将在 Day 3 之后接入；RAG、Agent 与前端仍按手册逐步实现。
