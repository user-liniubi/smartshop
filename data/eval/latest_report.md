# SmartShop Agent 固定评测报告

## 指标

| 指标 | 结果 |
|---|---:|
| case_count | 31 |
| intent_accuracy | 1.0 |
| order_no_extraction_accuracy | 1.0 |
| action_accuracy | 1.0 |
| tool_behavior_accuracy | 1.0 |
| rag_hit_at_3 | 1.0 |
| rag_hit_at_5 | 1.0 |
| no_evidence_refusal_rate | 1.0 |
| task_success_rate | 1.0 |
| p50_latency_ms | 874.7 |
| p95_latency_ms | 1943.45 |

## 分类结果

| 分类 | 成功 / 总数 |
|---|---:|
| exchange | 1 / 1 |
| missing_info | 4 / 4 |
| order_fact | 3 / 3 |
| policy | 8 / 8 |
| prompt_injection | 3 / 3 |
| return | 1 / 1 |
| similar_product | 4 / 4 |
| unauthorized | 2 / 2 |
| unrelated | 4 / 4 |
| warranty | 1 / 1 |

## 口径

- 意图和订单号使用 DeepSeek 结构化输出实测。
- 工具指标验证订单归属和未知工具拦截，不执行任意 SQL。
- RAG Hit@K 以人工标注的 gold files 是否进入前 K 条来源计算。
- 任务成功率要求意图、订单号、工作流动作、工具行为以及适用的 RAG/拒答均正确。
- 该报告不包含最终回答人工正确率或引用支持度抽检。
