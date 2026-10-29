# Day 7 复盘｜DeepSeek 接入

## 今日知识点

- DeepSeek 使用 OpenAI 兼容 Chat Completions 协议
- 使用 `AsyncOpenAI` 进行异步模型调用
- 请求超时、有限重试和错误分类
- Pydantic `SecretStr` 保护 API Key
- 记录模型调用耗时

## 完成代码

- DeepSeek 客户端：`backend/app/services/llm.py`
- 配置字段：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`
- 超时：默认 30 秒，重试次数固定为 0
- 错误码：`model_not_configured`、`model_unavailable`、`model_empty_response`
- 自动化测试使用 Mock `AsyncOpenAI` 验证请求模型、证据 Prompt、响应解析和错误映射

## 实际验收

本地目前没有配置 DeepSeek API Key。真实请求已完成 BGE 检索并进入模型调用边界，随后按设计返回：

```json
{
  "error": {
    "code": "model_not_configured",
    "message": "DeepSeek 服务尚未配置"
  }
}
```

这证明后端没有伪造模型回答。真实 DeepSeek 回答需要在本地 `.env` 配置 `DEEPSEEK_API_KEY` 后重启服务再验收。

当前自动化测试共 37 项通过，其中包含 DeepSeek 兼容客户端请求构造和失败映射测试。

## 设计取舍

模型 Key 不进入代码或日志。只有检索结果达到阈值后才调用模型，减少无依据请求和无效成本。

## 第七天验收

- [ ] 已学习（需本人完成知识复习并确认）
- [x] 已开发
- [x] 已测试
- [ ] 已提交 Git（首次提交后更新）
- [ ] 真实 DeepSeek 调用（缺少本地 API Key）
