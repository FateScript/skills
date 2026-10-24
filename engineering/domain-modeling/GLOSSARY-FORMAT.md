# GLOSSARY.md 格式

## 结构

```md
# {上下文名称}

{用一两句话说明该上下文是什么，以及它为什么存在。}

## 语言

**Order**:
{用一两句话定义该术语}
_避免使用_: Purchase, transaction

**Invoice**:
交付后发送给客户的付款请求。
_避免使用_: Bill, payment request

**Customer**:
下订单的人或组织。
_避免使用_: Client, buyer, account
```

## 规则

- **明确选择用词。** 同一概念有多个名称时，选择最合适的一个，其余列在 `_避免使用_` 下。
- **定义简短。** 最多一两句话，解释它**是什么**，而不是它做什么。
- **只收录该项目上下文特有的术语。** 超时、错误类型和通用工具模式等一般编程概念不属于这里，即使项目大量使用它们。加入前先判断：这是本上下文独有的概念，还是一般编程概念？
- **自然分组时使用子标题。** 如果所有术语属于同一领域，平铺列表即可。

## 单上下文与多上下文仓库

**单上下文（大多数仓库）：** 在仓库根目录使用一份 `GLOSSARY.md`。

**多上下文：** 在根目录创建 `GLOSSARY-MAP.md`，列出各上下文、位置及关系：

```md
# 术语表映射

## 上下文

- [Ordering](./src/ordering/GLOSSARY.md) — 接收并追踪客户订单
- [Billing](./src/billing/GLOSSARY.md) — 生成发票并处理付款
- [Fulfillment](./src/fulfillment/GLOSSARY.md) — 管理仓库拣货与发货

## 关系

- **Ordering → Fulfillment**：Ordering 发出 `OrderPlaced` 事件，Fulfillment 据此开始拣货
- **Fulfillment → Billing**：Fulfillment 发出 `ShipmentDispatched` 事件，Billing 据此生成发票
- **Ordering ↔ Billing**：共享 `CustomerId` 和 `Money` 类型
```

Skill 根据现有文件判断结构：

- 有 `GLOSSARY-MAP.md`：先读取映射，定位上下文。
- 只有根目录的 `GLOSSARY.md`：按单上下文处理。
- 两者都没有：在第一个术语确定时，按需创建根目录的 `GLOSSARY.md`。

存在多个上下文时，推断当前主题属于哪个上下文；无法确定再询问。
