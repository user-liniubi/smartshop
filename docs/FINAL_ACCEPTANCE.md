# SmartShop AI 最终验收报告

| 项目 | 内容 |
|---|---|
| 验收日期 | 2026-11-06 |
| 项目定位 | 单商家售后智能客服本地技术原型 |
| 发布版本 | `v1.0.0` |
| 代码基线 | `e8eff02` 加最终验收文档与版本号变更 |

## 验收结论

售后主闭环、消费者端、客服工作台、固定评测、请求级观测、异步文档索引和双存储删除均已实际运行通过。当前版本可以作为个人项目演示和面试材料交付。

本报告只记录实际执行结果，不将本地固定场景结果解释为生产环境准确率。

## 自动化检查

| 检查项 | 命令 | 实际结果 |
|---|---|---|
| 全量测试 | `uv run pytest -q` | `94 passed in 44.30s` |
| 静态检查 | `uv run ruff check .` | `All checks passed!` |
| 格式检查 | `uv run ruff format --check .` | `139 files already formatted` |
| 锁文件 | `uv lock --check` | 通过 |
| 迁移版本 | `uv run alembic current` | `0eebbeffd084 (head)` |
| 模型迁移差异 | `uv run alembic check` | `No new upgrade operations detected` |

## 固定评测

执行命令：

```powershell
uv run python -m scripts.run_eval
```

| 指标 | 本次结果 |
|---|---:|
| 场景数 | 31 |
| 意图准确率 | 1.0 |
| 订单号提取准确率 | 1.0 |
| 工作流动作准确率 | 1.0 |
| 工具行为准确率 | 1.0 |
| RAG Hit@3 | 1.0 |
| RAG Hit@5 | 1.0 |
| 无依据拒答率 | 1.0 |
| 任务成功率 | 1.0 |
| P50 延迟 | 874.70 ms |
| P95 延迟 | 1943.45 ms |

评测期间出现过非法意图结构化输出，系统按设计降级后仍完成全部场景。31 条样本是自建固定场景，不能代表开放用户和生产流量上的泛化准确率。

## 真实售后闭环

通过运行中的 FastAPI、真实 MySQL 和 DeepSeek 完成：

```text
消费者创建会话
→ “耳机坏了，想退货”：ask_more_info / collecting_info
→ “订单号 A10086”：ask_more_info / collecting_info
→ “左耳没有声音”：answer / resolved
→ 申请人工：pending
→ 客服接管：claimed
→ 人工回复：claimed
→ 消费者读取到 sender_type=agent
→ 客服关闭：closed，closed_at 已写入
```

验收会话 ID：`12`。

## 服务与页面

| 项目 | 地址或检查 | 结果 |
|---|---|---|
| 健康检查 | `GET /health` | 200，返回 `X-Request-ID=01a279e9224041e3b3e7d568a71b0b3f` |
| Swagger | <http://127.0.0.1:8000/docs> | 200 |
| 消费者端 | <http://127.0.0.1:8501> | 200 |
| 客服工作台 | <http://127.0.0.1:8502> | 200 |
| Celery | `celery inspect ping` | 1 node online / pong |
| Redis | `redis-cli ping` | PONG |

## 异步索引与删除

真实异步任务结果：

```text
task_id: 41bc5ac173d5419dba4e0e503874a84d
initial_status: pending
final_status: success
progress: 100
document_id: 12
```

随后调用 `DELETE /knowledge/documents/12`：

- HTTP 状态：204；
- MySQL 文档列表：已移除；
- Chroma 剩余向量：0。

该验收同时验证了 Redis -> Celery -> MySQL `ingestion_jobs`、BGE 向量写入和双存储删除链路。

## 手工复验

1. 按 [DEMO.md](DEMO.md) 启动 MySQL、Redis、API、Worker 和双端页面。
2. 使用演示账号完成三轮售后、转人工、客服接管、回复和关闭。
3. 请求 `/health`，在响应头确认 `X-Request-ID`。
4. 通过客服账号上传一份临时知识文件并轮询任务状态。
5. 删除该文档，确认接口返回 204，并检查列表和向量均无残留。

## 当前边界

- 项目是单商家、售后阶段的技术原型，不包含购物车、下单、支付、物流或多商家经营。
- 31 条固定评测结果不能等同于生产准确率。
- 尚未完成最终回答正确率和引用支持度的人工抽检。
- 没有生产级队列监控、告警、高可用和容量验证。
- 消费者端和客服端使用 Streamlit，不是 React/Vue 商业前端。
