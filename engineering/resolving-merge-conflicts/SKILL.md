---
name: resolving-merge-conflicts
description: "当你需要解决正在进行中的 git merge/rebase 冲突时使用。"
---

1. **查看 merge/rebase 的当前状态。** 检查 git 历史和发生冲突的文件。

2. **找到每处冲突的一手资料。** 深入理解每项改动为何产生，以及它原本的意图。阅读 commit messages，查看 PR，并检查最初的 issues/tickets。

3. **解决每个 hunk。** 尽可能保留双方意图。如果二者不兼容，选择符合此次 merge 明确目标的一方，并说明取舍。**不要**发明新行为。必须解决冲突，绝不使用 `--abort`。

4. 找出项目的**自动化检查**并运行它们——通常依次为 typecheck、tests、format。修复 merge 导致的任何问题。

5. **完成 merge/rebase。** Stage 所有内容并 commit。如果正在 rebase，继续 rebase 流程，直到所有 commits 都完成 rebase。
