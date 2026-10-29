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
