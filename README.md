### 工程

日常代码工作技能。本个人技能集合使用 `ask-agent` 作为路由入口，不同步 `ask-matt`。

**手动调用：**

- **[ask-agent](./engineering/ask-agent/SKILL.md)** - 根据当前问题、目标和工作阶段，推荐合适的 skill 或组合工作流程。
- **[grill-with-docs](./engineering/grill-with-docs/SKILL.md)** - 通过持续追问打磨计划或设计，并同步建立领域术语、`CONTEXT.md` 和 ADR。
- **[triage](./engineering/triage/SKILL.md)** - 按状态机分类、验证和处理 issue 或外部 PR，生成 agent brief。
- **[improve-codebase-architecture](./engineering/improve-codebase-architecture/SKILL.md)** - 扫描代码库，找出将浅模块加深的架构机会，并生成可视化报告。
- **[to-spec](./engineering/to-spec/SKILL.md)** - 把已有对话综合成 spec，并发布到 issue tracker。
- **[to-tickets](./engineering/to-tickets/SKILL.md)** - 把计划或 spec 拆成可独立交付的 tracer-bullet tickets，标注阻塞关系。
- **[implement](./engineering/implement/SKILL.md)** - 根据 spec 或 tickets 实现功能，结合 TDD，完成后做 code review 并提交。
- **[wayfinder](./engineering/wayfinder/SKILL.md)** - 为大于单次会话容量的大型工作建立决策地图，逐项解决前置决策。

**模型可自动调用：**

- **[prototype](./engineering/prototype/SKILL.md)** - 编写一次性原型，快速验证状态模型、业务逻辑或 UI 方案。
- **[diagnosing-bugs](./engineering/diagnosing-bugs/SKILL.md)** - 用“复现失败 → 缩小范围 → 假设 → 加仪器 → 修复 → 回归测试”的循环诊断困难 bug 和性能回归。
- **[research](./engineering/research/SKILL.md)** - 查找官方文档、源码和规范等一手资料，将带引用的结论写入 Markdown 文件。
- **[tdd](./engineering/tdd/SKILL.md)** - 以测试驱动开发，围绕公开接口和约定的 seam 执行 red-green-refactor。
- **[domain-modeling](./engineering/domain-modeling/SKILL.md)** - 建立和打磨项目领域模型，统一术语，维护 `CONTEXT.md` 与 ADR。
- **[codebase-design](./engineering/codebase-design/SKILL.md)** - 设计深模块：用小接口和清晰 seam 隐藏大量实现。
- **[code-review](./engineering/code-review/SKILL.md)** - 从固定版本点做双轴审查：编码标准和需求/spec。
- **[resolving-merge-conflicts](./engineering/resolving-merge-conflicts/SKILL.md)** - 逐个冲突块理解双方意图，解决正在进行的 merge/rebase 冲突并完成操作。
- **[wizard](./engineering/wizard/SKILL.md)** - 生成交互式 Bash 向导，引导人类完成凭据配置、第三方后台操作或一次性迁移。

### 生产力

通用工作流技能，不限定于代码任务。

- **[grill-me](./productivity/grill-me/SKILL.md)** - 围绕计划或设计持续追问，直到每个决策分支都被澄清。
- **[grilling](./productivity/grilling/SKILL.md)** - 通用的设计树追问引擎，按轮次压力测试计划、决策或想法。
- **[handoff](./productivity/handoff/SKILL.md)** - 将当前对话压缩成交接文档，方便另一个 agent 继续工作。
- **[teach](./productivity/teach/SKILL.md)** - 在当前工作区内，通过多次会话教授用户一项技能或概念。
- **[wait-what](./productivity/wait-what/SKILL.md)** - 当上一条消息没有讲清时，用更简单的语言和上下文重新说明。
- **[writing-for-agents](./productivity/writing-for-agents/SKILL.md)** - 编写供 agent 读取的 skill、`AGENTS.md` 和 `CLAUDE.md` 等文档。

### 开发中

尚在试用和调整的技能。

- **[loop-me](./in-progress/loop-me/SKILL.md)** - 通过持续追问，把重复发生的生活或工作循环整理成可实现的工作流规格。
- **[writing-fragments](./in-progress/writing-fragments/SKILL.md)** - 在写作探索阶段挖掘和积累原始片段，暂不组织文章结构。
- **[writing-shape](./in-progress/writing-shape/SKILL.md)** - 从已有原始材料出发，逐段塑造文章的论点、顺序和形式。
- **[writing-beats](./in-progress/writing-beats/SKILL.md)** - 从已有原始材料出发，以可选路径的节拍方式逐步写成文章。
