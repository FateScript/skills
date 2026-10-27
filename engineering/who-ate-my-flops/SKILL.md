---
name: who-ate-my-flops
description: 诊断和优化单节点 PyTorch 训练或推理任务的端到端性能。用于分析 GPU 利用率、torch.profiler trace、计算与通信瓶颈，或在正确性约束下进行多轮性能优化；不替代一般功能 bug 排查。
---

# PyTorch 性能诊断与优化

将一个可重复运行的任务变成可测量、可验证的优化流程。根据用户目标选择下面的流程，只读取当前需要的文件。向用户解释和交付时沿用用户的语言；内部流程与模板保留上游英文。

## 选择流程

用户可输入 `$who-ate-my-flops init`、`$who-ate-my-flops diagnose` 或 `$who-ate-my-flops optimize`；这些是同一 skill 的模式，不是插件命名空间命令。

| 用户目标或当前步骤 | 读取文件 |
| --- | --- |
| 首次设置任务、缺少已确认的 contract | [init](references/init.md) |
| 一次诊断、一个主要瓶颈和实测修复 | [diagnose](references/diagnose.md) |
| 已授权持续优化，直到交付优化分支 | [optimize](references/optimize.md) |
| 建立独立 worktree、性能与正确性基线 | [setup-baseline](references/setup-baseline.md) |
| 采集或分析 trace，生成五种视图和诊断 | [torch-profile](references/torch-profile.md) |
| 从源码提取计算图及执行调度，不运行任务 | [extract-computation-graph](references/extract-computation-graph.md) |
| 将真实启动脚本转换为可重复 benchmark | [convert-to-benchmark-script](references/convert-to-benchmark-script.md) |
| 整理已完成的优化，复验并交付分支 | [clean-up](references/clean-up.md) |
| 为已交付结果生成本地 PR 和 issue 草稿 | [publish-pr](references/publish-pr.md) |

内部流程提到另一个 skill 时，读取上表对应文件并执行，不依赖其他同名 skill 的安装或自动发现。`diagnose` 引用的优化取舍见 `optimize.md` 的 Tradeoffs 部分，读取该部分不代表启动多轮优化。

## 运行约定

- `<skill root>` 是本文件所在目录，解析软链接后用绝对路径调用资源；不是目标项目目录。`<ws>` 是目标 worktree 中的 `workspace-who-ate-my-flops/`。
- 保留 `tools/` 和 `template/` 的相对布局。工作区工具用 `python "<skill root>/tools/workspace.py" ...`；trace 工具从 skill 根目录运行 `python -m tools.view ...`，传入绝对路径。
- 工具使用 Python 3.10+ 和标准库；`workspace.py` 依赖 Unix `fcntl`。实际采集、测量和正确性检查在任务自己的 PyTorch/GPU 环境中进行。
- 先从上下文确认仓库、启动命令、可用 GPU、允许的修改范围和正确性要求，只追问缺失信息。沿用已有授权，不重复确认已确定的约束；将结果写入 `contract.md`。
- `init` 完成配置，不自行开始实验。只有用户要求诊断或优化才进入相应流程。仅分析已有 trace 或读取计算图时，不要求先分配 GPU 或启动完整优化。
- benchmark 保持真实任务的模型、batch、序列长度、精度、并行方式与 world size；裁剪运行时长或数据时记录对测量范围的影响。
- 正确性容差由原始代码的重复运行确定，后续优化不得为通过检查而放宽。性能结论使用实测数据，明确区分耗时上限和已实现收益。
- `optimize` 在当前会话继续工作，并以 `workspace.py finish` 校验完成条件；遇到用户停止或无法恢复的资源阻塞，保留记录并说明恢复所需条件。
- `publish-pr` 只生成本地草稿。推送、发布 PR 或发送消息需要用户另行授权。

来源和迁移差异见 [CREDITS.md](CREDITS.md)。
