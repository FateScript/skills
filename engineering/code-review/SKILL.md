---
name: code-review
description: 从一个固定点（commit、branch、tag 或 merge-base）开始，沿两个维度审查变更——Standards（代码是否遵循本仓库已记录的编码标准？）和 Spec（代码是否符合原始 issue/spec 的要求？）。在并行 sub-agent 中运行两项审查，并将结果并列报告。用于用户想要审查 branch、PR、进行中的变更，或要求“review since X”时。
---

沿两个维度审查用户提供的固定点与 `HEAD` 之间的 diff：

- **Standards**——代码是否符合本仓库已记录的编码标准？
- **Spec**——代码是否忠实实现了原始 issue / spec？

两个维度都由**并行 sub-agent** 处理，以免彼此的 context 相互污染；随后由本技能汇总它们的发现。

issue tracker 应当已经提供给你。如果缺少 `docs/agents/issue-tracker.md`，请让用户运行 `/setup-matt-pocock-skills`。

## 流程

### 1. 锁定固定点

用户指定的任何内容都是固定点——commit SHA、branch 名称、tag、`main`、`HEAD~5` 等。如果用户没有指定，就询问。

只记录一次 diff 命令：`git diff <fixed-point>...HEAD`（使用 three-dot，因此比较基准是 merge-base）。同时通过 `git log <fixed-point>..HEAD --oneline` 记录 commit 列表。

继续之前，先确认固定点可以解析（`git rev-parse <fixed-point>`），并且 diff 非空。无效 ref 或空 diff 应当在这里就失败，而不是等到两个并行 sub-agent 内部才失败。

### 2. 确定规格来源

按以下顺序查找原始 spec：

1. commit message 中的 issue 引用（`#123`、`Closes #45`、GitLab `!67` 等）——按照 `docs/agents/issue-tracker.md` 中的工作流获取。
2. 用户作为参数传入的路径。
3. `docs/`、`specs/` 或 `.scratch/` 下与 branch 名称或 feature 匹配的 spec 文件。
4. 如果仍未找到，询问用户 spec 在哪里。如果用户表示没有 spec，则跳过 **Spec** sub-agent，并报告“没有可用的 spec”。

### 3. 确定标准来源

查找仓库中说明代码应当如何编写的所有内容，例如 `CODING_STANDARDS.md` 或 `CONTRIBUTING.md`。

除了仓库自身记录的内容之外，Standards 维度始终还要带上下面的**坏味道基线**——这是一组固定的 Fowler code smells（_Refactoring_，第 3 章），即使仓库没有记录任何标准也适用。它受两条规则约束：

- **以仓库为准。** 已记录的仓库标准始终优先；如果仓库标准明确认可某种会被基线标记的写法，就不要报告该 smell。
- **始终需要判断。** 每一种 smell 都只是带标签的启发式判断（例如 “possible Feature Envy”），绝不是硬性违规；而且与这里的任何标准一样，已经由工具强制检查的内容应当跳过。

每一种 smell 都按“它是什么”→“如何修复”的方式描述；将它们与 diff 对照：

- **Mysterious Name**——函数、变量或类型的名称没有揭示它做什么或保存什么。→ 重命名；如果找不到一个诚实准确的名称，说明设计本身还很模糊。
- **Duplicated Code**——同样的逻辑结构出现在变更中的多个 hunk 或文件里。→ 提取共享结构，并从两处调用。
- **Feature Envy**——某个 method 访问另一个 object 的数据，多于访问自身的数据。→ 将该 method 移到它所依恋的数据上。
- **Data Clumps**——同样的几个 field 或 param 总是结伴传递（说明一个 type 正等待被创建）。→ 将它们组合成一个 type，再传递该 type。
- **Primitive Obsession**——使用 primitive 或 string 表示一个本应拥有自身 type 的领域概念。→ 为该概念创建一个小型专用 type。
- **Repeated Switches**——针对同一个 type 的相同 `switch`/`if` 级联在变更中反复出现。→ 用 polymorphism 替代，或让两处共用同一个 map。
- **Shotgun Surgery**——一个逻辑变更迫使你在 diff 中分散修改许多文件。→ 将会一起变化的内容聚集到同一个 module 中。
- **Divergent Change**——一个文件或 module 因为多个互不相关的原因而被修改。→ 拆分它，使每个 module 只因一种原因而变化。
- **Speculative Generality**——为 spec 并不需要的需求添加 abstraction、parameter 或 hook。→ 删除它；重新内联，直到真正的需求出现。
- **Message Chains**——调用方依赖了本不该知道的长串 `a.b().c().d()` 导航。→ 将这段遍历隐藏在第一个 object 的某个 method 后面。
- **Middle Man**——某个 class 或 function 的主要作用只是继续委托。→ 删除中间层，直接调用真正的目标。
- **Refused Bequest**——某个 subclass 或 implementer 忽略或覆盖了所继承内容中的大部分。→ 放弃 inheritance，改用 composition。

### 4. 并行启动两个子代理

**Standards sub-agent 的 prompt**——包含：

- 完整的 diff 命令和 commit 列表。
- 步骤 3 中找到的 standards-source 文件列表，**再加上完整粘贴的步骤 3 坏味道基线**——sub-agent 无法通过其他方式获得它。
- 任务说明：“按相关文件/hunk 报告：(a) diff 中每一处违反已记录标准的位置，并引用相应标准（文件 + 规则）；(b) 发现的所有基线 smell，写明名称并引用对应 hunk。区分硬性违规与判断性意见——违反已记录标准可以是硬性违规，但基线 smell 始终只是判断性意见，而且已记录的仓库标准优先于基线。跳过工具已经强制检查的内容。控制在 400 字以内。”

**Spec sub-agent 的 prompt**——包含：

- diff 命令和 commit 列表。
- spec 的路径或已获取的内容。
- 任务说明：“报告：(a) spec 要求但缺失或只完成一部分的需求；(b) diff 中未被要求的行为（scope creep）；(c) 看起来已经实现、但实现方式似乎有误的需求。每项发现都要引用对应的 spec 行。控制在 400 字以内。”

如果缺少 spec，就跳过 Spec sub-agent，并在最终报告中说明。

### 5. 汇总

将两份报告分别放在 `## Standards` 和 `## Spec` 标题下，保持原文或只做轻微清理。**不要**合并或重新排序发现——两个维度是有意分开的（参见_为什么要分成两个维度_）。

最后用一行总结收尾：每个维度的发现总数，以及该维度内最严重的问题（如果存在）。不要跨维度选出一个总冠军——维度分离正是为了避免这种重新排序。

## 为什么要分成两个维度

一项变更可能通过其中一个维度，却未通过另一个：

- 代码遵循了所有标准，却实现了错误的内容 → **Standards 通过，Spec 失败。**
- 代码完全按照 issue 的要求实现，却破坏了项目约定 → **Spec 通过，Standards 失败。**

分开报告可防止一个维度掩盖另一个维度的问题。
