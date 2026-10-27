# 来源与迁移

- 上游：[OpenPerfAgent/who-ate-my-flops](https://github.com/OpenPerfAgent/who-ate-my-flops)
- 固定版本：`20577a5af7c9be58cbca61a131222f781b8745a7`，插件版本 `0.1.0`。
- 迁移日期：2026-10-26。
- Copyright © 2026 Impossible, Inc.；保留完整 [Apache-2.0 许可证](LICENSE)。

本地采用一个中文 skill 入口，将上游 9 个 SKILL.md 正文保留为按需读取的英文流程。工具和模板原样保留，未携带插件市场清单或演示媒体；通过本仓库 `link-skill.sh` 发现和链接。

修改点：路径以本 skill 根目录为准；原插件命令改为单一 skill 的模式；内部 skill 引用改由入口映射解析；移除 Claude 专属定时器和未安装的 humanizer 依赖；沿用当前会话持续执行的机制；trace 命令从 skill 根目录运行以避免目标仓库的同名模块冲突；交付时使用独立基线 worktree 进行 A/B 测量，避免覆盖交付源码。中文入口补充按需执行、已有授权和运行环境的边界。
