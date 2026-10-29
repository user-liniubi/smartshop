# Day 10 复盘｜RAG 问答闭环

## 今日知识点

- Query Embedding 与 Top-K 检索
- 商品过滤与全局政策同时召回
- 证据拼装和来源引用
- 模型提示注入防护
- 无证据拒答
- 可注入的 LLM 依赖测试

## 完成代码

- RAG 编排：`backend/app/services/rag.py`
- 请求和响应 Schema：`backend/app/schemas/rag.py`
- 接口：`POST /api/v1/rag/ask`
- 会话 AI 回复：`POST /chat/sessions/{id}/messages`
- 引用写入 `chat_messages.citations_json`

## 实际验收

- 真实 BGE + Chroma 能召回 4 个相关片段
- 无依据问题返回固定拒答，不调用 DeepSeek
- 有依据问题使用 Mock LLM 的接口测试返回回答和文档引用
- 引用包含文档 ID、Chunk ID、文件名、标题、页码或章节与相似度
- 未登录请求返回 401
- 有相关证据但未配置 DeepSeek Key 时返回 503，不编造答案

## 真实模型验收

使用本地配置的 DeepSeek Key 实际调用成功：

```text
问题：降噪耳机保修多久？
回答：降噪耳机质保期为十二个月。[1][2]
来源：warranty_policy.md、headphones_manual.md
HTTP：200
```

通过聊天接口再次询问后，AI 回答“降噪耳机提供 12 个月质保。[1][2]”，4 条引用元数据写入 MySQL。

## 第十天验收

- [ ] 已学习（需本人完成知识复习并确认）
- [x] 已开发
- [x] 已测试
- [x] 已提交 Git
- [x] 真实 DeepSeek 回答
- [x] 检索、引用结构、无依据拒答通过

提交信息：`feat: add persistent chat and RAG knowledge pipeline`  
提交哈希：`f150a03`
