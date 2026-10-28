# Day 1 复盘｜项目初始化

## 今日知识点

- **Python 虚拟环境**：项目依赖安装到 `.venv`，避免污染全局 Python。
- **依赖锁定**：`pyproject.toml` 声明直接依赖，`uv.lock` 固定完整依赖图。
- **HTTP 基础**：健康检查使用 `GET /health`，成功返回 `200`；不存在的路由返回 `404`；不支持的方法返回 `405`。
- **FastAPI**：通过应用入口暴露路由，并自动生成 Swagger 页面 `/docs`。
- **Git**：只提交源码、配置模板和文档；`.env`、`.venv`、日志及本地数据不提交。

## 完成代码与接口

- 项目运行版本：Python `3.11.16`
- 依赖管理：`uv 0.12.13`
- 应用入口：`backend/app/main.py`
- 健康检查：`GET /health`
- 接口文档：`GET /docs`
- 环境配置：`backend/app/core/config.py`
- 基础日志：`backend/app/core/logging.py`
- 统一错误响应：`backend/app/core/exceptions.py`

## 正常路径测试

实际启动 Uvicorn 后验证：

| 请求 | 结果 |
|---|---|
| `GET /health` | `200`，响应 `{"status":"ok"}` |
| `GET /docs` | `200`，页面包含 Swagger UI |

## 异常与边界路径测试

| 请求 | 结果 |
|---|---|
| `GET /not-found` | `404`，返回统一 `error` JSON |
| `POST /health` | `405`，返回统一 `error` JSON |

自动化测试结果：

```text
3 passed, 1 warning in 0.16s
```

Ruff 结果：

```text
All checks passed!
14 files already formatted
```

测试中的唯一警告来自 FastAPI 测试客户端对 `httpx` 的弃用提示，不影响当前接口结果。后续升级依赖时再统一处理。

## 遇到的问题与解决

1. 系统默认 `python` 为 3.10.18，但手册要求 3.11。通过 `uv sync --python 3.11` 创建独立 `.venv`，确认项目运行时为 3.11.16。
2. 首次运行 pytest 时测试进程未自动识别项目根包。为 pytest 配置 `pythonpath = ["."]` 后，3 条测试全部通过。

## 设计取舍

- `/health` 不访问外部服务，保持轻量，用于确认应用进程和路由已启动。
- 错误响应统一为 `{"error":{"code":"...","message":"..."}}`，后续接口可以沿用相同错误格式。
- 日志在应用启动时统一配置，并使用 `.env` 中的 `LOG_LEVEL` 控制级别。
- 当前只建立后续阶段需要的基础目录，不提前实现商品、数据库、RAG 或 Agent。

## Git 提交

提交信息：`feat: initialize SmartShop AI backend`

## 第一天验收

- [ ] 已学习（需本人完成知识复习并确认）
- [x] 已开发
- [x] 已测试
- [ ] 已提交 Git（首次提交后更新）
- [x] 工程验收通过
