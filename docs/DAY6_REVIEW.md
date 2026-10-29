# Day 6 复盘｜会话持久化

## 今日知识点

- REST 会话与消息资源设计
- 请求级 SQLAlchemy Session
- 会话归属校验
- 消费者、AI 与客服消息发送方区分
- JSON 字段保存引用元数据

## 完成代码

- `POST /chat/sessions`
- `POST /chat/sessions/{id}/messages`
- `GET /chat/sessions/{id}/messages`
- 会话 Repository：`backend/app/repositories/chat.py`
- 会话 Service：`backend/app/services/chat.py`
- 消息 Schema：`backend/app/schemas/chat.py`

## 实际验收

- 创建会话后返回 MySQL 会话 ID
- 无依据问题成功保存消费者消息和 AI 兜底回复
- 停止并重启 Uvicorn 后，重新登录仍能读取同一会话的 3 条历史消息
- 其他消费者访问该会话返回 404
- 会话状态和消息均来自 MySQL，不使用进程内存保存

## 设计取舍

每条用户消息先独立提交，再执行耗时的向量检索和模型调用。即使模型暂时不可用，用户已发送的问题仍会保留，不会因为后续 AI 失败而丢失。

## 第六天验收

- [ ] 已学习（需本人完成知识复习并确认）
- [x] 已开发
- [x] 已测试
- [x] 已提交 Git
- [x] 工程验收通过

提交信息：`feat: add persistent chat and RAG knowledge pipeline`  
提交哈希：`f150a03`
