from __future__ import annotations

import importlib.util
import json
import stat
import sys
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "fetch_subtitles.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "video_summary_fetch_subtitles", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SubtitleParserTests(unittest.TestCase):
    def test_platform_and_command_are_restricted_to_subtitles(self):
        module = load_module()
        self.assertEqual(module.platform_for_url("https://youtu.be/abc123"), "youtube")
        self.assertEqual(
            module.platform_for_url("https://www.bilibili.com/video/BV1xx"), "bilibili"
        )
        with self.assertRaises(ValueError):
            module.platform_for_url("https://example.com/video")

        command = module.build_ytdlp_command(
            "https://www.youtube.com/watch?v=abc123",
            Path("/tmp/video-summary/raw/subtitle"),
            ["zh-Hans", "en"],
        )
        self.assertIn("--skip-download", command)
        self.assertIn("--write-subs", command)
        self.assertIn("--no-write-auto-subs", command)
        self.assertIn("--no-playlist", command)
        self.assertNotIn("--format", command)
        self.assertNotIn("-f", command)

        auto_command = module.build_ytdlp_command(
            "https://www.youtube.com/watch?v=abc123",
            Path("/tmp/video-summary/raw/subtitle"),
            ["all"],
            auto=True,
        )
        self.assertIn("--write-auto-subs", auto_command)
        self.assertIn("--no-write-subs", auto_command)

        android_command = module.build_ytdlp_command(
            "https://www.youtube.com/watch?v=abc123",
            Path("/tmp/video-summary/raw/subtitle"),
            ["en"],
            extractor_args="youtube:player_client=android",
        )
        self.assertEqual(
            android_command[android_command.index("--extractor-args") + 1],
            "youtube:player_client=android",
        )

    def test_vtt_is_cleaned_and_duplicate_cues_are_collapsed(self):
        module = load_module()
        content = """WEBVTT\n\n00:00:00.000 --> 00:00:01.250\n<c>Hello</c> &amp; world\n\n00:00:01.250 --> 00:00:02.000\nHello &amp; world\n\n00:00:02.000 --> 00:00:03.000\n第二段\n"""
        cues = module.parse_vtt(content)
        self.assertEqual(
            cues,
            [
                module.Cue(0, 2000, "Hello & world"),
                module.Cue(2000, 3000, "第二段"),
            ],
        )

    def test_json3_and_ass_are_supported(self):
        module = load_module()
        json3 = json.dumps(
            {
                "events": [
                    {"tStartMs": 0, "dDurationMs": 1200, "segs": [{"utf8": "你好"}]},
                    {"tStartMs": 1200, "dDurationMs": 800, "segs": [{"utf8": "世界"}]},
                ]
            }
        )
        self.assertEqual(
            module.parse_json3(json3),
            [module.Cue(0, 1200, "你好"), module.Cue(1200, 2000, "世界")],
        )

        ass = """[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:01.00,0:00:03.50,Default,,0,0,0,,第一行\\N第二行\n"""
        self.assertEqual(
            module.parse_ass(ass), [module.Cue(1000, 3500, "第一行 第二行")]
        )


class FetchFlowTests(unittest.TestCase):
    def _fake_ytdlp(self, directory: Path, *, write_subtitle: bool = True) -> Path:
        script = directory / "fake-yt-dlp.py"
        script.write_text(
            textwrap.dedent(
                f"""
                #!{sys.executable}
                import pathlib
                import sys

                args = sys.argv[1:]
                if {write_subtitle!r} and "--write-subs" in args:
                    stem = pathlib.Path(args[args.index("--output") + 1])
                    stem.parent.mkdir(parents=True, exist_ok=True)
                    stem.with_name(stem.name + ".zh-Hans.vtt").write_text(
                        "WEBVTT\\n\\n00:00:00.000 --> 00:00:02.000\\n测试字幕\\n",
                        encoding="utf-8",
                    )
                sys.exit(0)
                """
            ).lstrip(),
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        return script

    def test_fetch_prefers_manual_and_writes_metadata(self):
        module = load_module()
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            fake = self._fake_ytdlp(directory)
            result = module.fetch_subtitles(
                "https://www.youtube.com/watch?v=abc123",
                directory / "out",
                ["zh-Hans", "en"],
                yt_dlp=str(fake),
                timeout=10,
            )
            self.assertEqual(result["subtitle_type"], "manual")
            self.assertEqual(result["cue_count"], 1)
            self.assertEqual(
                (directory / "out" / "text.txt").read_text(encoding="utf-8"),
                "测试字幕\n",
            )
            self.assertEqual(
                json.loads(
                    (directory / "out" / "metadata.json").read_text(encoding="utf-8")
                )["language"],
                "zh-Hans",
            )

    def test_fetch_fails_when_both_subtitle_passes_produce_nothing(self):
        module = load_module()
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            fake = self._fake_ytdlp(directory, write_subtitle=False)
            with self.assertRaises(module.SubtitleError) as context:
                module.fetch_subtitles(
                    "https://www.bilibili.com/video/BV1xx",
                    directory / "out",
                    ["zh-Hans"],
                    yt_dlp=str(fake),
                    timeout=10,
                )
            self.assertIn("没有得到可解析的字幕文件", str(context.exception))

    def test_failed_fetch_clears_stale_normalized_outputs(self):
        module = load_module()
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            output = directory / "out"
            output.mkdir()
            for name in ("subtitle.srt", "text.txt", "metadata.json"):
                (output / name).write_text("stale", encoding="utf-8")
            fake = self._fake_ytdlp(directory, write_subtitle=False)
            with self.assertRaises(module.SubtitleError):
                module.fetch_subtitles(
                    "https://www.bilibili.com/video/BV1xx",
                    output,
                    ["zh-Hans"],
                    yt_dlp=str(fake),
                    timeout=10,
                )
            self.assertFalse((output / "subtitle.srt").exists())
            self.assertFalse((output / "text.txt").exists())
            self.assertFalse((output / "metadata.json").exists())


if __name__ == "__main__":
    unittest.main()
