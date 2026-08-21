---
name: wizard
description: 生成一个交互式 bash wizard，引导人类完成只有他们才能执行的步骤。当需要配置基础设施、设置凭据或 CI secrets、引导用户操作陌生的第三方 dashboard，或执行一次性 migration/cutover 时使用。不要为 agent 自己能够执行的步骤调用此 skill。
---

# 配置向导

**Wizard** 是一个 bash 脚本，它会一步步引导人类完成某项手工流程；这种流程如果完全靠手做很繁琐，每次都重新向 AI 解释也同样繁琐。它会打开每个 URL，准确说明要点击和复制什么，捕获这些值并写入正确位置（`.env`、GitHub secrets），在每个阶段进行确认，并显示还剩多少阶段。它可以配置第三方服务、运行一次性 migration，或把项目从一种状态迁移到另一种状态。

令人愉快的 UX 已由 [template.sh](template.sh) 解决——逐阶段进度、确认关卡、跨平台 URL 打开（包括 WSL）、隐藏式 secret 输入、幂等的 `.env` upserts、`gh secret`/`gh variable` 写入，以及收尾摘要。**你的工作只是界定流程范围并编写各阶段。** `STAGES` 标记上方的库代码在每个 wizard 中都完全相同；一致性正是重点——绝不要手工编辑它。

Wizard 默认是临时性的——为一次运行而构建，保存在 scratch 或 `scripts/` 路径中，任务完成后删除。只有当用户希望提供一条可重复、应长期保存在仓库中的设置路径时，才 commit 它。

## 流程

### 1. 界定流程范围

梳理人类必须执行的每一个手工步骤，以及在过程中要捕获的每一个值。先阅读仓库——不要毫无准备就提问：

- 对于 setup：检查 `.env`、`.env.example`、`.env.*`、`README`、`docker-compose*`、framework config 和 `.github/workflows/*`（其中每一个 `secrets.*` / `vars.*` 引用都是 wizard 必须产出的值）。
- 对于 migration 或 transition：检查当前状态、目标状态，以及二者之间不可逆的操作。

然后向用户展示按顺序排列的阶段列表及每个阶段产出的值，并请其确认——他们可能会添加、删除或重排阶段。

**完成条件：** 每个阶段都已按顺序命名；对于每个捕获的值，你都知道：(a) 人类从哪里取得它，(b) 它会写到哪里（`.env`、GitHub secret、二者皆是，或任何地方都不写——有些阶段只有操作），以及 (c) 它是否为 secret（隐藏式输入）或公开值。

### 2. 绘制每个阶段的操作路径

为每个阶段写出人类遵循的精确路径：打开哪个 URL、在那里做什么、值显示在哪里、它会填充哪个变量。例如：“Dashboard → Developers → API keys → Reveal test key → copy”。如果你并不知道当前 UI 或确切命令，就如实说明，并询问用户或查阅文档——绝不要虚构可能并不存在的步骤。

**完成条件：** 每个阶段都落实为陌生人也能照着完成的具体说明。

### 3. 编写向导

把 `template.sh` 复制到目标路径。用按依赖顺序排列的阶段替换示例阶段，每一步对应一个 `stage`。使用库 helpers——`stage`、`say`/`step`、`open_url`、`ask`/`ask_secret`、`write_env`、`set_secret`/`set_var`、`pause`/`confirm`——并将 `TOTAL_STAGES` 设置为所编写阶段的数量。

保持模板设定的标准：先打开 URL，再询问其中的值；任何 secret 都使用 `ask_secret`；每个需要持久化的值都使用 `write_env`；只对 CI 实际需要的值使用 `set_secret`；执行任何不可逆操作前先 `confirm`。每个 `stage` 都会清屏，只显示当前步骤——每个阶段只放一个专注任务，避免人类需要查看的内容滚出屏幕。不要修改标记上方的库代码。

### 4. 验证并交接

- 运行 `bash -n <script>`；如果有 `shellcheck`，也运行它。
- 运行 `chmod +x <script>`。
- 不要自行端到端运行——它会打开浏览器并阻塞等待人类输入。改为静态追踪：步骤 1 中的每个值都被捕获并落到步骤 1 指定的位置，每个 `set_secret` 名称都与 CI 中某个 `secrets.*` 引用完全匹配。
- 告诉用户如何运行它。如果它是一条可重复的 setup 路径，就 commit 它，并从 README 链接过去，让下一位使用者直接运行脚本，而不是询问 AI。
