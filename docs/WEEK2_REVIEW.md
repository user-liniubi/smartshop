# 第二周验收｜会话持久化与 RAG 基础

## 周目标

让用户能够创建会话、保存消息，并通过退换货政策和商品资料回答问题。

## 交付结果

| 开发日 | 交付 | 验收 |
|---|---|---|
| Day 6 | 会话创建、消息保存、历史读取 | 重启后持久化通过 |
| Day 7 | DeepSeek 客户端、超时与错误分类 | 真实调用通过 |
| Day 8 | Markdown/TXT/PDF 解析与客服上传 | 通过 |
| Day 9 | BGE Chunk、Embedding、Chroma 持久化 | 27 个向量通过 |
| Day 10 | Top-K、来源引用、无依据拒答 | 检索、真实回答与引用通过 |

## 数据库与索引

```text
迁移版本：115c7df357d1 (head)
documents=10
document_chunks=27
Chroma vectors=27
```

知识资料为虚构售后政策、FAQ 和商品说明，不包含真实品牌价格或客户数据。

## 接口

| 接口 | 用途 |
|---|---|
| `POST /chat/sessions` | 创建本人会话 |
| `POST /chat/sessions/{id}/messages` | 保存问题并生成 RAG 回复 |
| `GET /chat/sessions/{id}/messages` | 读取会话历史 |
| `POST /knowledge/upload` | 客服上传并同步索引知识 |
| `GET /knowledge/documents` | 客服查看文档状态 |
| `POST /api/v1/rag/ask` | 有来源引用的知识问答 |

## 当前边界

- DeepSeek API Key 只保存在本地 `.env`，没有进入 Git。
- 文档索引为同步操作，Redis + Celery 属于后续阶段。
- 未运行商品详情前端；当前通过 Swagger 使用接口。
- BGE 首次加载在 CPU 上约 14～20 秒，后续查询复用已加载模型。
- 引用返回检索到的 Top-K 来源，模型是否严格采用每个来源需要在配置 Key 后人工抽查。
- 自动测试已验证 DeepSeek 兼容客户端请求结构，但不能代替真实网络与账号鉴权验收。

## 周验收结论

第二周闭环已经完成：知识文档可解析、分块、向量化、持久检索，会话消息可保存，无关问题可拒答，DeepSeek 能基于真实检索证据生成回答并返回来源引用。最终自动测试为 `37 passed`。

真实问答“降噪耳机保修多久？”返回十二个月质保，并引用 `warranty_policy.md` 与 `headphones_manual.md`。第二周验收通过。

## 按日执行记录

### Day 6｜会话持久化

**完成什么**

- 实现创建会话、发送消息和读取历史接口；
- 会话、消息和引用元数据保存到 MySQL；
- 消费者只能访问自己的会话；
- 区分消费者、AI、客服和系统消息发送方。

**实际实现**

- 路由：`backend/app/api/routes/chat.py`；
- 服务：`backend/app/services/chat.py`；
- Repository：`backend/app/repositories/chat.py`；
- 消息引用保存到 `citations_json`。

**使用技术**

- FastAPI REST、SQLAlchemy Session、JSON 字段、对象级会话授权。

**问题与解决**

- 模型调用失败可能造成用户消息丢失。先独立提交用户消息，再执行检索和模型调用。
- 其他消费者可能通过猜测会话 ID 读取记录。查询 SQL 同时匹配会话 ID 和当前用户 ID。

**验收**

- 重启 Uvicorn 后仍能读取同一会话历史；
- 他人会话返回 404；
- 用户消息、AI 消息和引用均持久化。

### Day 7｜DeepSeek 接入

**完成什么**

- 封装 DeepSeek Chat 客户端；
- 配置 API Key、Base URL、模型和超时；
- 实现 API 错误、空响应和未配置错误分类；
- 记录真实模型调用耗时。

**实际实现**

- 使用 OpenAI 兼容 SDK `AsyncOpenAI`；
- 模型 Key 使用 `SecretStr`，不写入代码和日志；
- 当前不自动重试，避免重复生成和额外成本；
- 超时映射为稳定的 `model_unavailable`。

