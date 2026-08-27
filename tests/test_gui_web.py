# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false, reportImplicitOverride=false, reportIndexIssue=false, reportPrivateUsage=false, reportUnannotatedClassAttribute=false, reportUninitializedInstanceVariable=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false, reportUnusedParameter=false

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import final
from unittest import mock
from urllib.error import URLError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from maw.gui_web import EventPump, LauncherApi, LauncherPaths, PreflightError, _emoji_font_urls, _is_ffmpeg_start_failure, _is_ffprobe_start_failure, _request_from_payload, _route_dropped_path, _valid_emoji_font, default_paths, download_emoji_font, run_app  # noqa: E402
from maw.gui_workflow import TranscriptionCancelledError, TranscriptionProcessError, TranscriptionRequest, TranscriptionResult  # noqa: E402


class FakeWindow:
    def __init__(self) -> None:
        self.scripts: list[str] = []

    def evaluate_js(self, script: str) -> None:
        self.scripts.append(script)


@final
class GuiWebBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.env_path = self.root / ".env"
        self.example_path = self.root / ".env.example"
        _ = self.example_path.write_text("DASHSCOPE_API_KEY=\nDASHSCOPE_REGION=beijing\n", encoding="utf-8")
        self.paths = LauncherPaths(root=self.root, env_path=self.env_path, launcher_html=self.root / "launcher.html")
        self.window = FakeWindow()
        self.api = LauncherApi(paths=self.paths, window_getter=lambda: self.window)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_get_config_returns_registry_and_masked_key_when_env_exists(self) -> None:
        """Given local config, When JS asks for config, Then secrets are masked and registries return."""
        _ = self.env_path.write_text("DASHSCOPE_API_KEY=sk-secret-abcd\nDASHSCOPE_REGION=singapore\nMAW_GUI_LANG=en\n", encoding="utf-8")

        # 系统环境变量优先于 .env；置空相关变量，保证断言的是 .env 里的值。
        # lastModel/lastLanguage 走 pick_optional：只要键存在就返回（空串也算），
        # 必须移除宿主键，否则断言 None 会被宿主键破坏。
        with mock.patch.dict(
            os.environ,
            {"DASHSCOPE_API_KEY": "", "DASHSCOPE_REGION": "", "MAW_GUI_LANG": ""},
            clear=False,
        ):
            for key in ("MAW_GUI_LAST_MODEL", "MAW_GUI_LAST_LANGUAGE"):
                os.environ.pop(key, None)
            config = self.api.get_config()

        self.assertEqual(config["apiKey"], "sk-secret-abcd")
        self.assertEqual(config["maskedApiKey"], "sk-…abcd")
        self.assertEqual(config["region"], "singapore")
        self.assertEqual(config["guiLang"], "en")
        self.assertEqual(config["providerId"], "qwen")
        self.assertEqual(config["modelId"], "qwen-audio-3.0-asr-flash-filetrans")
        self.assertIsNone(config["lastModel"])
        self.assertIsNone(config["lastLanguage"])
        self.assertEqual([provider["id"] for provider in config["providers"]], ["qwen"])
        self.assertEqual(config["providers"][0]["keyUrl"], "https://help.aliyun.com/zh/model-studio/get-api-key")
        self.assertEqual(len(config["providers"][0]["commonLanguages"]), 10)
        self.assertEqual(config["models"][0]["id"], "qwen-audio-3.0-asr-flash-filetrans")
        self.assertEqual(config["models"][1]["id"], "fun-asr")
        self.assertEqual(config["models"][2]["id"], "qwen3-asr-flash-filetrans")
        self.assertTrue(config["models"][0]["supportsSpeaker"])
        self.assertTrue(config["models"][0]["supportsContext"])
        self.assertTrue(config["models"][0]["supportsHotwords"])
        self.assertTrue(config["models"][0]["supportsVocabulary"])
        self.assertEqual(config["models"][0]["languages"][0]["id"], "")
        self.assertFalse(config["models"][2]["supportsSpeaker"])
        self.assertEqual(config["languages"][0]["id"], "")

    def test_save_settings_writes_env_without_echoing_key(self) -> None:
        """Given form values, When saved, Then .env is updated and response masks the key."""
        result = self.api.save_settings({
            "modelId": "qwen3-asr-flash-filetrans",
            "apiKey": "sk-super-secret-9999",
            "region": "singapore",
            "language": "zh",
            "workspaceId": "ws-1",
            "guiLang": "en",
        })

        text = self.env_path.read_text(encoding="utf-8")
        self.assertIn("DASHSCOPE_API_KEY=sk-super-secret-9999", text)
        self.assertIn("DASHSCOPE_WORKSPACE_ID=ws-1", text)
        self.assertEqual(result["maskedApiKey"], "sk-…9999")
        self.assertNotIn("super-secret", result["message"])

    def test_save_prefs_writes_only_gui_memory_keys(self) -> None:
        self.env_path.write_text("# keep\nDASHSCOPE_REGION=beijing\n", encoding="utf-8")

        result = self.api.save_prefs({"modelId": "fun-asr", "language": ""})

        self.assertTrue(result["ok"])
        self.assertEqual(
            self.env_path.read_text(encoding="utf-8"),
            "# keep\nDASHSCOPE_REGION=beijing\nMAW_GUI_LAST_MODEL=fun-asr\nMAW_GUI_LAST_LANGUAGE=\n",
        )

    def test_zoom_preference_round_trips_normalized_through_config(self) -> None:
        result = self.api.save_prefs({"zoomPercent": 115})

        self.assertEqual(result, {"ok": True, "zoomPercent": 115})
        self.assertEqual(self.api.get_config()["zoomPercent"], 115)
        self.assertIn("MAW_GUI_ZOOM_PERCENT=115", self.env_path.read_text(encoding="utf-8"))

    def test_zoom_preference_normalizes_malformed_and_out_of_range_values(self) -> None:
        for value, expected in (("NaN", 100), (79, 80), (151, 150)):
            with self.subTest(value=value):
                result = self.api.save_prefs({"zoomPercent": value})
                self.assertEqual(result, {"ok": True, "zoomPercent": expected})
                self.assertEqual(self.api.get_config()["zoomPercent"], expected)

    def test_get_config_exposes_last_language_empty_vs_absent(self) -> None:
        self.env_path.write_text("MAW_GUI_LAST_MODEL=fun-asr\nMAW_GUI_LAST_LANGUAGE=\n", encoding="utf-8")

        # pick_optional 按“键是否存在”读取：宿主同名键（即使是空串）会盖过 .env，
        # 必须移除宿主键，让 .env 的值生效。
        with mock.patch.dict(os.environ, {}, clear=False):
            for key in ("MAW_GUI_LAST_MODEL", "MAW_GUI_LAST_LANGUAGE"):
                os.environ.pop(key, None)
            remembered = self.api.get_config()
            self.env_path.write_text("DASHSCOPE_DEFAULT_LANGUAGE=zh\n", encoding="utf-8")
            absent = self.api.get_config()

        self.assertEqual(remembered["lastModel"], "fun-asr")
        self.assertEqual(remembered["lastLanguage"], "")
        self.assertIsNone(absent["lastLanguage"])
        self.assertEqual(absent["language"], "zh")

    def test_open_file_opens_existing_file(self) -> None:
        artifact = self.root / "clip.srt"
        artifact.write_text("1\n", encoding="utf-8")

        with mock.patch("maw.gui_web._open_existing_path", return_value={"ok": True}) as open_path:
            result = self.api.open_file({"path": str(artifact)})

        self.assertTrue(result["ok"])
        open_path.assert_called_once_with(artifact)

    def test_open_file_rejects_missing_file(self) -> None:
        with mock.patch("maw.gui_web._open_existing_path") as open_path:
            result = self.api.open_file({"path": str(self.root / "missing.srt")})

        self.assertFalse(result["ok"])
        self.assertIn("File does not exist", result["error"])
        open_path.assert_not_called()

    def test_open_containing_folder_opens_resolved_parent_for_existing_file(self) -> None:
        artifact = self.root / "nested" / "clip.srt"
        artifact.parent.mkdir()
        artifact.write_text("1\n", encoding="utf-8")

        with mock.patch("maw.gui_web._open_existing_path", return_value={"ok": True}) as open_path:
            result = self.api.open_containing_folder({"path": str(artifact)})

        self.assertEqual(result, {"ok": True})
        open_path.assert_called_once_with(artifact.parent.resolve())

    def test_open_containing_folder_rejects_missing_file(self) -> None:
        with mock.patch("maw.gui_web._open_existing_path") as open_path:
            result = self.api.open_containing_folder({"path": str(self.root / "missing.srt")})

        self.assertFalse(result["ok"])
        self.assertIn("File does not exist", result["error"])
        open_path.assert_not_called()

    def test_open_containing_folder_rejects_directory_input(self) -> None:
        directory = self.root / "artifacts"
        directory.mkdir()

        with mock.patch("maw.gui_web._open_existing_path") as open_path:
            result = self.api.open_containing_folder({"path": str(directory)})

        self.assertFalse(result["ok"])
        self.assertIn("File does not exist", result["error"])
        open_path.assert_not_called()

    def test_check_ffmpeg_reports_found_when_both_tools_exist(self) -> None:
        ffmpeg = self.root / "bin" / "ffmpeg.exe"
        ffprobe = self.root / "bin" / "ffprobe.exe"
        ffmpeg.parent.mkdir()
        ffmpeg.write_bytes(b"exe")
        ffprobe.write_bytes(b"exe")

        def which(name: str, *, path: str | None = None) -> str:
            return str(ffmpeg if name == "ffmpeg" else ffprobe)

        with mock.patch("maw.gui_web.shutil.which", side_effect=which):
            result = self.api.check_ffmpeg()

        self.assertTrue(result["found"])
        self.assertEqual(result["directory"], str(ffmpeg.parent))

    def test_check_ffmpeg_falls_back_to_bundled_tools(self) -> None:
        ffmpeg_dir = self.root / "ffmpeg" / "bin"
        ffmpeg_dir.mkdir(parents=True)
        ffmpeg = ffmpeg_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        ffprobe = ffmpeg_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        ffmpeg.write_bytes(b"exe")
        ffprobe.write_bytes(b"exe")

        with mock.patch("maw.gui_web.shutil.which", return_value=None):
            with mock.patch("maw.gui_web._bundled_ffmpeg_directory", return_value=ffmpeg_dir):
                result = self.api.check_ffmpeg()

        self.assertTrue(result["found"])
        self.assertEqual(result["ffmpeg"], str(ffmpeg))
        self.assertEqual(result["ffprobe"], str(ffprobe))

    def test_check_ffmpeg_uses_macos_candidate_directories(self) -> None:
        ffmpeg_dir = self.root / "homebrew" / "bin"
        ffmpeg_dir.mkdir(parents=True)

        def which(name: str, *, path: str | None = None) -> str:
            assert path is not None
            self.assertIn(str(ffmpeg_dir), path.split(os.pathsep))
            return str(ffmpeg_dir / ("ffmpeg.exe" if name == "ffmpeg" else "ffprobe.exe"))

        with mock.patch.object(sys, "platform", "darwin"):
            with mock.patch("maw.gui_workflow.MACOS_FFMPEG_CANDIDATE_DIRECTORIES", (str(ffmpeg_dir),)):
                with mock.patch("maw.gui_web.shutil.which", side_effect=which):
                    result = self.api.check_ffmpeg()

        self.assertTrue(result["found"])
        self.assertEqual(result["directory"], str(ffmpeg_dir))

    def test_save_ffmpeg_path_invalid_stays_missing(self) -> None:
        result = self.api.save_ffmpeg_path({"path": str(self.root / "missing")})

        self.assertFalse(result["ok"])
        self.assertFalse(result["found"])

    def test_save_ffmpeg_path_reports_configuration_write_failure(self) -> None:
        with mock.patch("maw.gui_web.save_env", side_effect=PermissionError("read-only app bundle")):
            result = self.api.save_ffmpeg_path({"path": "/opt/homebrew/bin"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["field"], "ffmpegPath")
        self.assertEqual(result["code"], "config_save_failed")
        self.assertIn("read-only app bundle", result["detail"])

    def test_save_ffmpeg_path_accepts_a_directory_with_both_macos_tools(self) -> None:
        ffmpeg_dir = self.root / "bin"
        ffmpeg_dir.mkdir()
        ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
        (ffmpeg_dir / ffmpeg_name).write_bytes(b"executable")
        (ffmpeg_dir / ffprobe_name).write_bytes(b"executable")

        result = self.api.save_ffmpeg_path({"path": str(ffmpeg_dir)})

        self.assertTrue(result["ok"])
        self.assertTrue(result["found"])
        self.assertEqual(result["directory"], str(ffmpeg_dir))
        self.assertIn(f"FFMPEG_PATH={ffmpeg_dir}", self.env_path.read_text(encoding="utf-8"))

    @unittest.skipUnless(os.name == "nt", "os.startfile 仅 Windows 可用；os.name 补丁会让 pathlib 选择 WindowsPath")
    def test_open_output_folder_uses_startfile_on_windows(self) -> None:
        folder = self.root / "out"
        folder.mkdir()
        self.api.result = TranscriptionResult(srt_path=folder / "a.srt")

        with mock.patch("maw.gui_web.os.name", "nt"):
            with mock.patch("maw.gui_web.os.startfile", create=True) as startfile:
                result = self.api.open_output_folder()

        self.assertTrue(result["ok"])
        startfile.assert_called_once_with(str(folder))

    def test_cancel_transcription_sets_event(self) -> None:
        """Given a running cancellation token, When cancel is called, Then the event is set."""
        self.api.cancel_event = threading.Event()

        result = self.api.cancel_transcription()

        self.assertTrue(self.api.cancel_event.is_set())
        self.assertTrue(result["ok"])

    def test_start_transcription_rejects_missing_media(self) -> None:
        """Given missing media, When transcription starts, Then validation fails before subprocess."""
        result = self.api.start_transcription({"mediaPath": str(self.root / "missing.mp3"), "srtPath": str(self.root / "out.srt")})

        self.assertFalse(result["ok"])
        self.assertEqual(result["field"], "mediaPath")
        self.assertEqual(result["code"], "media_not_found")
        self.assertIn("media", result["error"].lower())

    def test_batch_invalid_items_returns_preflight_details(self) -> None:
        result = self.api.start_batch_transcription({
            "items": [{"id": "missing", "mediaPath": str(self.root / "missing.mp3")}],
            "apiKey": "sk-test",
        })

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "batch_items_invalid")
        self.assertIn("missing", result["detail"])

    def test_start_transcription_rejects_empty_resolved_api_key(self) -> None:
        """Given media and output but no key anywhere, When starting, Then API key blocks."""
        media = self.root / "clip.mp3"
        _ = media.write_bytes(b"media")

        # 置空系统环境变量，保证“任何位置都没有 Key”的前提成立。
        with mock.patch.dict(os.environ, {"DASHSCOPE_API_KEY": ""}, clear=False):
            result = self.api.start_transcription({"mediaPath": str(media), "srtPath": str(self.root / "out.srt"), "apiKey": ""})

        self.assertFalse(result["ok"])
        self.assertEqual(result["field"], "apiKey")
        self.assertEqual(result["code"], "api_key_missing")

    def test_start_transcription_accepts_api_key_from_env_file(self) -> None:
        """Given saved API key, When field is empty, Then resolved key is used."""
        media = self.root / "clip.mp3"
        _ = media.write_bytes(b"media")
        self.env_path.write_text("DASHSCOPE_API_KEY=sk-from-env\n", encoding="utf-8")

        # 置空系统环境变量，保证解析到的 Key 确实来自 .env 而非宿主环境。
        with mock.patch.dict(os.environ, {"DASHSCOPE_API_KEY": ""}, clear=False):
            with mock.patch("maw.gui_web.run_transcription"):
                result = self.api.start_transcription({"mediaPath": str(media), "srtPath": str(self.root / "out.srt"), "apiKey": ""})

        self.assertTrue(result["ok"])
        self.api.cancel_transcription()

    def test_start_transcription_rejects_singapore_without_workspace(self) -> None:
        """Given Singapore region, When workspace is absent, Then workspace blocks."""
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")

        result = self.api.start_transcription({
            "mediaPath": str(media),
            "srtPath": str(self.root / "out.srt"),
            "apiKey": "sk-test",
            "region": "singapore",
            "workspaceId": "",
        })

        self.assertFalse(result["ok"])
        self.assertEqual(result["field"], "workspaceId")
        self.assertEqual(result["code"], "workspace_missing")

    def test_start_transcription_rejects_missing_output_path_with_code(self) -> None:
        """Given media but no output path, When transcription starts, Then output_missing blocks."""
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")

        result = self.api.start_transcription({"mediaPath": str(media), "srtPath": "", "apiKey": "sk-test"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["field"], "srtPath")
        self.assertEqual(result["code"], "output_missing")

    def test_default_output_avoids_existing_srt_and_reports_rename(self) -> None:
        media = self.root / "clip.mp4"
        media.write_bytes(b"media")
        output = self.root / "clip.qwen-audio.srt"
        output.write_text("existing", encoding="utf-8")

        result = self.api.default_output({"mediaPath": str(media), "providerId": "qwen", "modelId": "qwen-audio-3.0-asr-flash-filetrans"})

        self.assertTrue(result["renamed"])
        self.assertEqual(result["path"], str(self.root / "clip.qwen-audio-1.srt"))

    def test_start_transcription_rechecks_output_collision_before_worker(self) -> None:
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")
        output = self.root / "out.srt"
        output.write_text("existing", encoding="utf-8")
        result = TranscriptionResult(srt_path=self.root / "out-1.srt")

        with mock.patch("maw.gui_web.run_transcription", return_value=result):
            started = self.api.start_transcription({"mediaPath": str(media), "srtPath": str(output), "apiKey": "sk-test"})
            self.assertTrue(started["ok"])
            self.assertTrue(started["outputRenamed"])
            self.assertEqual(started["outputPath"], str(self.root / "out-1.srt"))
            if self.api.worker:
                self.api.worker.join(timeout=1)

    def test_request_from_payload_test_run_overrides_manual_length_limit(self) -> None:
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")

        request = _request_from_payload({
            "mediaPath": str(media),
            "srtPath": str(self.root / "out.srt"),
            "apiKey": "sk-test",
            "region": "beijing",
            "lengthLimit": "30m",
            "testRun": True,
            "debugRaw": True,
            "speaker": True,
            "guiLang": "en",
        }, self.env_path)

        self.assertEqual(request.length_limit, "2m")
        self.assertEqual(request.srt_path.name, "out-test.srt")
        self.assertTrue(request.debug_raw)
        self.assertTrue(request.speaker)

    def test_request_from_payload_without_test_run_uses_manual_length_limit(self) -> None:
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")

        request = _request_from_payload({
            "mediaPath": str(media),
            "srtPath": str(self.root / "out.srt"),
            "apiKey": "sk-test",
            "region": "beijing",
            "lengthLimit": "30m",
            "testRun": False,
        }, self.env_path)

        self.assertEqual(request.length_limit, "30m")

    def test_request_from_payload_passes_segmentation_options(self) -> None:
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")

        request = _request_from_payload({
            "mediaPath": str(media),
            "srtPath": str(self.root / "out.srt"),
            "apiKey": "sk-test",
            "maxLen": "14",
            "minLen": "3",
            "gapSplit": "800",
        }, self.env_path)

        self.assertEqual(request.max_len, "14")
        self.assertEqual(request.min_len, "3")
        self.assertEqual(request.gap_split, "800")

    def test_request_from_payload_rejects_invalid_segmentation_options(self) -> None:
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")
        base = {
            "mediaPath": str(media),
            "srtPath": str(self.root / "out.srt"),
            "apiKey": "sk-test",
        }

        with self.assertRaises(PreflightError) as raised:
            _request_from_payload({**base, "maxLen": "2", "minLen": "3"}, self.env_path)

        self.assertEqual(raised.exception.field, "maxLen")
        self.assertEqual(raised.exception.code, "segmentation_invalid")

    def test_request_from_payload_passes_qwen_audio_options_without_persisting_them(self) -> None:
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")
        request = _request_from_payload({
            "providerId": "qwen",
            "modelId": "qwen-audio-3.0-asr-flash-filetrans",
            "mediaPath": str(media),
            "srtPath": str(self.root / "out.srt"),
            "apiKey": "sk-test",
            "region": "beijing",
            "qwenAudioContext": "产品名和专业术语",
            "qwenAudioHotwords": "张三\n李四,阿里云",
            "qwenAudioVocabularyId": "vocab-qwen-audio",
            "qwenAudioHotwordWeight": "50",
        }, self.env_path)

        self.assertEqual(request.qwen_audio_context, "产品名和专业术语")
        self.assertEqual(request.qwen_audio_hotwords, "张三\n李四,阿里云")
        self.assertEqual(request.qwen_audio_vocabulary_id, "vocab-qwen-audio")
        self.assertEqual(request.qwen_audio_hotword_weight, "50")

    def test_request_from_payload_passes_qwen_audio_hotword_file_mode(self) -> None:
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")
        hotwords = self.root / "hotwords.txt"
        hotwords.write_text("张三\n阿里云\n", encoding="utf-8")
        request = _request_from_payload({
            "providerId": "qwen",
            "modelId": "qwen-audio-3.0-asr-flash-filetrans",
            "mediaPath": str(media),
            "srtPath": str(self.root / "out.srt"),
            "apiKey": "sk-test",
            "region": "beijing",
            "qwenAudioHotwordsMode": "file",
            "qwenAudioHotwordsFile": str(hotwords),
            "qwenAudioHotwords": "不会被使用",
        }, self.env_path)

        self.assertEqual(request.qwen_audio_hotwords_file, str(hotwords))
        self.assertEqual(request.qwen_audio_hotwords, "")

    def test_request_from_payload_rejects_missing_qwen_audio_hotword_file(self) -> None:
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")

        with self.assertRaisesRegex(PreflightError, "\\.txt"):
            _request_from_payload({
                "providerId": "qwen",
                "modelId": "qwen-audio-3.0-asr-flash-filetrans",
                "mediaPath": str(media),
                "srtPath": str(self.root / "out.srt"),
                "apiKey": "sk-test",
                "region": "beijing",
                "qwenAudioHotwordsMode": "file",
                "qwenAudioHotwordsFile": str(self.root / "missing.txt"),
            }, self.env_path)

    def test_read_hotword_file_returns_utf8_text(self) -> None:
        hotwords = self.root / "hotwords.txt"
        hotwords.write_text("张三\n阿里云\n", encoding="utf-8")

        result = self.api.read_hotword_file({"path": str(hotwords)})

        self.assertTrue(result["ok"])
        self.assertEqual(result["path"], str(hotwords))
        self.assertEqual(result["text"], "张三\n阿里云\n")

    def test_request_from_payload_rejects_qwen_audio_context_over_400_characters(self) -> None:
        media = self.root / "clip.mp3"
        media.write_bytes(b"media")

        with self.assertRaisesRegex(PreflightError, "400"):
            _request_from_payload({
                "providerId": "qwen",
                "modelId": "qwen-audio-3.0-asr-flash-filetrans",
                "mediaPath": str(media),
                "srtPath": str(self.root / "out.srt"),
                "apiKey": "sk-test",
                "region": "beijing",
                "qwenAudioContext": "x" * 401,
            }, self.env_path)

    def test_event_pump_batches_events_and_preserves_order(self) -> None:
        pump = EventPump(window_getter=lambda: self.window)
        pump.enqueue({"type": "log", "message": "one"})
        pump.enqueue({"type": "log", "message": "two"})

        pump.flush()

        self.assertEqual(len(self.window.scripts), 1)
        self.assertIn("onBackendEvents", self.window.scripts[0])
        self.assertLess(self.window.scripts[0].index("one"), self.window.scripts[0].index("two"))

    def test_ffprobe_start_failure_is_recognised_from_child_output(self) -> None:
        self.assertTrue(_is_ffprobe_start_failure([
            "subprocess.CalledProcessError: Command ['ffprobe', ...]",
            "returned non-zero exit status 3221225794.",
        ]))
        self.assertFalse(_is_ffprobe_start_failure([
            "subprocess.CalledProcessError: Command ['ffprobe', ...]",
            "returned non-zero exit status 1.",
        ]))

    def test_ffmpeg_start_failure_is_recognised_from_child_output(self) -> None:
        self.assertTrue(_is_ffmpeg_start_failure([
            "Traceback: Command ['ffmpeg', '-i', 'clip.mp4']",
            "returned non-zero exit status 3221225794.",
        ]))
        self.assertFalse(_is_ffmpeg_start_failure([
            "Command ['ffmpeg', ...]",
            "returned non-zero exit status 1.",
        ]))

    def test_launcher_api_queues_started_event_and_shutdown_flushes(self) -> None:
        self.api._emit({"type": "log", "message": "queued"})

        self.api.shutdown()

        self.assertTrue(self.window.scripts)
        self.assertIn("queued", self.window.scripts[-1])

    def test_worker_emits_done_with_srt_result(self) -> None:
        request = TranscriptionRequest(
            media_path=self.root / "clip.wav",
            srt_path=self.root / "clip.srt",
        )
        result = TranscriptionResult(srt_path=self.root / "clip.srt")

        with mock.patch("maw.gui_web.run_transcription", return_value=result):
            self.api._worker_main(request, threading.Event())

        self.assertEqual(self.api.result, result)
        self.assertTrue(self.window.scripts)
        event_script = self.window.scripts[-1]
        self.assertIn('"type": "done"', event_script)
        self.assertIn(str(result.srt_path).replace("\\", "\\\\"), event_script)
        self.assertIn('"rawPath": ""', event_script)

    def test_worker_emits_retryable_error_for_ffprobe_start_failure(self) -> None:
        request = TranscriptionRequest(
            media_path=self.root / "clip.wav",
            srt_path=self.root / "clip.srt",
        )

        def fail_with_ffprobe_output(*_args: object, **kwargs: object) -> None:
            callback = kwargs["on_event"]
            assert callable(callback)
            callback("subprocess.CalledProcessError: Command ['ffprobe', ...]")
            callback("returned non-zero exit status 3221225794.")
            raise TranscriptionProcessError(1)

        with mock.patch("maw.gui_web.run_transcription", side_effect=fail_with_ffprobe_output):
            self.api._worker_main(request, threading.Event())

        self.assertTrue(self.window.scripts)
        event_script = self.window.scripts[-1]
        self.assertIn('"code": "ffprobe_start_failed"', event_script)
        self.assertIn('"detail": "Transcription failed with exit code 1"', event_script)

    def test_worker_emits_cancellation_error_for_cancelled_transcription(self) -> None:
        request = TranscriptionRequest(
            media_path=self.root / "clip.wav",
            srt_path=self.root / "clip.srt",
        )

        with mock.patch("maw.gui_web.run_transcription", side_effect=TranscriptionCancelledError()):
            self.api._worker_main(request, threading.Event())

        self.assertTrue(self.window.scripts)
        event_script = self.window.scripts[-1]
        self.assertIn('"type": "error"', event_script)
        self.assertIn('"code": "transcription_cancelled"', event_script)
        self.assertNotIn('"code": "transcription_failed"', event_script)

    def test_worker_emits_retryable_error_for_ffmpeg_start_failure(self) -> None:
        request = TranscriptionRequest(
            media_path=self.root / "clip.mp4",
            srt_path=self.root / "clip.srt",
        )

        def fail_with_ffmpeg_output(*_args: object, **kwargs: object) -> None:
            callback = kwargs["on_event"]
            assert callable(callback)
            callback("Traceback: Command ['ffmpeg', '-i', 'clip.mp4']")
            callback("returned non-zero exit status 3221225794.")
            raise TranscriptionProcessError(1)

        with mock.patch("maw.gui_web.run_transcription", side_effect=fail_with_ffmpeg_output):
            self.api._worker_main(request, threading.Event())

        self.assertTrue(self.window.scripts)
        event_script = self.window.scripts[-1]
        self.assertIn('"code": "ffmpeg_start_failed"', event_script)
        self.assertIn('"detail": "Transcription failed with exit code 1"', event_script)

    def test_route_dropped_path_routes_media_hotwords_and_rejects_rest(self) -> None:
        """Given dropped paths, When routed, Then only media and hotword files are accepted."""
        media = _route_dropped_path(r"D:\Videos\clip.MP4")
        hotwords = _route_dropped_path(r"D:\Videos\clip.txt")
        project = _route_dropped_path(r"D:\Videos\clip.json")
        subtitle = _route_dropped_path(r"D:\Videos\clip.srt")

        self.assertEqual(media, {"type": "dropMedia", "path": r"D:\Videos\clip.MP4"})
        self.assertEqual(hotwords, {"type": "dropHotwordFile", "path": r"D:\Videos\clip.txt"})
        self.assertEqual(project, {"type": "dropReject", "path": r"D:\Videos\clip.json"})
        self.assertEqual(subtitle, {"type": "dropReject", "path": r"D:\Videos\clip.srt"})


@final
class LauncherRuntimeTests(unittest.TestCase):
    def test_run_app_passes_debug_and_controls_automatic_devtools(self) -> None:
        paths = LauncherPaths(
            root=Path("launcher-root"),
            env_path=Path("launcher-root/.env"),
            launcher_html=Path("launcher-root/launcher.html"),
        )

        for debug, devtools in ((False, False), (True, False), (True, True)):
            fake_webview = mock.Mock()
            fake_webview.settings = {"OPEN_DEVTOOLS_IN_DEBUG": True}
            fake_webview.create_window.return_value = None
            fake_webview.start.return_value = None
            with (
                mock.patch.dict(sys.modules, {"webview": fake_webview}),
                mock.patch("maw.gui_web.default_paths", return_value=paths),
                mock.patch("maw.gui_web.LauncherApi"),
                mock.patch("maw.gui_web.asset_path", return_value=Path("missing.ico")),
            ):
                run_app(debug=debug, devtools=devtools)

            self.assertEqual(fake_webview.settings["OPEN_DEVTOOLS_IN_DEBUG"], devtools)
            self.assertEqual(fake_webview.start.call_args.kwargs["debug"], debug or devtools)
            fake_webview.reset_mock()


@final
class LauncherAssetContractTests(unittest.TestCase):
    def test_launcher_message_url_stops_before_closing_punctuation(self) -> None:
        script = (ROOT / "web" / "launcher" / "launcher.js").read_text(encoding="utf-8")

        expected = r'''const urlPattern = /https?:\/\/[^\s<>"'|)\]}，。；：！？）】》」』]+/gi;'''
        self.assertIn(expected, script)

    def test_launcher_hero_shows_the_bundled_brand_icon(self) -> None:
        page = (ROOT / "web" / "launcher" / "index.html").read_text(encoding="utf-8")
        stylesheet = (ROOT / "web" / "launcher" / "launcher.css").read_text(encoding="utf-8")

        self.assertIn('<div class="hero-brand">', page)
        self.assertIn('<img class="hero-icon" src="../../assets/show.webp"', page)
        self.assertIn(".hero-icon {\n  width: 72px;\n  height: 72px;", stylesheet)

    def test_launcher_reports_media_drop_rejection_and_output_collision(self) -> None:
        page = (ROOT / "web" / "launcher" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "launcher" / "launcher.js").read_text(encoding="utf-8")

        self.assertIn('id="srtPathNotice" class="hint warn hidden"', page)
        self.assertIn("drop_reject_media", script)
        self.assertIn('drop_reject_media: "仅支持以下媒体文件类型：\\n{extensions}"', script)
        self.assertIn('function appendMessageText(container, text)', script)
        self.assertIn('setError("mediaPath", mediaDropError())', script)
        self.assertIn('output_collision: "检测到同名输出文件', script)
        self.assertIn("result.outputRenamed", script)

    def test_launcher_exposes_segmentation_controls_and_payload_fields(self) -> None:
        page = (ROOT / "web" / "launcher" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "launcher" / "launcher.js").read_text(encoding="utf-8")
        stylesheet = (ROOT / "web" / "launcher" / "launcher.css").read_text(encoding="utf-8")

        for control in ("segmentationField", "maxLen", "minLen", "gapSplit"):
            self.assertIn(f'id="{control}"', page)
        self.assertIn('maxLen: $("maxLen").value.trim()', script)
        self.assertIn('minLen: $("minLen").value.trim()', script)
        self.assertIn('gapSplit: $("gapSplit").value.trim()', script)
        self.assertIn('segmentation: "字幕切句"', script)
        self.assertIn(".segmentation-row", stylesheet)

    def test_ffmpeg_save_distinguishes_write_failure_from_missing_tools(self) -> None:
        script = (ROOT / "web" / "launcher" / "launcher.js").read_text(encoding="utf-8")

        self.assertIn("config_save_failed", script)
        self.assertIn("result.found === false", script)
        self.assertIn("if (!result.ok) { const message = ffmpegSaveError(result);", script)

    def test_launcher_batch_and_single_stop_controls_are_wired(self) -> None:
        page = (ROOT / "web" / "launcher" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "launcher" / "launcher.js").read_text(encoding="utf-8")
        batch_script = (ROOT / "web" / "launcher" / "batch.js").read_text(encoding="utf-8")

        self.assertIn('id="stop" class="ghost server-stop hidden"', page)
        self.assertIn('data-i18n="batch_start">✨ 开始批量生成', page)
        self.assertIn('bridge("cancel_transcription")', script)
        self.assertIn('window.MAWLauncher.confirm(t("batch_skip_completed_confirm"))', batch_script)
        self.assertIn('data-i18n="batch_confirm_yes">是', page)
        self.assertIn('data-i18n="batch_confirm_no">否', page)
        self.assertIn('batchDropNotice', page)
        self.assertIn('window.MAWLauncher.appendLog?.(`[${message}]`, { inline: true })', batch_script)
        self.assertIn('window.MAWLauncher.backend === "real"', batch_script)
        self.assertLess(batch_script.index('if (window.MAWLauncher.backend === "real") return;'), batch_script.index('event.stopImmediatePropagation();'))

    def test_language_filter_hint_is_available_to_single_language_providers(self) -> None:
        page = (ROOT / "web" / "launcher" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "launcher" / "launcher.js").read_text(encoding="utf-8")

        self.assertIn('id="languageFilterHint"', page)
        self.assertIn('language_filter_hint: "默认仅显示常用语言', script)
        self.assertIn('$("languageFilterHint").classList.toggle("hidden", showRare || commons.length === 0);', script)
        self.assertIn("const selectedModel = () =>", script)
        self.assertIn("applyProviderLanguages(provider(), selectedModel())", script)

    def test_qwen_audio_launcher_exposes_one_shot_context_and_hotwords_only(self) -> None:
        page = (ROOT / "web" / "launcher" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "launcher" / "launcher.js").read_text(encoding="utf-8")

        for field in ("qwenAudioContext", "qwenAudioHotwordsMode", "qwenAudioHotwords", "qwenAudioHotwordsFile", "qwenAudioHotwordWeight"):
            self.assertIn(f'id="{field}"', page)
        self.assertIn('qwenAudioContext: $("qwenAudioContext").value.trim()', script)
        self.assertIn('qwenAudioHotwords: $("qwenAudioHotwords").value.trim()', script)
        self.assertIn('qwenAudioHotwordsMode: $("qwenAudioHotwordsMode").value', script)
        self.assertIn('qwenAudioHotwordsFile: $("qwenAudioHotwordsFile").value.trim()', script)
        self.assertIn('kind: "hotwords"', script)
        self.assertIn('read_hotword_file', script)
        self.assertIn('qwenAudioContextCount', page)
        self.assertIn('classList.toggle("over-limit", count > 400)', script)
        self.assertIn('qwenAudioHotwordsWarning', page)
        self.assertIn('qwen_audio_hotwords_weight_override_hint', script)
        self.assertIn('parseHotwordEntry', script)
        self.assertIn('MAX_SUPER_HOTWORDS = 50', script)
        self.assertNotIn('id="qwenAudioVocabularyId"', page)
        self.assertNotIn("qwenAudioVocabularyId", script)
        self.assertIn('supportsContext', script)

    def test_multilanguage_launcher_uses_full_width_language_layout(self) -> None:
        page = (ROOT / "web" / "launcher" / "index.html").read_text(encoding="utf-8")
        stylesheet = (ROOT / "web" / "launcher" / "launcher.css").read_text(encoding="utf-8")

        self.assertIn('class="language-layout"', page)
        self.assertIn('class="language-side"', page)
        self.assertIn('id="languageGroup" class="adv-group"', page)
        self.assertIn(
            ".adv-group {\n  grid-column: 1 / -1;\n  display: grid;",
            stylesheet,
        )
        self.assertIn(
            ".grid-two:not(.single-language) #languageField .language-layout {\n  display: grid;\n  grid-template-columns: minmax(0, 1fr) minmax(220px, .8fr);",
            stylesheet,
        )
        self.assertIn(
            ".grid-two:not(.single-language) #languageField #language {\n  height: 132px;\n  max-height: 132px;\n}",
            stylesheet,
        )

    def test_advanced_options_are_grouped_into_titled_cards(self) -> None:
        page = (ROOT / "web" / "launcher" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "launcher" / "launcher.js").read_text(encoding="utf-8")
        stylesheet = (ROOT / "web" / "launcher" / "launcher.css").read_text(encoding="utf-8")

        self.assertIn('id="segmentationField" class="adv-group segmentation-field"', page)
        self.assertIn('id="advancedParamsGroup" class="adv-group"', page)
        self.assertIn("function syncAdvancedParamsGroup()", script)
        self.assertIn("renderKeyStatus(); syncWorkspace(); syncAdvancedParamsGroup();", script)
        self.assertIn('id="qwenAudioOptions" class="adv-group qwen-audio-options hidden"', page)
        self.assertIn('data-i18n="advanced_params"', page)
        self.assertIn('data-i18n="advanced_misc"', page)
        self.assertIn('data-i18n="qwen_audio_options_title"', page)
        self.assertIn('advanced_params: "识别参数"', script)
        self.assertIn('advanced_misc: "其他"', script)
        self.assertIn('qwen_audio_options_title: "Qwen 上下文与热词"', script)
        self.assertIn('gap_split_placeholder: "默认 1500"', script)
        self.assertIn('gap_split_placeholder: "Default: 1500"', script)
        self.assertIn("停顿切句默认 1500ms", script)
        self.assertIn("pause split defaults to 1500 ms", script)
        self.assertIn('$("languageGroup").classList.toggle("hidden", current.supportsLanguage === false)', script)
        self.assertIn(".advanced-col {\n  display: grid;\n  grid-template-columns: 1fr 1fr;", stylesheet)
        self.assertNotIn("display: contents", stylesheet)

    def test_regional_fields_are_temporarily_hidden_for_domestic_launcher(self) -> None:
        page = (ROOT / "web" / "launcher" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "launcher" / "launcher.js").read_text(encoding="utf-8")

        self.assertIn('id="regionField" class="field hidden"', page)
        self.assertIn('id="workspaceField" class="field hidden"', page)
        self.assertIn("北京地域选填（推荐），新加坡地域必填。", page)
        self.assertIn(
            "const SHOW_REGIONAL_FIELDS = false;",
            script,
        )
        self.assertIn(
            '$("regionField").classList.toggle("hidden", !SHOW_REGIONAL_FIELDS || current.regions.length === 0);',
            script,
        )
        self.assertIn(
            '$("workspaceField").classList.toggle("hidden", !SHOW_REGIONAL_FIELDS || provider().regions.length === 0);',
            script,
        )
        self.assertIn('data.region === "singapore" && !data.workspaceId', script)

    def test_launcher_section_titles_share_emoji_numbering_and_size(self) -> None:
        page = (ROOT / "web" / "launcher" / "index.html").read_text(encoding="utf-8")
        stylesheet = (ROOT / "web" / "launcher" / "launcher.css").read_text(encoding="utf-8")

        for expected in ("1️⃣ 媒体与输出", "2️⃣ 识别设置", "3️⃣ 日志"):
            self.assertIn(expected, page)
        self.assertIn(".card h2 {\n  margin: 0 0 12px;\n  color: var(--text-secondary);\n  font-size: 16px;", stylesheet)


@final
class DefaultPathsTests(unittest.TestCase):
    def test_default_paths_resolves_frozen_meipass_root(self) -> None:
        """Given PyInstaller 冻结环境, When 解析默认路径, Then 资源根为 _MEIPASS。"""
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "_MEIPASS", "/opt/app/_internal", create=True):
            paths = default_paths()
        self.assertEqual(paths.launcher_html, Path("/opt/app/_internal/web/launcher/index.html"))
        self.assertEqual(paths.root, Path("/opt/app/_internal"))

    def test_default_paths_uses_repo_root_when_not_frozen(self) -> None:
        """Given 源码运行, When 解析默认路径, Then 资源根为仓库根。"""
        self.assertFalse(getattr(sys, "frozen", False))
        paths = default_paths()
        self.assertEqual(paths.launcher_html, ROOT / "web" / "launcher" / "index.html")


