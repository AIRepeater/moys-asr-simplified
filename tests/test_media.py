from __future__ import annotations

import tempfile
import unittest
from unittest import mock
from pathlib import Path

from maw.media import MediaConversionError, MediaStatus, convert_media_for_browser, resolve_project_media


class MediaResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        self.project = self.root / "take.qwen3-asr-api.mosp"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_project_media_field_has_priority(self) -> None:
        media = self.root / "elsewhere.mp4"
        media.write_bytes(b"media")
        result = resolve_project_media(self.project, {"media": str(media)})
        self.assertEqual(result.status, MediaStatus.SUCCESS)
        self.assertEqual(result.resolved_path, media)

    def test_missing_project_media_falls_back_to_one_same_name_candidate(self) -> None:
        media = self.root / "take.flv"
        media.write_bytes(b"media")
        result = resolve_project_media(self.project, {"media": "D:/old/take.mp4"})
        self.assertEqual(result.status, MediaStatus.CONVERSION_NEEDED)
        self.assertEqual(result.resolved_path, media)

    def test_flv_prefers_adjacent_mp4(self) -> None:
        flv = self.root / "take.flv"
        mp4 = self.root / "take.mp4"
        flv.write_bytes(b"flv")
        mp4.write_bytes(b"mp4")

        result = resolve_project_media(self.project, {"media": str(flv)})

        self.assertEqual(result.status, MediaStatus.SUCCESS)
        self.assertEqual(result.requested_path, flv)
        self.assertEqual(result.resolved_path, mp4)

    def test_multiple_same_name_candidates_report_conflict(self) -> None:
        (self.root / "take.mp4").write_bytes(b"mp4")
        (self.root / "take.wav").write_bytes(b"wav")
        result = resolve_project_media(self.project, {"media": "D:/old/take.mp4"})
        self.assertEqual(result.status, MediaStatus.CONFLICT)
        self.assertEqual([path.name for path in result.candidates], ["take.mp4", "take.wav"])

    def test_unknown_existing_extension_is_unsupported(self) -> None:
        media = self.root / "take.xyz"
        media.write_bytes(b"media")
        result = resolve_project_media(self.project, {"media": str(media)})
        self.assertEqual(result.status, MediaStatus.UNSUPPORTED)
        self.assertIsNone(result.resolved_path)

    def test_no_media_is_missing_without_scanning_other_stems(self) -> None:
        (self.root / "other.mp4").write_bytes(b"media")
        result = resolve_project_media(self.project, {"segments": []})
        self.assertEqual(result.status, MediaStatus.MISSING)
        self.assertFalse(result.candidates)

    def test_flv_conversion_uses_ffmpeg_and_caches_result(self) -> None:
        source = self.root / "take.flv"
        source.write_bytes(b"flv")
        ffmpeg = self.root / "ffmpeg.exe"
        ffmpeg.write_bytes(b"exe")
        cache = self.root / "cache"

        def run(command, **kwargs):
            output = Path(command[-1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"mp4")
            return type("Completed", (), {"returncode": 0, "stderr": "", "stdout": ""})()

        with mock.patch("maw.media.subprocess.run", side_effect=run) as process:
            result = convert_media_for_browser(source, ffmpeg_path=ffmpeg, cache_dir=cache)
            again = convert_media_for_browser(source, ffmpeg_path=ffmpeg, cache_dir=cache)

        self.assertEqual(result, again)
        self.assertEqual(result.read_bytes(), b"mp4")
        process.assert_called_once()

    def test_flv_conversion_defaults_to_adjacent_mp4(self) -> None:
        source = self.root / "take.flv"
        source.write_bytes(b"flv")
        ffmpeg = self.root / "ffmpeg.exe"
        ffmpeg.write_bytes(b"exe")

        def run(command, **kwargs):
            output = Path(command[-1])
            output.write_bytes(b"mp4")
            return type("Completed", (), {"returncode": 0, "stderr": "", "stdout": ""})()

        with mock.patch("maw.media.subprocess.run", side_effect=run) as process:
            result = convert_media_for_browser(source, ffmpeg_path=ffmpeg)

        self.assertEqual(result, self.root / "take.mp4")
        self.assertTrue(result.is_file())
        self.assertFalse(list(self.root.glob("take.part-*.mp4")))
        process.assert_called_once()

    def test_flv_conversion_rejects_nonzero_ffmpeg_output_and_cleans_temp(self) -> None:
        source = self.root / "take.flv"
        source.write_bytes(b"flv")
        ffmpeg = self.root / "ffmpeg.exe"
        ffmpeg.write_bytes(b"exe")

        def run(command, **kwargs):
            Path(command[-1]).write_bytes(b"partial")
            return type("Completed", (), {"returncode": 1, "stderr": "bad input", "stdout": ""})()

        with mock.patch("maw.media.subprocess.run", side_effect=run) as process:
            with self.assertRaisesRegex(MediaConversionError, "退出码 1"):
                convert_media_for_browser(source, ffmpeg_path=ffmpeg)

        self.assertFalse((self.root / "take.mp4").exists())
        self.assertFalse(list(self.root.glob("take.part-*.mp4")))
        self.assertEqual(process.call_count, 2)

    def test_flv_conversion_reports_missing_ffmpeg(self) -> None:
        source = self.root / "take.flv"
        source.write_bytes(b"flv")
        with mock.patch("maw.media.shutil.which", return_value=None):
            with self.assertRaises(MediaConversionError):
                convert_media_for_browser(source, cache_dir=self.root / "cache")


if __name__ == "__main__":
    unittest.main()
