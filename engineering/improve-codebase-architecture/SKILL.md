---
name: improve-codebase-architecture
description: 扫描代码库，寻找加深模块的机会，将它们呈现为可视化 HTML 报告，然后围绕你选择的候选项持续追问。
disable-model-invocation: true
---

# 改进代码库架构

找出架构摩擦，并提出**加深机会**——将浅模块重构为深模块。目标是提升可测试性和 AI 可导航性。

这条命令以项目的领域模型为依据，并建立在一套共享的设计词汇之上：

- 调用 Skill 工具并传入 "codebase-design"，获取架构词汇（**module**、**interface**、**depth**、**seam**、**adapter**、**leverage**、**locality**）及其原则（删除测试、“interface is the test surface”、“one adapter = hypothetical seam, two = real”）。每条建议中都必须准确使用这些术语——不要换成 “component”、“service”、“API” 或 “boundary”。
- `CONTEXT.md` 中的领域语言为合适的 seam 提供名称；`docs/adr/` 中的 ADR 记录了这条命令不应重新争论的决策。

## 流程

### 1. 探索

**先确定扫描范围——遵循 YAGNI。** 加深一个模块的价值在于让未来对它的改动更容易，因此应格外关注代码库中近期经常变动的部分。先决定_去哪里_看，再开始查看：

- 如果用户已经指定了方向——某个模块、子系统或痛点——就沿着该方向探索，并跳过下面的推断步骤。
- 否则，向前回溯足够长的一段提交历史（`git log --oneline`），找出代码库的热点——那些反复出现的文件和区域——并优先关注这些路径。如果变更十分分散，没有明确热点，就扩大扫描范围。

先读取项目的领域术语表（`CONTEXT.md`），以及所关注区域中的所有 ADR。

然后启动一个 sub-agent 遍历代码库。不要遵循僵硬的启发式规则——自然地探索，并记录你遇到摩擦的地方：

- 理解一个概念是否需要在许多小模块之间反复跳转？
- 哪些模块很**浅**——interface 几乎和 implementation 一样复杂？
- 哪些地方只是为了便于测试而提取了纯函数，但真正的 bug 隐藏在这些函数的调用方式中（缺乏 **locality**）？
- 哪些紧密耦合的模块会跨越各自的 seam 泄漏？
- 代码库的哪些部分没有测试，或很难通过现有 interface 测试？

对任何疑似浅模块应用**删除测试**：删除它以后，复杂度会集中起来，还是只会转移到别处？你要寻找的信号是“是的，复杂度会集中起来”。

### 2. 将候选项呈现为 HTML 报告

将一个自包含的 HTML 文件写入操作系统的临时目录，确保仓库中不留下任何文件。从 `$TMPDIR` 解析临时目录；如果没有，则回退到 `/tmp`（Windows 上使用 `%TEMP%`）。文件路径使用 `<tmpdir>/architecture-review-<timestamp>.html`，使每次运行都生成新文件。为用户打开该文件——Linux 使用 `xdg-open <path>`，macOS 使用 `open <path>`，Windows 使用 `start <path>`——并告诉用户它的绝对路径。

报告使用 **通过 CDN 引入的 Tailwind** 进行布局和样式设计；当图、流程或时序能够可靠传达结构时，使用**通过 CDN 引入的 Mermaid** 绘制图表。将 Mermaid 与手工制作的 CSS/SVG 视觉效果结合起来——当关系呈图结构时（调用图、依赖关系、时序）使用 Mermaid；当你需要更具编辑设计感的内容时（体量图、剖面图、折叠动画），使用手工制作的 div/SVG。每个候选项都要有一幅**重构前/后的可视化图**。务必以视觉方式呈现。

为每个候选项渲染一张卡片，其中包含：

- **文件**——涉及哪些文件/模块
- **问题**——当前架构为何造成摩擦
- **解决方案**——用通俗语言说明将要改变什么
- **收益**——用 locality 和 leverage 解释收益，并说明测试会如何改善
- **重构前/后图示**——并排放置的自定义图，展示当前模块为何浅，以及将如何加深
- **建议强度**——`Strong`、`Worth exploring`、`Speculative` 三者之一，以徽章形式呈现

在报告末尾添加**首要建议**部分：说明你会优先处理哪个候选项，以及原因。

**领域内容使用 CONTEXT.md 的词汇，架构内容使用 `/codebase-design` 的词汇。** 如果 `CONTEXT.md` 定义了 “Order”，就应写 “the Order intake module”——不要写 “the FooBarHandler”，也不要写 “the Order service”。

**与 ADR 冲突时**：如果某个候选项与现有 ADR 矛盾，只有当摩擦真实且严重到值得重新审视该 ADR 时，才把它列出来。在卡片中清楚标记这一点（例如使用警告提示：_“contradicts ADR-0007 — but worth reopening because…”_）。不要列出 ADR 所禁止的每一种理论重构。

完整的 HTML 脚手架、图表模式和样式指南参见 [HTML-REPORT.md](HTML-REPORT.md)。

此时不要提出 interface 方案。文件写完后，询问用户：“你想探索其中哪一个？”

### 3. 持续追问循环

用户选择一个候选项后，调用 Skill 工具并传入 "grilling"，与用户一起走完决策树——约束、依赖、加深后模块的形态、seam 后面放什么、哪些测试会保留下来。

随着决策逐渐明确，相关副作用应当场发生——调用 Skill 工具并传入 "domain-modeling"，在推进过程中持续更新领域模型：

- **要用 `CONTEXT.md` 中不存在的概念为加深后的模块命名？** 将该术语加入 `CONTEXT.md`。如果文件不存在，就按需创建。
- **在对话中明确了一个模糊术语？** 当场更新 `CONTEXT.md`。
- **用户以关键理由否决了该候选项？** 提议创建一份 ADR，措辞为：_“要我把这记录为 ADR 吗？这样未来的架构审查就不会再次提出它。”_ 只有当未来的探索者确实需要知道该理由，才能避免再次建议同一事项时，才提出这项建议——临时性理由（“现在不值得做”）和不言自明的理由都应跳过。
- **想为加深后的模块探索其他 interface 方案？** 调用 Skill 工具并传入 "codebase-design"，使用其中 design-it-twice 的并行 sub-agent 模式。
