---
name: video-summary
description: 当用户提供 YouTube 或哔哩哔哩视频链接并要求总结、提取字幕或梳理内容时，使用 yt-dlp 直接获取已有字幕并生成中文总结；没有可用字幕时明确报告失败。
---

# 视频总结

## 目标与边界

这个 skill 只做一条可核验的链路：视频链接 → 平台已有字幕文件 → 字幕文本 → 中文总结。

- 支持 YouTube（`youtube.com`、`youtu.be`）和哔哩哔哩（`bilibili.com`、`b23.tv`）单个视频。
- 字幕可以是作者提供的字幕，也可以是平台提供的自动字幕；在结果中标明字幕语言和类型（人工/自动）。
- 内容依据字幕文本。字幕没有覆盖的画面、音乐、演示或评论，不作为事实写入总结。
- 字幕抓取失败、视频没有字幕、字幕文件为空或格式无法解析时，流程在这里结束并说明原因。此时请用户提供字幕文件或可访问的字幕链接，再继续总结。
- 运行过程中只请求字幕资源，不下载视频或音频，也不启动语音识别。

## 执行流程

### 1. 确认输入和依赖

从用户消息中取出视频 URL，确认它属于 YouTube 或哔哩哔哩。URL 含有播放参数时原样传给脚本；一次只处理一个视频。

先检查 `yt-dlp` 和 Python 3：

```bash
command -v yt-dlp
python3 --version
```

缺少 `yt-dlp` 时，报告安装方式（例如 `python3 -m pip install -U yt-dlp`），等待用户完成安装后再运行；不要把安装或凭据配置当作总结步骤。

### 2. 直接抓取字幕

使用随 skill 附带的脚本。将 `VIDEO_SUMMARY_SKILL_DIR` 替换为当前安装目录；常见位置是 `~/.codex/skills/video-summary` 或 `~/.claude/skills/video-summary`。

```bash
VIDEO_SUMMARY_SKILL_DIR="${VIDEO_SUMMARY_SKILL_DIR:-$HOME/.codex/skills/video-summary}"
if [ ! -f "$VIDEO_SUMMARY_SKILL_DIR/scripts/fetch_subtitles.py" ] && [ -f "$HOME/.claude/skills/video-summary/scripts/fetch_subtitles.py" ]; then
  VIDEO_SUMMARY_SKILL_DIR="$HOME/.claude/skills/video-summary"
fi
VIDEO_SUMMARY_OUT="$(mktemp -d "${TMPDIR:-/tmp}/video-summary.XXXXXX")"

python3 "$VIDEO_SUMMARY_SKILL_DIR/scripts/fetch_subtitles.py" \
  "<视频 URL>" \
  --output-dir "$VIDEO_SUMMARY_OUT" \
  --languages "zh-Hans,zh-Hant,zh-CN,zh-TW,zh,en"
```

脚本先尝试人工字幕，再尝试自动字幕；两种情况都使用 `yt-dlp --skip-download`，不会选择视频格式。成功时会在输出目录写入：

- `subtitle.srt`：保留时间戳的规范化字幕；
- `text.txt`：去掉时间戳、适合阅读和总结的纯文本；
- `metadata.json`：来源 URL、平台、语言、字幕类型、字幕文件和统计信息；
- `raw/`：实际抓到的字幕文件，便于复核。

默认语言优先中文，其次英文。用户指定其他语言时，把它们放在 `--languages` 的逗号分隔列表中；若明确接受视频的任意可用语言，可以使用 `--languages all`。脚本返回非零状态或 `cue_count` 为零时，按“失败协议”处理，不猜测视频内容。

### 3. 阅读和核对字幕

读取 `metadata.json`、`subtitle.srt` 和 `text.txt`。先确认：

1. `url` 与用户要求的视频一致；
2. `cue_count` 大于零，纯文本不是空白；
3. 字幕语言和 `subtitle_type` 已记录；
4. 时间戳顺序基本递增，明显重复的自动字幕只在不改变含义的范围内合并。

字幕是英文或其他语言时，直接用原文理解并用中文输出；专有名词首次出现时保留原文。不要把字幕中的猜测改写成确定事实。

### 4. 生成总结

短字幕可以直接总结。`text.txt` 较长时，按 `subtitle.srt` 的 cue 边界分成约 8,000–12,000 字的片段，先为每段提取要点和时间戳，再综合所有片段；不要在截断处切开句子。详细模板和检查项见 [references/summary-template.md](references/summary-template.md)。

总结至少包含：

- 一句话结论；
- 3–7 条关键要点；
- 按时间戳标注的内容结构或事件顺序；
- 重要事实、数据、定义或行动建议（能在字幕中定位）；
- 术语/人物/作品名（必要时附原文）；
- 字幕质量和不确定性说明，尤其是自动字幕听辨不清的地方。

事实与推断分开写。引用原话时保持原意，并在 SRT 中找到对应时间戳；没有字幕依据的内容标为“字幕未提及”，不补看似合理的细节。

## 输出格式

```markdown
# <视频标题或简短标识>

- 来源：<URL>
- 字幕：<语言>（<人工/自动>）

## 一句话结论
<一句话>

## 关键要点
1. ...
2. ...

## 内容结构
- [00:00:00] ...
- [00:05:30] ...

## 重要事实与术语
- ...

## 不确定性
- <字幕质量、缺失信息或无法从字幕判断的内容>
```

没有可靠标题时，用“视频总结”作为标题，并保留完整 URL。总结完成后告诉用户字幕文件和纯文本文件的路径，方便复核。

## 失败协议

遇到下列任一情况，返回简短、可操作的失败信息：

- URL 不是支持的平台；
- `yt-dlp` 未安装或版本过旧；
- 平台拒绝访问、视频私有/受限或网络请求超时；
- 人工字幕和自动字幕都不存在；
- 下载到的文件为空或格式无法解析。

失败信息应包含已完成的检查、脚本给出的核心错误和下一步选择（安装/更新 `yt-dlp`、调整语言列表、提供字幕文件或提供可访问链接）。失败时不生成“根据视频内容”的猜测性总结。
