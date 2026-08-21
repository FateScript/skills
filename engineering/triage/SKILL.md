---
name: triage
description: 推动 issues 和外部 PR 在 triage role 状态机中流转——分类、验证、按需追问，并编写可直接交给 agent 的 briefs。
disable-model-invocation: true
---

# 分诊

推动项目 issue tracker 中的 issues 在一个小型 triage role 状态机中流转。

如果本仓库将外部 pull requests 视为请求入口（参见 issue-tracker 配置），triage 也覆盖它们：**PR 就是附带代码的 issue**——相同 roles、相同 states、相同状态机，只在下文标注“针对 PR”之处存在少量差异。根据 tracker 配置，将裸 `#42` 解析为 issue 或 PR。

在 triage 期间发布到 issue tracker 的每条评论或 issue **都必须**以这段免责声明开头：

```
> *此内容由 AI 在 triage 期间生成。*
```

## 参考文档

- [AGENT-BRIEF.md](AGENT-BRIEF.md)——如何编写经久耐用的 agent briefs
- [OUT-OF-SCOPE.md](OUT-OF-SCOPE.md)——`.out-of-scope/` 知识库的工作方式

## 角色

两个**类别** roles：

- `bug`——某些东西坏了
- `enhancement`——新功能或改进

五个**状态** roles：

- `needs-triage`——需要 maintainer 评估
- `needs-info`——正在等待 reporter 提供更多信息
- `ready-for-agent`——已经完整说明，可交给 AFK agent
- `ready-for-human`——需要人类实现
- `wontfix`——不会处理

对于 PR，相同 states 要结合所附代码来理解：`ready-for-agent` 表示已附上一份 brief，agent 应接手 diff 的下一步；`ready-for-human` 表示已准备好由人类 merge。

每个完成 triage 的 issue 都应恰好带有一个类别 role 和一个状态 role。如果状态 roles 冲突，应指出冲突并在执行任何其他操作前询问 maintainer。

这些是规范 role 名称——issue tracker 中实际使用的 label 字符串可能不同。相关 mapping 应已提供给你。如果没有，告诉用户运行 `/setup-matt-pocock-skills`。

状态转换：没有 label 的 issue 通常先进入 `needs-triage`；然后再从这里转到 `needs-info`、`ready-for-agent`、`ready-for-human` 或 `wontfix`。Reporter 回复后，`needs-info` 会回到 `needs-triage`。Maintainer 可以随时覆盖状态——对于看起来异常的转换，应指出并先询问再继续。

## 调用方式

Maintainer 调用 `/triage`，用自然语言描述想做什么。理解请求并执行。例如：

- “显示所有需要我关注的内容”
- “我们来看看 #42”（issue 或 PR）
- “把 #42 移到 ready-for-agent”
- “有哪些内容已经可以让 agents 接手？”

## 显示需要关注的内容

查询 issue tracker，按最旧优先展示三个分组：

1. **无 label**——从未 triage。
2. **`needs-triage`**——正在评估。
3. **自上次 triage notes 以来 reporter 有新活动的 `needs-info`**——需要重新评估。

如果 PR 在范围内，就在这些分组中包含外部 PR，并为每一行标记 `[PR]` 或 `[issue]`。发现过程只展示_外部_ PR（tracker 配置定义谁算外部人员）——协作者正在进行的 PR 不属于 triage 工作。此筛选只用于发现；无论作者是谁，被明确点名的 PR 始终都要 triage。

显示每组数量以及每项的一行摘要。让 maintainer 选择。

## 分诊某个具体 issue 或 PR

1. **收集上下文。** 完整阅读 issue 或 PR（正文、评论、labels、作者、日期；如果是 PR，还要阅读 diff）。解析此前的所有 triage notes，以免重复询问已经解决的问题。使用项目的领域术语表探索代码库，并遵守所触及区域中的 ADR。针对代码库执行两项检查：(a) **冗余**——按领域概念（而不只是请求的原始措辞）搜索是否已有所请求行为的实现，并报告查找过的位置。如果找到了，就属于已经实现的 `wontfix`（步骤 5）。(b) **此前已拒绝**——读取 `.out-of-scope/*.md`，并指出任何与当前请求相似的内容。

2. **给出建议。** 告诉 maintainer 你建议的类别和状态，并说明理由；同时提供与请求相关的简短代码库摘要，包括它是否已经实现。等待指示。

3. **验证主张。** 在任何追问开始前，先检查主张是否成立。对于 bug，按 reporter 提供的步骤复现。对于 PR，确认 diff 确实实现了它声称的内容——checkout 后运行相关 tests 或 commands。报告结果：已确认（附代码路径）、失败，或细节不足（这是强烈的 `needs-info` 信号）。经过确认的验证会让 agent brief 更有力。

4. **追问（如需要）。** 如果请求需要进一步明确，就调用 Skill tool 两次，分别传入 “grilling” 和 “domain-modeling”——每轮提出一组问题，逐步将请求打磨成形；随着决策落定，精化领域术语，并内联更新 `CONTEXT.md`/ADRs。

5. **应用结果：**
   - `ready-for-agent`——发布一条 agent brief 评论（[AGENT-BRIEF.md](AGENT-BRIEF.md)）。
   - `ready-for-human`——使用与 agent brief 相同的结构，但注明无法委托的原因（需要判断、外部访问、设计决策、手动测试）。
   - `needs-info`——发布 triage notes（模板见下文）。
   - `wontfix`——关闭，评论内容取决于其_原因_：
     - **已经实现**——该变更已经存在于代码库中。指出它所在的位置；**不要**写入 `.out-of-scope/`（该知识库用于记录_已拒绝_的请求，而不是已经构建的内容）。
     - **已拒绝（bug）**——礼貌说明，然后关闭。
     - **已拒绝（enhancement）**——写入 `.out-of-scope/`，从评论中链接该文件，然后关闭（[OUT-OF-SCOPE.md](OUT-OF-SCOPE.md)）。
   - `needs-triage`——应用该 role。如果已有部分进展，可以选择添加评论。

## 快速覆盖状态

如果 maintainer 说“把 #42 移到 ready-for-agent”，就相信他们并直接应用该 role。先确认即将执行的操作（role 变更、评论、关闭），然后行动。跳过追问。如果在没有进行追问会话的情况下移到 `ready-for-agent`，询问他们是否想编写 agent brief。

## `needs-info` 模板

```markdown
## 分诊记录

**目前已经确认的内容：**

- 要点 1
- 要点 2

**我们仍需要你（@reporter）提供：**

- 问题 1
- 问题 2
```

把追问期间已经解决的一切记录在“目前已经确认的内容”下，避免丢失这些工作。问题必须具体且可操作，不能只是“请提供更多信息”。

## 恢复此前的会话

如果 issue 或 PR 中已有 triage notes，先阅读它们，检查 reporter 是否回答了任何待解决问题，并在继续前展示更新后的整体情况。不要重复询问已经解决的问题。