**使用技术**

- DeepSeek Chat API、OpenAI 兼容 SDK、async/await、pytest Mock。

**问题与解决**

- 模型 Key 不能出现在源码和日志中。通过环境变量注入，并在日志中只记录模型名和耗时。
- 首次调用耗时包含 BGE 冷加载，不能当成 DeepSeek 单次延迟。分别记录阶段耗时。

**验收**

- 真实 DeepSeek 请求返回 200；
- Key 未配置和 API 异常均有稳定错误码；
- 客户端请求结构和响应解析有自动化测试。

### Day 8｜售后知识文档

**完成什么**

- 准备退换货、质保、配送、五个商品说明和 PDF 售后 FAQ；
- 支持 Markdown、TXT、PDF 解析；
- 保留文件名、标题、页码和章节元数据；
- 客服上传与文档列表接口完成。

**实际实现**

- 解析器：`backend/app/rag/parsing.py`；
- PDF 使用 PyMuPDF 提取文本和页码；
- 上传接口同时校验角色、扩展名、文件大小和空文本；
- 文件元数据写入 MySQL。

**使用技术**

- Python 标准库、PyMuPDF、FastAPI UploadFile、SHA-256。

**问题与解决**

- PDF 可能没有可提取文字。扫描版 PDF 明确提示暂不支持 OCR。
- 消费者可能调用客服上传接口。通过客服角色依赖返回 403。

**验收**

- Markdown、TXT 和 PDF 均能解析；
- 空文件、不支持的扩展名和扫描 PDF 有明确错误；
- 消费者上传被拒绝。

### Day 9｜分块、Embedding 与 Chroma

**完成什么**

- 实现固定长度和 overlap 分块；
- 使用 BGE-small-zh-v1.5 生成 512 维中文向量；
- 向量写入本地持久化 Chroma；
- MySQL Chunk 元数据与 Chroma `vector_id` 建立映射；
- 文档通过 SHA-256 去重。

**实际实现**

- `backend/app/rag/chunking.py` 负责文本切分；
- `backend/app/rag/embeddings.py` 封装 BGE；
- `backend/app/rag/vector_store.py` 封装 Chroma；
- 演示文档最终形成 10 份文档、27 个 Chunk 和 27 个向量。

**使用技术**

- BGE-small-zh-v1.5、sentence-transformers、Chroma、SHA-256。

**问题与解决**

- 首次加载 BGE 在 CPU 上较慢。后续查询复用进程内模型，并允许本地缓存模式。
- 文档重复上传会生成重复向量。使用文件哈希和 Chunk 哈希去重。

**验收**

- MySQL 与 Chroma 数量一致；
- 进程重新加载后索引仍可检索；
- 耳机、退货、内存等查询能命中正确文档。

### Day 10｜RAG 问答闭环

**完成什么**

- 实现问题向量化、Top-K 检索和相似度阈值；
- 拼接检索证据并调用 DeepSeek；
- 返回文档、页码或章节、片段和相似度；
- 无依据时直接拒答，不调用模型；
- 增加提示注入防护。

**实际实现**

- RAG 编排：`backend/app/services/rag.py`；
- 接口：`POST /api/v1/rag/ask`；
- 聊天接口复用 RAG 并发保存 AI 引用；
- 文档内容作为不可信 evidence，不作为系统指令。

**使用技术**

- RAG、Embedding、Top-K、Prompt 约束、来源引用、拒答策略。

**问题与解决**

- 无关问题可能被低相似度片段强行回答。根据抽样测试将最低相关度设为 0.5。
- 有引用不等于模型一定正确采用引用。明确引用是检索来源，仍需通过固定评测和人工抽查验证支持关系。

**验收**

- 真实问题“降噪耳机保修多久”返回十二个月质保；
- 引用 `warranty_policy.md` 和 `headphones_manual.md`；
- 无关问题不调用 DeepSeek；
- 全部自动测试最终为 `37 passed`。
