# SmartShop AI

SmartShop AI 是一个面向 AI 应用开发求职的智能电商项目。当前完成第一阶段 Day 1 / P0：可运行的 FastAPI 后端骨架、环境配置、基础日志、统一错误响应和健康检查测试。

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

## 测试与检查

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

异常路径可手动访问不存在的接口，例如 <http://127.0.0.1:8000/not-found>。服务会返回统一结构的 `404` JSON。

## 当前目录

```text
backend/app/
├── core/            # 配置、日志与统一异常处理
├── schemas/         # 接口响应模型
└── main.py          # FastAPI 入口
tests/               # 接口测试
docs/                # 每日复盘
```

商品、数据库、RAG、Agent 与前端将在后续开发日按手册逐步实现。
