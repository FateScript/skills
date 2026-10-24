---
name: pr
description: 编写 Pull Request 正文时使用。
metadata:
  credits:
    skill: show-me
    author: Dex Horthy
    organisation: Humanlayer
    url: "https://github.com/humanlayer/skills/blob/main/plugins/show-me/skills/show-me/SKILL.md"
---

按以下模板编写 PR 正文：

```markdown
## Summary

<图、diff 草图或文件树>

## Evidence

- **Before:** <截图、输出或失败的测试>
  **After:** <截图、输出或通过的测试>

## Merge Danger

**Door:** <one-way 或 two-way>

<可选：说明>

**Blast Radius:** <一个词概括影响范围>

<可选：合并后可能产生的影响>
```

省略开场白，文字保持简短；领域词汇采用项目 `GLOSSARY.md` 中的用语。

## Summary

选择能清楚说明关键变化的最小视图：

- 逻辑或算法用伪代码，例如 `on(save) → 未变化则返回缓存 → 写入新内容 → 返回新结果`。
- 运行时流程用调用树，标出关键调用的先后与嵌套关系。
- UI 用组件树，注明重要 state 和 module 边界。
- 文件职责或较大的重构用浅层文件树。
- 组件交互、控制流或数据流可以用 Mermaid。
- 如果重点是现有结构发生了什么变化，用 `diff`，并让 diff 的形态匹配主题：组件、文件布局、调用树、状态或控制流。
- 大部分内容都是新写的、删去上下文会掩盖职责或顺序、或读者需要可复制的目标形态时，展示完整代码块。

例如，描述控制流变化时：

```diff
 on(save)
-  write content
+  if content is unchanged
+    return cached result
+  write new content
+  invalidate cache
```

描述文件布局时：

```diff
 src/
 ├── commands/
+│   └── show-me.ts       # expands the slash command
 ├── sessions/
-└── transport.ts
+└── transport/
+    ├── client.ts
+    └── stream.ts
```

把每个视图放在它支持的简短说明旁边。只保留当前问题需要的调用、文件、属性、状态和边界；可以组合多种视图，但避免堆砌。

## Evidence

给出变更确实生效的具体**前后对照**。视觉变更且环境可用时优先截图；否则使用测试结果、控制台输出等执行证据。精确指出哪个测试之前失败、之后通过，可以用伪代码表达测试步骤。

## Merge Danger

说明合并是 **two-way door**（容易回滚）还是 **one-way door**（难以撤销），并解释必要的风险。`Blast Radius` 概括变更可能影响的范围，例如布局偏移、下游使用者故障或移动端适配。
