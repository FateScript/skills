---
name: codebase-design
description: 设计深模块的共享词汇。用于用户想要设计或改进模块的 interface、寻找加深机会、决定 seam 的位置、提高代码的可测试性或 AI 可导航性，或其他技能需要深模块词汇时。
---

# 代码库设计

设计**深模块**：用小型 interface 隐藏大量行为，将其放在清晰的 seam 上，并能通过该 interface 进行测试。只要在设计或重构代码，就使用这套语言和原则。目标是为调用方带来 leverage，为维护者带来 locality，并让所有人都能方便地测试。

## 术语表

请准确使用以下术语——不要用 “component”、“service”、“API” 或 “boundary” 替代它们。统一语言正是这套词汇的意义所在。

**Module**——任何同时拥有 interface 和 implementation 的事物。刻意不限定规模：它可以是函数、类、包，也可以是跨越多个层级的切片。_避免使用_：unit、component、service。

**Interface**——调用方为了正确使用 module 必须知道的一切：不仅包括类型签名，还包括不变量、顺序约束、错误模式、必需配置和性能特征。_避免使用_：API、signature（这两个词过于狭窄——只指类型层面的表面）。

**Implementation**——module 内部的内容，也就是它的代码主体。它与 **Adapter** 不同：一个事物可以是小型 adapter，却拥有大型 implementation（例如 Postgres repo）；也可以是大型 adapter，却只有小型 implementation（例如内存 fake）。当讨论重点是 seam 时，使用 “adapter”；其他情况下使用 “implementation”。

**Depth**——interface 所带来的 leverage：调用方（或测试）每学习一单位 interface，能够使用多少行为。大量行为隐藏在小型 interface 后面的 module 是**深**的；interface 与 implementation 几乎一样复杂的 module 是**浅**的。

**Seam** _（Michael Feathers）_——一个无需在该处编辑代码就能改变行为的位置；也就是 module 的 interface 所在的_位置_。seam 应该放在哪里，是一项独立的设计决策，与 seam 后面应该放什么不同。_避免使用_：boundary（它与 DDD 中的 bounded context 含义重叠）。

**Adapter**——在 seam 处满足某个 interface 的具体事物。它描述的是_角色_（填补哪个位置），而不是实质（内部是什么）。

**Leverage**——调用方从 depth 中获得的收益：每学习一单位 interface，就能得到更多能力。一份 implementation 可以在 N 个调用点和 M 个测试中反复产生回报。

**Locality**——维护者从 depth 中获得的收益：变更、bug、知识和验证都集中在一处，而不是散落在各个调用方。修复一次，处处生效。

## 深模块与浅模块

**深模块** = 小型 interface + 大量 implementation：

```
┌─────────────────────┐
│    小型 Interface   │  ← 方法少，参数简单
├─────────────────────┤
│                     │
│  深层 Implementation│  ← 隐藏复杂逻辑
│                     │
└─────────────────────┘
```

**浅模块** = 大型 interface + 少量 implementation（应避免）：

```
┌─────────────────────────────────┐
│          大型 Interface         │  ← 方法多，参数复杂
├─────────────────────────────────┤
│        薄 Implementation        │  ← 仅仅透传
└─────────────────────────────────┘
```

设计 interface 时，问自己：

- 能否减少方法数量？
- 能否简化参数？
- 能否将更多复杂度隐藏在内部？

## 原则

- **Depth 是 interface 的属性，而不是 implementation 的属性。** 深模块在内部可以由小型、可 mock、可替换的部分组成——只是这些部分不属于 interface。一个 module 既可以有**内部 seam**（implementation 私有，供自身测试使用），也可以在 interface 处有**外部 seam**。
- **删除测试。** 想象删除这个 module。如果复杂度也随之消失，它只是一个透传层。如果复杂度会重新出现在 N 个调用方中，那么它确实发挥了应有的作用。
- **Interface 就是测试表面。** 调用方和测试跨越同一个 seam。如果你想越过 interface 去测试内部，module 的形态可能并不正确。
- **一个 adapter 意味着假设中的 seam；两个 adapter 才意味着真实的 seam。** 除非确实有事物会跨越 seam 发生变化，否则不要引入 seam。

## 为可测试性而设计

良好的 interface 会让测试自然而然：

1. **接收依赖，不要自行创建依赖。**

   ```typescript
   // 易于测试
   function processOrder(order, paymentGateway) {}

   // 难以测试
   function processOrder(order) {
     const gateway = new StripeGateway();
   }
   ```

2. **返回结果，不要制造副作用。**

   ```typescript
   // 易于测试
   function calculateDiscount(cart): Discount {}

   // 难以测试
   function applyDiscount(cart): void {
     cart.total -= discount;
   }
   ```

3. **缩小表面积。** 方法越少，需要的测试就越少。参数越少，测试准备就越简单。

## 关系

- 一个 **Module** 恰好拥有一个 **Interface**（它呈现给调用方和测试的表面）。
- **Depth** 是 **Module** 的属性，要相对于它的 **Interface** 来衡量。
- **Seam** 是 **Module** 的 **Interface** 所在的位置。
- **Adapter** 位于 **Seam** 处，并满足相应的 **Interface**。
- **Depth** 为调用方带来 **Leverage**，为维护者带来 **Locality**。

## 不采用的表述

- **将 depth 定义为 implementation 行数与 interface 行数之比**（Ousterhout）：这种定义会鼓励给 implementation 注水。这里改用“depth 即 leverage”的定义。
- **将 “Interface” 理解为 TypeScript 的 `interface` 关键字或类的 public methods**：这种理解过于狭窄——这里的 interface 包括调用方必须知道的每一项事实。
- **“Boundary”**：它与 DDD 中的 bounded context 含义重叠。应使用 **seam** 或 **interface**。

## 进一步深入

- **根据依赖关系加深一组模块**——参见 [DEEPENING.md](DEEPENING.md)：依赖类别、seam 纪律，以及“替换而非叠加”的测试方式。
- **探索其他 interface 方案**——参见 [DESIGN-IT-TWICE.md](DESIGN-IT-TWICE.md)：启动多个并行 sub-agent，以几种截然不同的方式设计 interface，再根据 depth、locality 和 seam 的位置进行比较。
