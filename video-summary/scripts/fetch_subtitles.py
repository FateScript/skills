#!/usr/bin/env python3
"""只抓取 YouTube / 哔哩哔哩的已有字幕，不下载视频或音频。

脚本把 yt-dlp 下载的字幕规范化为 ``subtitle.srt`` 和 ``text.txt``，并
输出一份可供 agent 复核的 ``metadata.json``。它不包含语音识别回退路径：
找不到可解析字幕时以非零状态结束。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


DEFAULT_LANGUAGES = (
    "zh-Hans",
    "zh-Hant",
    "zh-CN",
    "zh-TW",
    "zh",
    "en",
)

SUPPORTED_EXTENSIONS = {
    ".ass",
    ".dfxp",
    ".json3",
    ".lrc",
    ".srv3",
    ".srt",
    ".ttml",
    ".vtt",
}

TIMING_ARROW_RE = re.compile(r"\s*-->\s*")
HTML_TAG_RE = re.compile(r"<[^>]*>")
VTT_TIMESTAMP_TAG_RE = re.compile(r"<(?:(?:\d{1,2}:)?\d{2}:\d{2}[\.,]\d{1,3})>")
ASS_OVERRIDE_RE = re.compile(r"\{[^}]*\}")
LRC_LINE_RE = re.compile(
    r"^\s*\[(?P<minutes>\d{1,3}):(?P<seconds>\d{2}(?:[\.,]\d{1,3})?)\]\s*(?P<text>.*)$"
)


class SubtitleError(RuntimeError):
    """可向用户展示的字幕获取/解析错误。"""


@dataclass(frozen=True)
class Cue:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class SubtitleCandidate:
    path: Path
    language: str


def platform_for_url(url: str) -> str:
    """返回 URL 所属平台，拒绝 skill 范围外的站点。"""

    value = url.strip()
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("请输入以 http:// 或 https:// 开头的视频 URL。")

    host = parsed.hostname.lower().rstrip(".")
    if host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com"):
        return "youtube"
    if host == "b23.tv" or host == "bilibili.com" or host.endswith(".bilibili.com"):
        return "bilibili"
    raise ValueError(
        "仅支持 YouTube（youtube.com/ youtu.be）和哔哩哔哩（bilibili.com/ b23.tv）视频。"
    )


def parse_languages(raw: str | Sequence[str] | None) -> list[str]:
    """解析逗号分隔的语言偏好，并保留用户给出的顺序。"""

    if raw is None:
        values: Iterable[str] = DEFAULT_LANGUAGES
    elif isinstance(raw, str):
        values = raw.split(",")
    else:
        values = raw

    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        language = str(item).strip()
        if not language or language in seen:
            continue
        result.append(language)
        seen.add(language)
    if not result:
        raise ValueError(
            "--languages 不能为空；可使用 --languages all 获取任意可用字幕。"
        )
    return result


def build_ytdlp_command(
    url: str,
    output_stem: Path,
    languages: Sequence[str],
    *,
    auto: bool = False,
    yt_dlp: str | Sequence[str] = "yt-dlp",
    socket_timeout: int = 30,
    extractor_args: str | None = None,
) -> list[str]:
    """构造只写字幕的 yt-dlp 命令。

    ``yt_dlp`` 可以是可执行文件路径，也可以是诸如
    ``[sys.executable, "-m", "yt_dlp"]`` 的命令前缀，便于测试和虚拟环境使用。
    """

    prefix = [yt_dlp] if isinstance(yt_dlp, str) else list(yt_dlp)
    if not prefix:
        raise ValueError("yt-dlp 命令不能为空。")

    command = [
        *prefix,
        "--no-update",
        "--ignore-config",
        "--no-playlist",
        "--ignore-no-formats-error",
        "--skip-download",
        "--no-warnings",
        "--retries",
        "2",
        "--socket-timeout",
        str(max(1, int(socket_timeout))),
        "--sub-format",
        "vtt/srt/best",
        "--sub-langs",
        ",".join(languages),
        "--output",
        str(output_stem),
    ]
    if extractor_args:
        command.extend(["--extractor-args", extractor_args])
    if auto:
        command.extend(["--no-write-subs", "--write-auto-subs"])
    else:
        command.extend(["--write-subs", "--no-write-auto-subs"])
    command.append(url)
    return command


def clean_caption_text(value: str) -> str:
    """移除字幕标记并规范空白，保留可读的文字内容。"""

    text = value.replace("\ufeff", "")
    text = (
        text.replace("\\N", " ")
        .replace("\\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )
    text = VTT_TIMESTAMP_TAG_RE.sub("", text)
    text = ASS_OVERRIDE_RE.sub("", text)
    text = HTML_TAG_RE.sub("", text)
    text = html.unescape(text)
    # 零宽字符会让相邻 cue 看起来不同，先统一移除。
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    return " ".join(text.split()).strip()


def parse_timestamp(value: str) -> int:
    """将 VTT/SRT/TTML 常见时间格式转换为毫秒。"""

    token = value.strip().split()[0]
    token = token.replace(",", ".")
    parts = token.split(":")
    if len(parts) == 3:
        hours_text, minutes_text, seconds_text = parts
    elif len(parts) == 2:
        hours_text = "0"
        minutes_text, seconds_text = parts
    else:
        raise ValueError(f"无法解析字幕时间戳：{value!r}")

    try:
        hours = int(hours_text)
        minutes = int(minutes_text)
        seconds = float(seconds_text)
    except ValueError as exc:
        raise ValueError(f"无法解析字幕时间戳：{value!r}") from exc
    if hours < 0 or minutes < 0 or seconds < 0 or minutes >= 60 or seconds >= 60:
        raise ValueError(f"字幕时间戳超出范围：{value!r}")
    return max(0, round((hours * 3600 + minutes * 60 + seconds) * 1000))


def format_srt_timestamp(milliseconds: int) -> str:
    total_ms = max(0, int(milliseconds))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _deduplicate_cues(cues: Iterable[Cue]) -> list[Cue]:
    """去除相邻且完全相同的 cue，避免自动字幕重复堆叠。"""

    result: list[Cue] = []
    for cue in cues:
        if not cue.text:
            continue
        if result and result[-1].text == cue.text:
            # 保留更长的时间范围，仍然不改变字幕文字。
            previous = result[-1]
            result[-1] = Cue(
                start_ms=min(previous.start_ms, cue.start_ms),
                end_ms=max(previous.end_ms, cue.end_ms),
                text=previous.text,
            )
            continue
        result.append(cue)
    return result


def _parse_arrow_cues(content: str) -> list[Cue]:
    """解析 VTT/SRT 这类带 ``-->`` 时间轴的字幕。"""

    lines = content.lstrip("\ufeff").splitlines()
    cues: list[Cue] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if "-->" not in line:
            index += 1
            continue

        left, right = TIMING_ARROW_RE.split(line, maxsplit=1)
        try:
            start_ms = parse_timestamp(left)
            end_ms = parse_timestamp(right)
        except ValueError:
            index += 1
            continue

        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            # NOTE/STYLE/REGION blocks are handled before a timing line; once a
            # cue has started, a line beginning with those words is ordinary
            # caption text and must be preserved.
            text_lines.append(lines[index].strip())
            index += 1
        text = clean_caption_text(" ".join(text_lines))
        if text:
            cues.append(Cue(start_ms=start_ms, end_ms=max(start_ms, end_ms), text=text))
        index += 1
    return _deduplicate_cues(cues)


def parse_vtt(content: str) -> list[Cue]:
    return _parse_arrow_cues(content)


def parse_srt(content: str) -> list[Cue]:
    return _parse_arrow_cues(content)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _xml_time_to_ms(value: str) -> int:
    token = value.strip()
    if token.endswith("ms"):
        return round(float(token[:-2]))
    if token.endswith("s") and ":" not in token:
        return round(float(token[:-1]) * 1000)
    if ":" in token:
        return parse_timestamp(token)
    # TTML 允许纯数字秒数。
    return round(float(token) * 1000)


def parse_xml_subtitles(content: str) -> list[Cue]:
    """解析 TTML/DFXP/SRV3 的 ``p`` 或 ``text`` 元素。"""

    try:
        root = ET.fromstring(content.lstrip("\ufeff"))
    except ET.ParseError:
        return []

    cues: list[Cue] = []
    for element in root.iter():
        if _local_name(element.tag) not in {"p", "text"}:
            continue
        begin = element.attrib.get("begin") or element.attrib.get("start")
        end = element.attrib.get("end")
        duration = element.attrib.get("dur")
        duration_ms_attribute = element.attrib.get("dDurationMs")
        if not begin:
            continue
        try:
            start_ms = _xml_time_to_ms(begin)
            if end:
                end_ms = _xml_time_to_ms(end)
            elif duration:
                end_ms = start_ms + _xml_time_to_ms(duration)
            elif duration_ms_attribute:
                end_ms = start_ms + round(float(duration_ms_attribute))
            else:
                end_ms = start_ms + 1000
        except (TypeError, ValueError):
            continue
        text = clean_caption_text(" ".join(element.itertext()))
        if text:
            cues.append(Cue(start_ms=start_ms, end_ms=max(start_ms, end_ms), text=text))
    return _deduplicate_cues(cues)


def parse_json3(content: str) -> list[Cue]:
    """解析 YouTube 常见的 json3 字幕格式。"""

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return []
    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        return []

    cues: list[Cue] = []
    for event in events:
        if not isinstance(event, dict) or "tStartMs" not in event:
            continue
        segments = event.get("segs")
        if not isinstance(segments, list):
            continue
        text_parts = [
            str(segment.get("utf8", ""))
            for segment in segments
            if isinstance(segment, dict) and segment.get("utf8") is not None
        ]
        text = clean_caption_text("".join(text_parts))
        if not text:
            continue
        try:
            start_ms = int(float(event.get("tStartMs", 0)))
            duration_ms = int(float(event.get("dDurationMs", 1000)))
        except (TypeError, ValueError):
            continue
        cues.append(
            Cue(
                start_ms=max(0, start_ms),
                end_ms=max(0, start_ms + duration_ms),
                text=text,
            )
        )
    return _deduplicate_cues(cues)


def parse_lrc(content: str) -> list[Cue]:
    """解析简单 LRC 歌词时间轴；没有结束时间时使用下一行开始时间。"""

    timed: list[tuple[int, str]] = []
    for line in content.splitlines():
        match = LRC_LINE_RE.match(line)
        if not match:
            continue
        try:
            start_ms = round(
                (
                    int(match.group("minutes")) * 60
                    + float(match.group("seconds").replace(",", "."))
                )
                * 1000
            )
        except ValueError:
            continue
        text = clean_caption_text(match.group("text"))
        if text:
            timed.append((start_ms, text))

    cues: list[Cue] = []
    for index, (start_ms, text) in enumerate(timed):
        next_start = timed[index + 1][0] if index + 1 < len(timed) else start_ms + 5000
        cues.append(Cue(start_ms=start_ms, end_ms=max(start_ms, next_start), text=text))
    return _deduplicate_cues(cues)


def parse_ass(content: str) -> list[Cue]:
    """解析 ASS/SSA Events 段落中的 Dialogue 行。"""

    cues: list[Cue] = []
    in_events = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.lower() == "[events]":
            in_events = True
            continue
        if line.startswith("[") and line.endswith("]") and line.lower() != "[events]":
            in_events = False
        if not in_events or not line.lower().startswith("dialogue:"):
            continue
        fields = line.split(":", 1)[1].lstrip().split(",", 9)
        if len(fields) < 10:
            continue
        try:
            start_ms = parse_timestamp(fields[1])
            end_ms = parse_timestamp(fields[2])
        except ValueError:
            continue
        text = clean_caption_text(fields[9])
        if text:
            cues.append(Cue(start_ms=start_ms, end_ms=max(start_ms, end_ms), text=text))
    return _deduplicate_cues(cues)


def parse_subtitle_content(content: str, suffix: str = "") -> list[Cue]:
    """按扩展名解析字幕；未知扩展名会依次尝试常见格式。"""

    extension = suffix.lower()
    if not extension.startswith("."):
        extension = "." + extension if extension else ""
    if extension == ".json3":
        cues = parse_json3(content)
    elif extension in {".ttml", ".dfxp", ".srv3"}:
        cues = parse_xml_subtitles(content)
    elif extension == ".lrc":
        cues = parse_lrc(content)
    elif extension == ".ass":
        cues = parse_ass(content)
    else:
        cues = _parse_arrow_cues(content)

    if cues:
        return cues
    # 某些站点的扩展名不稳定；内容探测只用于解析，不会触发任何回退下载。
    for parser in (
        parse_json3,
        parse_xml_subtitles,
        _parse_arrow_cues,
        parse_lrc,
        parse_ass,
    ):
        try:
            fallback = parser(content)
        except (TypeError, ValueError, ET.ParseError):
            continue
        if fallback:
            return fallback
    return []


def parse_subtitle_file(path: Path) -> list[Cue]:
    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8", errors="replace")
    return parse_subtitle_content(content, path.suffix)


def subtitle_language(path: Path, output_stem: Path | None = None) -> str:
    """从 yt-dlp 的 ``subtitle.<language>.<ext>`` 文件名提取语言。"""

    name = path.name
    stem_name = output_stem.name if output_stem else "subtitle"
    prefix = stem_name + "."
    if name.startswith(prefix):
        remainder = name[len(prefix) :]
        if "." in remainder:
            return remainder.rsplit(".", 1)[0]
    if name == stem_name + path.suffix:
        return "unknown"
    return "unknown"


def _normalize_language(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def language_score(language: str, preferences: Sequence[str]) -> tuple[int, int]:
    """返回语言排序分数；越小越优先。"""

    candidate = _normalize_language(language)
    for index, preference in enumerate(preferences):
        wanted = _normalize_language(preference)
        if wanted == "all":
            return (0, index)
        if candidate == wanted:
            return (index, 0)
        candidate_base = candidate.split("-", 1)[0]
        wanted_base = wanted.split("-", 1)[0]
        if candidate_base and candidate_base == wanted_base:
            return (index, 1)
        if candidate.startswith(wanted + "-") or wanted.startswith(candidate + "-"):
            return (index, 2)
    return (len(preferences) + 1, 9)


def find_subtitle_files(
    raw_dir: Path, output_stem: Path | None = None
) -> list[SubtitleCandidate]:
    stem_name = output_stem.name if output_stem else "subtitle"
    candidates: list[SubtitleCandidate] = []
    for path in sorted(raw_dir.glob(stem_name + ".*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        candidates.append(
            SubtitleCandidate(path=path, language=subtitle_language(path, output_stem))
        )
    return candidates


def select_subtitle_files(
    candidates: Sequence[SubtitleCandidate], preferences: Sequence[str]
) -> list[SubtitleCandidate]:
    extension_order = {
        ".vtt": 0,
        ".srt": 1,
        ".json3": 2,
        ".ttml": 3,
        ".dfxp": 3,
        ".srv3": 4,
        ".ass": 5,
        ".lrc": 6,
    }
    return sorted(
        candidates,
        key=lambda candidate: (
            language_score(candidate.language, preferences),
            extension_order.get(candidate.path.suffix.lower(), 99),
            candidate.path.name,
        ),
    )


def _clear_generated_files(raw_dir: Path, output_stem: Path) -> None:
    prefix = output_stem.name + "."
    for path in raw_dir.iterdir() if raw_dir.exists() else ():
        if (
            path.is_file()
            and path.name.startswith(prefix)
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ):
            path.unlink()


def _clear_output_files(output_dir: Path) -> None:
    """移除本次流程会生成的固定文件，避免失败时误读上一次结果。"""

    for name in ("subtitle.srt", "text.txt", "metadata.json"):
        path = output_dir / name
        if path.is_file():
            path.unlink()


def _resolve_ytdlp(explicit: str | None) -> list[str]:
    if explicit:
        return [explicit]
    executable = shutil.which("yt-dlp")
    if executable:
        return [executable]
    # 允许只安装了 Python 包的环境。
    try:
        import importlib.util

        if importlib.util.find_spec("yt_dlp") is not None:
            return [sys.executable, "-m", "yt_dlp"]
    except (ImportError, ModuleNotFoundError):
        pass
    raise SubtitleError("找不到 yt-dlp。请先运行 `python3 -m pip install -U yt-dlp`。")


def _run_ytdlp(
    command: Sequence[str], timeout: int
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout)),
        )
    except FileNotFoundError as exc:
        raise SubtitleError(
            "找不到 yt-dlp 可执行文件。请先安装或通过 --yt-dlp 指定路径。"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SubtitleError(f"字幕请求超过 {timeout} 秒仍未完成，已停止。") from exc


def _short_process_error(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stderr or result.stdout or "").strip()
    if len(text) > 1800:
        text = text[-1800:]
    return text


def _write_outputs(
    cues: Sequence[Cue],
    output_dir: Path,
    *,
    url: str,
    platform: str,
    language: str,
    subtitle_type: str,
    source_path: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    srt_path = output_dir / "subtitle.srt"
    text_path = output_dir / "text.txt"
    metadata_path = output_dir / "metadata.json"

    srt_content = "".join(
        f"{index}\n{format_srt_timestamp(cue.start_ms)} --> {format_srt_timestamp(cue.end_ms)}\n{cue.text}\n\n"
        for index, cue in enumerate(cues, start=1)
    )
    text_content = " ".join(cue.text for cue in cues)
    if text_content:
        text_content += "\n"
    srt_path.write_text(srt_content, encoding="utf-8")
    text_path.write_text(text_content, encoding="utf-8")

    result: dict[str, Any] = {
        "url": url,
        "platform": platform,
        "language": language,
        "subtitle_type": subtitle_type,
        "source_path": str(source_path),
        "srt_path": str(srt_path),
        "text_path": str(text_path),
        "metadata_path": str(metadata_path),
        "cue_count": len(cues),
        "char_count": len(text_content.rstrip("\n")),
    }
    metadata_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def fetch_subtitles(
    url: str,
    output_dir: Path,
    languages: Sequence[str] | None = None,
    *,
    yt_dlp: str | Sequence[str] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    """抓取并规范化字幕；没有可解析字幕时抛出 ``SubtitleError``。"""

    platform = platform_for_url(url)
    preferences = parse_languages(languages)
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _clear_output_files(output_dir)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_stem = raw_dir / "subtitle"
    command_prefix = (
        _resolve_ytdlp(yt_dlp if isinstance(yt_dlp, str) else None)
        if yt_dlp is None or isinstance(yt_dlp, str)
        else list(yt_dlp)
    )

    errors: list[str] = []
    # YouTube 的部分客户端会因 PO token 限制看不到字幕；先走默认客户端，
    # 再用只取元数据/字幕的 Android 客户端重试。B 站不需要这个变体。
    extractor_variants: list[str | None] = [None]
    if platform == "youtube":
        extractor_variants.append("youtube:player_client=android")

    # 人工字幕优先；只有没有可解析文件时才请求自动字幕。
    for auto, subtitle_type in ((False, "manual"), (True, "auto")):
        for extractor_args in extractor_variants:
            _clear_generated_files(raw_dir, output_stem)
            command = build_ytdlp_command(
                url,
                output_stem,
                preferences,
                auto=auto,
                yt_dlp=command_prefix,
                extractor_args=extractor_args,
            )
            process = _run_ytdlp(command, timeout)
            candidates = select_subtitle_files(
                find_subtitle_files(raw_dir, output_stem), preferences
            )
            variant_label = f"（{extractor_args}）" if extractor_args else ""
            if not candidates:
                detail = _short_process_error(process)
                if detail:
                    errors.append(f"{subtitle_type}{variant_label} 字幕：{detail}")
                elif process.returncode:
                    errors.append(
                        f"{subtitle_type}{variant_label} 字幕请求返回状态 {process.returncode}"
                    )
                continue

            parse_errors: list[str] = []
            for candidate in candidates:
                cues = parse_subtitle_file(candidate.path)
                if not cues:
                    parse_errors.append(candidate.path.name)
                    continue
                result = _write_outputs(
                    cues,
                    output_dir,
                    url=url,
                    platform=platform,
                    language=candidate.language,
                    subtitle_type=subtitle_type,
                    source_path=candidate.path,
                )
                # 记录命令是否带来非零警告，但只要字幕有效就视为成功。
                if process.returncode:
                    result["yt_dlp_returncode"] = process.returncode
                    metadata_path = Path(result["metadata_path"])
                    metadata_path.write_text(
                        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                return result
            if parse_errors:
                errors.append(
                    f"{subtitle_type}{variant_label} 字幕文件无法解析：{', '.join(parse_errors)}"
                )

    detail = "; ".join(errors)
    message = "人工字幕和自动字幕都没有得到可解析的字幕文件。"
    if detail:
        message += f" yt-dlp 信息：{detail}"
    raise SubtitleError(message)


def default_output_dir(url: str) -> Path:
    # 用短哈希隔离不同 URL，避免复用旧字幕；不把 URL 原文写入临时路径。
    import hashlib

    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / "video-summary" / digest


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="只获取 YouTube/哔哩哔哩已有字幕并生成 SRT/纯文本文件。",
    )
    parser.add_argument("url", help="YouTube 或哔哩哔哩视频 URL。")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="输出目录；默认使用系统临时目录下按 URL 隔离的目录。",
    )
    parser.add_argument(
        "--languages",
        default=",".join(DEFAULT_LANGUAGES),
        help="逗号分隔的语言偏好，例如 zh-Hans,zh,en；使用 all 接受任意语言。",
    )
    parser.add_argument(
        "--yt-dlp",
        default=None,
        help="yt-dlp 可执行文件路径；省略时从 PATH 或 Python 模块中查找。",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="每次字幕请求的最长秒数（默认 180）。",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else default_output_dir(args.url)
    )
    try:
        result = fetch_subtitles(
            args.url,
            output_dir,
            parse_languages(args.languages),
            yt_dlp=args.yt_dlp,
            timeout=args.timeout,
        )
    except (SubtitleError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
