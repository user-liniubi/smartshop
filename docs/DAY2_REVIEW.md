# Day 2 复盘｜配置与后端分层

## 今日知识点

- **Pydantic Settings**：从环境变量和 `.env` 读取配置，并在应用启动前校验类型与合法值。
- **后端分层**：API 层负责协议入口和依赖组装，Service 层承载业务逻辑，Schema 层约束接口数据，Model/Repository 层预留给数据库阶段。
- **应用工厂**：通过 `create_app(settings)` 创建可替换配置的 FastAPI 实例，降低测试与后续部署耦合。
- **统一异常**：HTTP 错误、参数校验错误、可预期业务错误和未知错误都使用一致 JSON 外壳。
- **基础日志**：启动与关闭时记录应用名称和运行环境，日志级别来自配置。

## 完成代码与接口

- `/health` 从 `backend/app/main.py` 拆分到 `api/routes/health.py`
- 健康检查业务逻辑位于 `services/health.py`
- `create_app()` 应用工厂位于 `backend/app/main.py`
- 配置校验位于 `backend/app/core/config.py`
- 业务异常 `AppError` 与统一处理器位于 `backend/app/core/exceptions.py`
- 通用错误响应模型位于 `backend/app/schemas/common.py`
- 已建立 `api`、`models`、`repositories`、`schemas`、`services` 分层目录
- 本地 `.env` 已按 `.env.example` 创建，且不会进入 Git

## 测试范围

- 正常路径：配置从环境变量读取并完成大小写规范化；`GET /health` 返回 200。
- 异常路径：非法环境、非法日志级别、空应用名被拒绝。
- 参数错误：缺失必需查询参数时返回结构化 422。
- 业务错误：`AppError` 保留指定状态码与错误码。
- 未知错误：返回通用 500，不泄露内部异常文本。
- 接口边界：不存在的路由返回结构化 404，不支持的方法返回 405。

## 实际验收结果

```text
10 passed, 1 warning in 0.13s
All checks passed!
27 files already formatted
```

实际启动 Uvicorn 后验证：

| 请求 | 结果 |
|---|---|
| `GET /health` | `200`，响应 `{"status":"ok"}` |
| `GET /docs` | `200`，Swagger UI 正常加载 |
| `GET /openapi.json` | `200`，标题为 `SmartShop AI`，版本为 `0.2.0` |
| `GET /not-found` | `404`，返回统一 `error` JSON |

启动日志：

```text
INFO | backend.app.main | Starting SmartShop AI in development mode
```

唯一测试警告来自 FastAPI 测试客户端对 `httpx` 的弃用提示，不影响当前功能和接口结果。

## 遇到的问题与解决

1. Day 1 的配置字段只做类型声明，非法环境名和日志级别可能进入运行期。Day 2 改为 Literal 与字段校验器，并在测试中覆盖非法值。
2. Day 1 的健康检查直接写在入口文件。Day 2 改为路由、服务、响应 Schema 分层，后续接口可沿用相同结构。

## 设计取舍

- 健康检查不依赖数据库等外部资源，保证后续数据库异常时仍能区分“应用进程可用”和“业务依赖不可用”。
- 未处理异常只记录服务端日志，客户端只收到通用信息，避免泄露堆栈和内部实现。
- `models` 与 `repositories` 当前只建立包结构，不提前引入 SQLAlchemy 或数据库配置，边界留给 Day 3。

## 第二天验收

- [ ] 已学习（需本人完成知识复习并确认）
- [x] 已开发
- [x] 已测试
- [x] 已提交 Git
- [x] 工程验收通过

提交信息：`feat: add config validation and backend layers`  
提交哈希：`da1cda9`
