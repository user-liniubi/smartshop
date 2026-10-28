# Day 5 复盘｜订单与基础权限

## 今日知识点

- **身份认证**：用户名密码验证成功后签发带过期时间的 HMAC 签名 Token。
- **对象级授权**：查询订单时必须同时匹配订单 ID 和当前认证用户 ID。
- **防信息泄露**：访问其他用户订单统一返回 404，不区分“订单不存在”和“不是本人订单”。
- **通用登录错误**：用户名不存在和密码错误返回相同错误，降低账号枚举风险。
- **安全密码存储**：数据库只保存 scrypt 哈希与随机盐。
- **pytest 依赖替换**：通过 FastAPI 依赖覆盖，在内存数据库上测试真实路由和服务。

## 完成代码与接口

- `POST /auth/login`：演示账号登录并返回 Bearer Token
- `GET /orders/{order_id}`：查询当前登录用户自己的订单
- 受保护身份依赖：`backend/app/api/dependencies.py`
- 登录服务：`backend/app/services/auth.py`
- 订单服务：`backend/app/services/orders.py`
- 用户与订单查询仓储：`backend/app/repositories/`
- 登录和订单 Schema：`backend/app/schemas/auth.py`、`backend/app/schemas/order.py`
- Token 签名、过期校验和密码哈希：`backend/app/core/security.py`

## 正常路径

真实 MySQL 联调：

| 操作 | 结果 |
|---|---|
| `consumer_demo` 使用 `Demo123!` 登录 | `200`，返回 Bearer Token |
| 查询自己的订单 `A10086` | `200`，返回商品和 `delivered` 状态 |

实际订单响应包含：

```json
{
  "id": 1,
  "order_no": "A10086",
  "status": "delivered",
  "product": {
    "id": 1,
    "name": "SmartShop 降噪耳机 Pro"
  }
}
```

## 异常与边界路径

| 操作 | 结果 |
|---|---|
| 错误密码登录 | `401 invalid_credentials` |
| 未携带 Token 查询订单 | `401 authentication_required` |
| Token 被篡改或已过期 | `401 invalid_token` |
| `consumer_demo` 查询 `consumer_other` 的订单 | `404 order_not_found` |
| 订单 ID 为 0 或负数 | `422 validation_error` |

自动化测试结果：

```text
21 passed, 1 warning in 7.33s
All checks passed!
55 files already formatted
```

## 遇到的问题与解决

1. 初次登录测试误用了空数据库夹具，接口正确返回 401。修正为演示数据夹具后，正常登录路径通过。
2. 查询其他用户订单时，选择返回 404 而不是 403，避免攻击者通过状态码判断任意订单号是否存在。

## 设计取舍

- 演示阶段使用标准库实现 HMAC 签名 Token，避免额外认证框架；生产化阶段如需要刷新 Token、吊销和密钥轮换，可替换为成熟 JWT/OIDC 方案。
- 登录时对不存在的用户也执行密码校验，降低响应时间差造成的账号枚举风险。
- Token 中的角色会在每次请求时与数据库角色复核，不单纯信任 Token 声明。

## 第五天验收

- [ ] 已学习（需本人完成知识复习并确认）
- [x] 已开发
- [x] 已测试
- [ ] 已提交 Git（首次提交后更新）
- [x] 工程验收通过
