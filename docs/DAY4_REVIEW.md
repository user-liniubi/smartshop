# Day 4 复盘｜核心数据表

## 今日知识点

- **主键与外键**：订单通过 `user_id` 关联消费者，通过 `product_id` 关联商品。
- **对象级归属**：订单的 `user_id` 由后端持久化并在查询时作为过滤条件，不能信任客户端传入的身份。
- **唯一约束**：用户名和订单号唯一，避免重复登录身份和重复业务单号。
- **复合索引**：订单按 `user_id + created_at` 建索引，为后续“某用户的订单历史”查询做准备。
- **幂等种子数据**：脚本通过用户名、商品名和订单号检查现有记录，可重复执行。

## 完成代码

- 六张核心表：`users`、`products`、`orders`、`chat_sessions`、`chat_messages`、`handoffs`
- SQLAlchemy 模型：`backend/app/models/entities.py`
- 受控状态枚举：`backend/app/models/enums.py`
- 密码哈希：`backend/app/core/security.py`
- 幂等演示数据脚本：`sample_data/seed.py`
- 核心表迁移：`migrations/versions/6dcf03460220_create_core_tables.py`

## 实际验收结果

MySQL 8.0.40 中的表：

```text
alembic_version
chat_messages
chat_sessions
handoffs
orders
products
users
```

当前迁移版本：

```text
6dcf03460220 (head)
```

演示数据数量：

```text
users=3
products=5
orders=5
```

五条订单均已核对归属：

| 订单号 | 消费者 | 商品 | 状态 |
|---|---|---|---|
| A10086 | consumer_demo | SmartShop 降噪耳机 Pro | delivered |
| A10087 | consumer_demo | SmartShop 机械键盘 K87 | shipped |
| A10088 | consumer_other | SmartShop 27 英寸显示器 | delivered |
| A10089 | consumer_demo | SmartShop 14 英寸笔记本 | cancelled |
| A10090 | consumer_other | SmartShop 无线鼠标 M2 | delivered |

自动化测试覆盖：

- 首次导入后表数量正确
- 第二次导入不产生重复数据
- 订单与消费者、商品关联正确
- 密码可用 scrypt 校验
- 相同密码因随机盐生成不同哈希
- 错误密码和损坏哈希被拒绝

自动化检查结果：

```text
13 passed, 1 warning in 2.63s
All checks passed!
42 files already formatted
```

## 设计取舍

- 自动化测试使用内存 SQLite，保持测试快速且不依赖外部数据库；真实 MySQL 通过迁移、数据查询和后续接口联调验收。
- 密码只保存 scrypt 哈希，不保存明文；演示密码仅用于虚构本地账号。
- 订单状态、用户角色、消息来源等使用字符串列并结合数据库 `CHECK` 约束，兼顾 MySQL 与测试 SQLite 的兼容性。

## 第四天验收

- [ ] 已学习（需本人完成知识复习并确认）
- [x] 已开发
- [x] 已测试
- [x] 已提交 Git
- [x] 工程验收通过

提交信息：`feat: add core tables and demo seed data`  
提交哈希：`5dac1bf`
