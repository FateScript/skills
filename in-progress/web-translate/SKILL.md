---
name: web-translate
description: 沉浸式翻译网页。当用户要求翻译网页、把网页翻译成中文、生成上原文下译文的中英对照页面，或给出 URL 要求「沉浸式翻译」时使用。禁止调用任何翻译 API，用模型自身能力翻译。
---

将网页逐字逐句翻译成中文，嵌入原网页，上原文下译文（沉浸式翻译效果）。不使用任何翻译 API。

两种交付方式：kimi-webbridge 原地注入（保留原页面排版与交互，默认）和静态 HTML 文件（用户要可保存的文件时）。主流程相同，只是解析和注入的环境不同。

## 主流程（kimi-webbridge 原地注入）

核心脚本在 `scripts/translate-inject.js`（提取 + 注入 + LaTeX 修复三合一，`__TR__` 为译文占位符）。首次提取时不带 TR 运行拿块列表，注入时把 TR 替换为译文 JSON 再运行。

1. **打开页面**：`kimi-webbridge status` 确认 `running` 和 `extension_connected` 均为 true；用独立 session（如 `web-translate`）`navigate` 打开目标页（`newTab: true`）。
2. **DOM 解析 + 内容区识别**：按站点确定正文容器，运行脚本的提取段。遍历 `h2,h3,h4,p,li`，克隆剔除 `.mw-editsection, sup.reference, style, script` 等噪声后取 textContent，归一化空白，每块打 `data-trid="b0..bN"`（顺序确定，重跑 id 不变）。完成标准：返回块列表，抽查块文本无 `[edit]`、引用上标等噪声。
3. **分段翻译**：块列表落盘为 JSON（如 `/tmp/<task>/blocks.json`），按约 3500 字符切块，每块派一个子代理并行翻译。给子代理的要求：禁止翻译 API，逐字逐句完整翻译，术语全块统一并列明关键术语表，专名保留原文可附中文，LaTeX 源码原样保留不译，不增删内容。完成标准：每个 `{id: 译文}` JSON 通过 id 集合校验（与输入完全一致，一个不能少）。
4. **插回 DOM**：把全部译文合并为 TR 替换进脚本，`evaluate` 执行；译文以 `<div class="zh-tr">`（绿色、较小字号）插到对应块之后。脚本可重入，重复执行会跳过已注入的块。完成标准：返回 `injected` 数等于块数。
5. **截图验证**：`scripts/screenshot.sh -s <session>`（kimi-webbridge skill 目录下）。新版 daemon 直接保存文件并在 `.data.path` 返回路径，若 helper 脚本解析报错，直接读该路径。滚动到公式、列表区域各截一张。完成标准：截图显示上原文下绿色译文，公式为渲染形态而非源码。

## LaTeX 渲染（Wikipedia 等含公式页面）

译文里的 LaTeX 源码片段必须替换为原文对应位置**已渲染的 `.mwe-math-element` 克隆节点**（脚本第 2、3 段已实现）：

- 匹配只用归一化空白后的 `indexOf`：先试元素完整 textContent（字形 + 注解），再试 `<annotation>` 的 LaTeX 源码；按公式长度降序匹配，防长式被短式截断。
- 替换后清理公式克隆前的残留字形噪声（如 `w ~ i`），判定为「单字符 token 序列」。

**禁用宽松空白正则做匹配**——长公式会触发灾难性回溯，卡死页面 JS 线程，只能刷新页面、译文全丢。

## 坑与要点

- 译文只存在于当前标签页的 DOM，刷新即失。务必把 blocks 和译文 JSON 落盘 `/tmp`，刷新后重跑三合一脚本即可一键重建（id 由提取顺序决定，与已存译文对得上）。
- 所有调 daemon 的 curl 都加 `--max-time`，页面卡死时避免无限挂起。
- 单次 `evaluate` 的代码载荷控制在几十 KB 内；译文很大时分批注入（每批 ≤ 20 块）。
- 静态 HTML 交付：curl 抓页面 → 用 bs4 走同样的提取/注入逻辑 → 输出单个 HTML，img src 和 a href 转绝对 URL（`//` 加 `https:`，`/` 加源站域名），去掉 srcset。
