---
name: to-tickets
description: 将计划、spec 或当前对话拆分成一组 tracer-bullet tickets，每张 ticket 都声明其阻塞边，并发布到已配置的 tracker——本地模式下，每张 ticket 一个文件并用文本表达边；真实 tracker 上则使用原生阻塞链接。
disable-model-invocation: true
---

# 转成任务票

将计划、spec 或对话拆分成一组 **tickets**——tracer-bullet 垂直切片，每张 ticket 都声明哪些 tickets 会**阻塞**它。

issue tracker 和 triage label 词汇应已提供给你。如果没有，告诉用户运行 `/setup-matt-pocock-skills`。

## 流程

### 1. 收集上下文

使用对话上下文中已有的一切信息。如果用户以参数形式传入了一个引用（spec 路径、issue 编号或 URL），获取它并完整阅读正文和评论。

### 2. 探索代码库（可选）

如果还没有探索代码库，就先探索，以理解代码的当前状态。Ticket 标题和描述应使用项目领域术语表的词汇，并遵守所触及区域中的 ADR。

寻找预先重构代码的机会，让后续实现更容易。“先让改动变得容易，再完成这个容易的改动。”

### 3. 起草垂直切片

将工作拆分成 **tracer bullet** tickets。

<vertical-slice-rules>

- 每个切片都要穿过所有层（schema、API、UI、tests），形成一条狭窄但**完整**的路径——必须是垂直切片，**不能**是单层的水平切片
- 每个完成的切片都能独立演示或验证
- 每个切片的规模都应能放进一个全新的 context window
- 所有预先重构都应首先完成

</vertical-slice-rules>

为每张 ticket 指定其**阻塞边**——它开始前必须先完成的其他 tickets。没有 blockers 的 ticket 可以立即开始。

**大范围重构是垂直切片的例外。** **大范围重构**是某个机械性变更——例如重命名一列或重新定义共享符号的类型——其**爆炸半径**扩散到整个代码库，导致一次编辑同时破坏数千个调用点，任何垂直切片都无法在保持绿色的情况下落地。不要强行把它塞进 tracer bullet；应按 **expand–contract** 排序。先 expand：在旧形式旁加入新形式，保证一切仍可工作。然后根据爆炸半径将调用点分批迁移（按 package、按目录），每一批都是一张被 expand ticket 阻塞的独立 ticket；由于旧形式仍然存在，每批之间 CI 都保持绿色。最后 contract：在没有调用方继续使用旧形式后将其删除；这张 ticket 被所有迁移批次阻塞。如果连单独的迁移批次都无法保持绿色，则保留这个顺序，但让它们共享一个 integration branch，并全部阻塞最终的 integrate-and-verify ticket——只承诺在那里恢复绿色。

### 4. 询问用户

以编号列表展示建议的拆分方案。每张 ticket 都要显示：

- **标题**：简短的描述性名称
- **被哪些 ticket 阻塞**：必须先完成的其他 tickets（如果有）
- **交付内容**：这张 ticket 会打通的端到端行为

询问用户：

- 粒度合适吗？（太粗 / 太细）
- 阻塞边正确吗——每张 ticket 是否只依赖那些真正构成门槛的 tickets？
- 是否应该合并某些 tickets，或进一步拆分？

持续迭代，直到用户批准拆分方案。

### 5. 将任务票发布到已配置的跟踪器

发布批准后的 tickets。具体**方式**取决于 `/setup-matt-pocock-skills` 配置的 tracker——tickets 本身相同，只有阻塞边的表达形式不同：

- **本地文件** → 在 `.scratch/<feature-slug>/issues/<NN>-<slug>.md` 下为每张 ticket 写一个文件，从 `01` 开始按依赖顺序编号（blockers 在前）。每个文件的 “Blocked by” 列出它依赖的编号/标题。使用下面的单 ticket 文件模板——每个文件只放一张 ticket，绝不要写成一个合并文件。
- **真实 issue tracker（GitHub、Linear 等）** → 按依赖顺序为每张 ticket 发布一个 issue（blockers 在前），这样每张 ticket 的阻塞边都能引用真实标识符。平台支持原生 blocking / sub-issue 关系时就使用它；否则，将每张 ticket 的 “Blocked by” 设置为会阻塞它的 issues。除非另有指示，否则应用 `ready-for-agent` triage label——这些 tickets 生来就可由 agent 接手。

推进**前沿**：所有 blockers 都已完成的 ticket 都位于前沿。对于纯线性链，这意味着从上到下依次处理。

**不要**关闭或修改任何 parent issue。

<local-ticket-template>

# <NN> — <任务票标题>

**要构建什么：** 从用户视角描述这张 ticket 会打通的端到端行为——不要逐层列出实现清单。

**被哪些 ticket 阻塞：** 列出构成门槛的 ticket 编号/标题，或写“无——可以立即开始”。

**状态：** ready-for-agent

- [ ] 验收标准 1
- [ ] 验收标准 2

</local-ticket-template>

<issue-template>

## 上级事项

指向 tracker 中 parent issue 的引用（如果来源是已有 issue；否则省略本节）。

## 要构建什么

从用户视角描述这张 ticket 会打通的端到端行为——不要按层拆解实现。

## 验收标准

- [ ] 标准 1
- [ ] 标准 2

## 被哪些任务票阻塞

- 指向每张阻塞 ticket 的引用，或写“无——可以立即开始”。

</issue-template>

无论采用哪种形式，都不要写具体文件路径或代码片段——它们很快会过时。例外：如果 prototype 产出的某个片段比文字更精确地编码了一项决策（状态机、reducer、schema、type shape），可以将它内联，并简短注明它来自 prototype。只保留富含决策的部分——不是可运行的 demo，只保留重要内容。
