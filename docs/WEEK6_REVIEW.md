# 第六周复盘：观测、测试与知识库运维

> 完成范围：开发手册 V2 的 Day 16～20。当前仍是本地可运行技术原型，不宣称生产级高可用。

## 本阶段交付

| 日期 | 交付 | 验收结果 |
|---|---|---|
| Day 16 | 请求 ID、请求日志、Agent 阶段耗时、输入限制、提示注入防护 | `/health` 返回 200 且带 32 位 `X-Request-ID`；实测请求耗时 8.94 ms |
| Day 17 | 将测试整理为 `unit / integration / e2e` | 最终全量回归 94 项测试全部通过 |
| Day 18 | 架构图、状态机、人工接管时序、6 个源码亮点、面试指南 | `docs/ARCHITECTURE.md`、`docs/INTERVIEW_GUIDE.md` 已建立并补齐 |
| Day 19 | Redis + Celery 异步索引、任务状态、重试与幂等 | 真实任务 `f3ffdc07ad8d4f47a1a73ef3fb595f0f` 成功，进度 100，生成文档 11 |
| Day 20 | MySQL 文档/Chunk 与 Chroma 向量同步删除 | 删除接口返回 204；Chroma 1→0，documents 1→0，document_chunks 1→0，删除后不再召回 |

## 核心设计

### 请求级观测

- 中间件为每个请求生成随机 32 位 ID；
- 响应头返回 `X-Request-ID`，日志过滤器把 ID 注入所有日志；
- 日志只记录方法、路径、状态码、耗时和任务 ID，不记录 Token、密码、API Key 或完整 Prompt；
- Agent 分开记录意图、编排、工具、检索和模型阶段，慢请求可定位到具体阶段。

### 异步索引

- 保留同步 `/knowledge/upload`，新增 `/knowledge/upload-async`，避免破坏已有调用；
- 上传接口只负责保存文件、创建 `ingestion_jobs` 和投递任务；
- MySQL 是任务状态的可信来源，Redis 只作为 Celery broker；
- Worker 首次加载 BGE 模型会产生明显冷启动耗时，不能与后续任务耗时混为一谈；
- 成功任务重复执行时幂等返回，临时数据库错误有限重试，业务错误直接失败。

### 双存储删除

- Chroma 不是业务唯一可信来源，`documents` 与 `document_chunks` 保存在 MySQL；
- 删除时根据 `document_chunks.vector_id` 精确清理向量；
- 向量删除可重复执行，随后再提交数据库删除；
- 当前顺序存在短暂一致性窗口，若数据库提交失败可重试整个删除操作。

## 建议手工验收

1. 启动 Redis、API 和 Celery Worker。
2. 用客服账号登录，调用 `POST /knowledge/upload-async`。
3. 使用返回的 `task_id` 轮询 `GET /knowledge/jobs/{task_id}`，确认状态变为 `success`。
4. 调用 `GET /knowledge/documents` 找到新文档 ID。
5. 调用 `DELETE /knowledge/documents/{document_id}`，确认返回 204。
6. 再次查看文档列表，并检索原文档中的关键词，确认文档和向量均不再返回。
7. 请求任意接口，在响应头确认存在 `X-Request-ID`，再用该 ID 在日志中定位同一次请求。

## 已知限制

- 没有独立的 Celery 队列监控、告警、优先级和死信队列；
- 上传文件保存在本地目录，小规模原型依赖单机 Worker；
- 删除存在“先清向量、后提交 MySQL”的短暂一致性窗口；
- 任务接口按已认证客服开放，当前没有单独的运维角色权限；
- 固定评测通过数不等于生产准确率。