class _FakeUrlResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            chunk = self._body[self._offset :]
        else:
            chunk = self._body[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def __enter__(self) -> _FakeUrlResponse:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


@final
class EmojiFontTests(unittest.TestCase):
    """Linux keycap 表情字体（Noto Color Emoji）的下载、校验与 API 契约。"""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write(self, name: str, data: bytes) -> Path:
        path = self.root / name
        path.write_bytes(data)
        return path

    def test_valid_emoji_font_accepts_true_type_magic(self) -> None:
        """Given 足够大且带 TrueType 魔数的文件, When 校验, Then 判定为有效缓存。"""
        path = self._write("ok.ttf", b"\x00\x01\x00\x00" + b"\0" * 2_000_000)

        self.assertTrue(_valid_emoji_font(path))

    def test_valid_emoji_font_rejects_small_garbage_and_missing(self) -> None:
        """Given 过小 / HTML 错误页 / 不存在的文件, When 校验, Then 全部判定无效。"""
        small = self._write("small.ttf", b"\x00\x01\x00\x00" + b"\0" * 10)
        html = self._write("html.ttf", b"<html>error</html>" + b"\0" * 2_000_000)

        self.assertFalse(_valid_emoji_font(small))
        self.assertFalse(_valid_emoji_font(html))
        self.assertFalse(_valid_emoji_font(self.root / "missing.ttf"))

    def test_emoji_font_urls_default_order_and_env_override(self) -> None:
        """Given 默认配置, When 取下载地址, Then 主 CDN 在前；MAW_EMOJI_FONT_URL 可整体覆盖。"""
        with mock.patch.dict(os.environ, {}, clear=True):
            urls = _emoji_font_urls()
            self.assertIn("https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@main/fonts/NotoColorEmoji.ttf", urls)
            self.assertEqual(urls[0], "https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@main/fonts/NotoColorEmoji.ttf")

        with mock.patch.dict(os.environ, {"MAW_EMOJI_FONT_URL": "https://mirror.example/font.ttf"}, clear=True):
            urls = _emoji_font_urls()
            self.assertEqual(urls[0], "https://mirror.example/font.ttf")
            self.assertIn("https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@main/fonts/NotoColorEmoji.ttf", urls)

    def test_download_emoji_font_success_writes_cache(self) -> None:
        """Given 第一个 URL 返回 200 且体积足够, When 下载, Then 写入 dest 且清理 .part。"""
        dest = self.root / "cache" / "NotoColorEmoji.ttf"
        payload = b"\x00\x01\x00\x00" + b"\0" * 2_000_000

        with mock.patch("maw.gui_web.urlopen", side_effect=[_FakeUrlResponse(200, payload)]):
            result = download_emoji_font(["https://ok.example/font.ttf"], dest, timeout=1)

        self.assertEqual(result, dest)
        self.assertEqual(dest.read_bytes(), payload)
        self.assertFalse((self.root / "cache" / "NotoColorEmoji.ttf.part").exists())

    def test_download_emoji_font_falls_through_failed_urls(self) -> None:
        """Given 首个 URL 抛异常 / 404 / 体积不足, When 下载, Then 依次回退到可用 URL。"""
        dest = self.root / "cache" / "NotoColorEmoji.ttf"
        payload = b"\x00\x01\x00\x00" + b"\0" * 2_000_000

        with mock.patch(
            "maw.gui_web.urlopen",
            side_effect=[URLError("blocked"), _FakeUrlResponse(404, b"nope"), _FakeUrlResponse(200, payload)],
        ):
            result = download_emoji_font(
                ["https://a.example/font.ttf", "https://b.example/font.ttf", "https://c.example/font.ttf"],
                dest,
                timeout=1,
            )

        self.assertEqual(result, dest)
        self.assertEqual(dest.read_bytes(), payload)

    def test_download_emoji_font_all_fail_cleans_partial(self) -> None:
        """Given 所有 URL 都失败, When 下载, Then 返回 None 且不留 .part 残留。"""
        dest = self.root / "cache" / "NotoColorEmoji.ttf"

        with mock.patch("maw.gui_web.urlopen", side_effect=[URLError("blocked"), _FakeUrlResponse(404, b"nope")]):
            result = download_emoji_font(["https://a.example/font.ttf", "https://b.example/font.ttf"], dest, timeout=1)

        self.assertIsNone(result)
        self.assertFalse((self.root / "cache" / "NotoColorEmoji.ttf.part").exists())

    def test_get_emoji_font_path_non_linux_returns_empty(self) -> None:
        """Given Windows/macOS, When 询问字体路径, Then 返回空且不下载。"""
        api = LauncherApi()

        with mock.patch("maw.gui_web.sys.platform", "win32"), mock.patch.object(api, "_start_emoji_font_download") as start:
            result = api.get_emoji_font_path()

        self.assertEqual(result, {"ok": True, "path": ""})
        start.assert_not_called()

    def test_get_emoji_font_path_linux_with_cache_returns_uri(self) -> None:
        """Given Linux 且缓存已存在, When 询问字体路径, Then 直接返回 file:// URI。"""
        api = LauncherApi()
        dest = self.root / "cache" / "NotoColorEmoji.ttf"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"\x00\x01\x00\x00" + b"\0" * 2_000_000)

        with mock.patch("maw.gui_web.sys.platform", "linux"), mock.patch("maw.gui_web._emoji_font_cache_path", return_value=dest):
            result = api.get_emoji_font_path()

        self.assertEqual(result, {"ok": True, "path": dest.as_uri()})

    def test_get_emoji_font_path_linux_missing_starts_background_download(self) -> None:
        """Given Linux 且缓存缺失, When 询问字体路径, Then 返回空并启动后台下载。"""
        api = LauncherApi()
        dest = self.root / "cache" / "NotoColorEmoji.ttf"

        with mock.patch("maw.gui_web.sys.platform", "linux"), mock.patch(
            "maw.gui_web._emoji_font_cache_path", return_value=dest
        ), mock.patch.object(api, "_start_emoji_font_download") as start:
            result = api.get_emoji_font_path()

        self.assertEqual(result, {"ok": True, "path": ""})
        start.assert_called_once_with(dest)

    def test_download_worker_enqueues_ready_event_on_success(self) -> None:
        """Given 下载成功, When 后台线程收尾, Then 向页面推送 emojiFontReady 事件。"""
        api = LauncherApi()
        dest = self.root / "cache" / "NotoColorEmoji.ttf"

        with mock.patch("maw.gui_web.download_emoji_font", return_value=dest):
            api._download_emoji_font_worker(dest)

        event = api.pump.events.get_nowait()
        self.assertEqual(event["type"], "emojiFontReady")
        self.assertEqual(event["path"], dest.as_uri())

    def test_download_worker_is_silent_on_failure(self) -> None:
        """Given 下载失败, When 后台线程收尾, Then 不推送事件（页面回退系统字体）。"""
        api = LauncherApi()

        with mock.patch("maw.gui_web.download_emoji_font", return_value=None):
            api._download_emoji_font_worker(self.root / "missing.ttf")

        self.assertTrue(api.pump.events.empty())

    def test_emoji_font_event_delivered_on_first_launch_when_pump_starts_after_download(self) -> None:
        """Given 首次启动时字体下载在 pump 启动前完成, When pump 启动, Then 事件被送达页面。"""
        window = FakeWindow()
        api = LauncherApi(window_getter=lambda: window)
        dest = self.root / "cache" / "NotoColorEmoji.ttf"

        # 模拟下载在 pump 启动前完成
        with mock.patch("maw.gui_web.download_emoji_font", return_value=dest):
            api._download_emoji_font_worker(dest)

        # 此时事件在队列中，但未送达页面
        self.assertFalse(api.pump.events.empty())
        self.assertEqual(len(window.scripts), 0)

        # 模拟 window.events.loaded 触发，启动 pump
        api.pump.start()

        # 等待 pump flush（pump 每 0.1 秒 flush 一次）
        deadline = time.time() + 2.0
        while time.time() < deadline and len(window.scripts) == 0:
            time.sleep(0.05)

        api.pump.shutdown()

        # 验证事件已送达页面
        self.assertGreater(len(window.scripts), 0)
        self.assertIn("emojiFontReady", window.scripts[-1])
        self.assertIn(dest.as_uri(), window.scripts[-1])


if __name__ == "__main__":
    unittest.main()
