---
name: ask-agent
description: 根据当前问题、目标和工作阶段，推荐合适的 skill 或组合工作流程。
---

# 询问 Agent

这是个人技能集合的路由器。用户把当前问题交给你时，先识别他们要解决的问题、当前阶段和约束，再推荐最合适的个别 skill 或工作流程。路由范围以个人仓库中实际存在的 skill 为准。

## 路由方法

1. **先判断状态，再匹配词。** 从对话和工作区读取必要事实：用户是在探索想法、做决策、实现、调试、审查，还是在处理一项已经进行中的工作。不要只因为某个词出现就选一项 skill。
2. **只给一个主推荐。** 可再给一个备选或下一步，但不要罗列一长串名单让用户自己猜。每个推荐都说明它解决的问题和何时切换。
3. **将多个 skill 组成顺序。** 如果用户要走一条工作流程，按阶段给出顺序，并标明每一步的产物如何解锁下一步。
4. **先检查前置条件。** `to-spec`、`to-tickets`、`triage` 和 `wayfinder` 依赖仓库已配置的 issue tracker 约定。如果环境中没有这些约定，在推荐中明确标出前置条件，而不要假设它们已经存在。
5. **路由只负责选择。** 输出推荐和理由，等用户选择或请求执行后再进入被推荐的 skill；不要在路由结果里同时开始另一项实际工作。
6. **只在必要时追问。** 如果两条路径的前置条件不同，且现有上下文无法判断哪一条，只问一个最小的澄清问题，同时附上推荐答案。其他情况下做出合理假设并给出推荐。

## 主流程：想法→交付

这是大多数功能开发请求的默认路径：

`grill-with-docs` → `to-spec` → `to-tickets` → `implement` → `code-review`

- 还在澄清想法时，在仓库中推荐 `grill-with-docs`；没有工作目录时推荐 `grill-me`。
- 讨论已足够清楚、需要多次会话才能完成时，用 `to-spec` 固化讨论，再用 `to-tickets` 切成可独立交付的垂直切片。
- 工作已经定义好、不值得再做规划时，直接推荐 `implement`。`implement` 内部会按需要使用 `tdd`，完成后使用 `code-review` 。
- 只想先写测试来构建一个具体行为时，单独推荐 `tdd`；已有分支或 PR 需要审查时，单独推荐 `code-review` 。

## 入口匝道

| 当前情况 | 主推荐 | 后续路径 |
| --- | --- | --- |
| 收到了还没整理的 bug report、feature request 或 PR | `triage` | 就绪后转给 `implement` |
| 困难 bug、间歇失败、性能回退 | `diagnosing-bugs` | 修复后用 `tdd` 留下回归测试 |
| 工作大到一次会话无法容纳，且路线不清晰 | `wayfinder` | 路线清晰后转到 `to-spec` |
| 代码库有架构摩擦或浅模块 | `improve-codebase-architecture` | 选定候选项后用 `grill-with-docs`、`codebase-design` |
| 需要一个可运行的答案来判断逻辑或 UI | `prototype` | 得出结论后回到实现流程 |

## 独立路径

| 问题形态 | 推荐 skill |
| --- | --- |
| 只需要通用追问引擎，不需要仓库记录或无状态包装 | `grilling` |
| 需要统一领域术语、编写 `CONTEXT.md` 或 ADR | `domain-modeling` |
| 需要设计深模块、选择 interface 或 seam | `codebase-design` |
| 要查找官方文档、API 或规范事实 | `research` |
| 正处于 git merge/rebase 冲突 | `resolving-merge-conflicts` |
| 只有人类能完成的凭据、dashboard 或一次性迁移步骤 | `wizard` |
| 需要将对话或任务交给新 agent | `handoff` |
| 用户没听懂上一条消息 | `wait-what` |
| 多次会话学习一个概念或技能 | `teach` |
| 挖掘写作原始片段 | `writing-fragments` → `writing-shape` 或 `writing-beats` |
| 发现工作中可重复自动化的循环 | `loop-me` |
| 编写 skill、`AGENTS.md` 或 `CLAUDE.md` | `writing-for-agents` |
| 编写 zsh 补全生成器 | `zcompy-completion` |

## 输出格式

每次输出以下结构：

```text
主推荐：`<skill>`
理由：<它与当前问题的匹配点>
现在解决：<这一步会产出什么>
后续：<在什么条件下切换到哪个 skill>
备选：`<skill>`（仅在存在真实分歧时列出）
```

推荐与用户当前阶段最近的一项，不要把整个技能集合的名单当作答案。
