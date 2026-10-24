---
name: implement-spec
description: "在一条集成分支上实现 /to-spec 与 /to-tickets 产出的完整规格。"
disable-model-invocation: true
---

用户已提供 spec；它应有关联 tickets，描述如何实现。issue tracker 应已配置；如果没有，告知用户运行 `/setup-matt-pocock-skills`。

目标是在一条**集成分支**上实现整个 spec，并按照 tracker 的工作流关闭每张 ticket。Tickets 是带阻塞关系的**任务图**，不是步骤清单；其中总有一组可立即处理的**前沿** tickets。

与子代理尽量通过 spec、tickets、研究笔记和先前 commit 的**上下文指针**沟通，不重复可通过指针读取的内容。条件允许时，在后台运行实现子代理，以提高并发。

## 步骤

1. 阅读 spec 和 tickets，理解任务图。
2. 如有必要，派探索子代理调查相关代码或外部资料。让它把 Markdown 笔记保存在仓库外、后续子代理都能读取的位置，供实现子代理使用。
3. 创建集成分支。如果 tracker 通过 PR 关闭工作，或用户要求 PR，在步骤 5 首次合并后打开草稿 PR，标明它会关闭哪些 spec 和 tickets；分支尚未领先 main 时不能打开 PR。
4. 为每张可处理 ticket 派一个实现子代理，在独立 worktree 和分支上工作。每个子代理开始前确认 worktree 基于集成分支；如果不是，先重置到该分支。调用 `tdd` skill 实现 ticket；完成前将集成分支最新提交合入自己的分支。
5. 实现子代理完成后，派合并子代理将其工作合入集成分支。
6. 如果前沿因此变化，继续启动新出现的可处理 tickets。
7. 所有 tickets 完成后，对集成分支调用 `code-review` skill；派一个实现子代理修复审查发现的全部问题。
8. 如果有草稿 PR，将其标记为可审查；否则按 tracker 工作流关闭每张 ticket，并报告集成分支。
9. 清理所有实现子代理的 worktree。
