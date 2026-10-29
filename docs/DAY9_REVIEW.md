# Day 9 复盘｜分块与向量入库

## 今日知识点

- 固定长度 Chunk 与 Overlap
- BGE-small-zh-v1.5 中文 Embedding
- Chroma 持久化集合
- MySQL Chunk 元数据与 Chroma `vector_id` 映射
- 文档 SHA-256 去重

## 完成代码

- Chunk：`backend/app/rag/chunking.py`
- BGE：`backend/app/rag/embeddings.py`
- Chroma：`backend/app/rag/vector_store.py`
- 入库服务：`backend/app/services/knowledge.py`
- 批量导入：`scripts/ingest_demo_docs.py`

## 实际验收

演示资料首次导入：

```text
9 documents
26 chunks
512 维向量
```

通过上传接口再导入一份 TXT 后：

```text
MySQL documents=10
MySQL document_chunks=27
Chroma vectors=27
```

MySQL 与 Chroma 数量一致。不同进程重新加载 Chroma 后仍能检索，证明索引已持久化。

## 检索抽样

| 问题 | 最高相似度 | 命中来源 |
|---|---:|---|
| 降噪耳机保修多久？ | 0.7147 | headphones_manual.md |
| 支持七天无理由退货吗？ | 0.7578 | return_policy.md |
| 笔记本能自己加内存吗？ | 0.6077 | laptop_manual.md |
| 今天天气怎么样？ | 0.3680 | 无关内容 |
| 火星有库存吗？ | 0.4097 | 无关内容 |

根据实测把最低相关度阈值设为 `0.5`，避免无关问题进入模型。

## 第九天验收

- [ ] 已学习（需本人完成知识复习并确认）
- [x] 已开发
- [x] 已测试
- [ ] 已提交 Git（首次提交后更新）
- [x] 工程验收通过
