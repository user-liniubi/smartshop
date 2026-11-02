# SmartShop AI 演示脚本

建议总时长 3～5 分钟。

## 演示前启动

```powershell
docker start smartshop-mysql-dev
uv run alembic upgrade head
uv run uvicorn backend.app.main:app --reload
uv run streamlit run frontend/consumer_app.py --server.port 8501
uv run streamlit run frontend/agent_app.py --server.port 8502
```

## 1. 介绍项目｜30 秒

> 这是一个单商家售后智能客服项目。系统从消费者已有订单后的售后问题开始，使用 DeepSeek 识别意图和选择工具，通过 MySQL 查询本人订单，再用 BGE 和 Chroma 检索退换货与商品资料，最终生成带来源的建议。异常时转人工，客服可接管、回复和关闭。

## 2. 消费者三轮售后｜90 秒

打开 <http://127.0.0.1:8501>，使用：

```text
consumer_demo / Demo123!
```

新建会话并依次输入：

```text
耳机坏了，想退货
订单号 A10086
左耳没有声音
```

展示：

- 第一轮同时追问订单号和具体故障；
- 第二轮只追问故障；
- 第三轮展示订单状态、商品和政策来源；
- 系统不承诺真实退款已完成。

## 3. 申请人工｜20 秒

点击“申请人工客服”，展示：

```text
status=need_human
action=waiting_for_agent
```

## 4. 客服接管与回复｜60 秒

打开 <http://127.0.0.1:8502>，使用：

```text
agent_demo / Agent123!
```

进入“待接管”，选择刚才的任务并点击“接管会话”。

展示：

- 会话历史；
- 工作流状态；
- 订单摘要；
- 转人工来源和原因。

发送：

```text
人工客服已收到，正在核实订单与售后方案。
```

## 5. 消费者查看人工消息｜20 秒

回到消费者端，切换或刷新会话：

- 页面显示“当前由人工客服处理”；
- 历史消息中可以看到人工回复；
- 消费者继续发送消息会保存，但 AI 不再自动回复。

## 6. 关闭任务｜20 秒

客服工作台点击“关闭会话”。消费者端刷新后显示会话已关闭。

## 7. 质量证据｜30 秒

展示：

- `/docs` 中的受控工具接口；
- `tool_invocations` 审计；
- handoff 的 `pending / claimed / closed` 状态；
- `data/eval/latest_report.md` 中的固定评测结果。

## 异常演示可选

- 查询他人的 `A10088`：不会泄露订单；
- 问无关问题：不会强行生成售后结论；
- 重复申请人工：不会创建第二条 handoff；
- 两个客服同时接管：只有一个条件更新成功。

## 表达边界

必须说明这是本地技术原型，不执行真实退款、支付或物流，不宣称生产并发能力和线上业务指标。
