from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from maw.gui_web import LauncherApi, LauncherPaths  # noqa: E402
from maw.gui_workflow import TranscriptionRequest, TranscriptionResult  # noqa: E402
from maw.launcher_batch import BatchItem, manifest_payload, run_batch  # noqa: E402


class BatchRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _items(self, count: int = 3) -> tuple[BatchItem, ...]:
        items = []
        for index in range(count):
            media = self.root / f"clip-{index}.mp3"
            media.write_bytes(b"media")
            items.append(BatchItem(str(index), TranscriptionRequest(media, self.root / f"clip-{index}.srt")))
        return tuple(items)

    def test_runner_is_fifo_and_never_overlaps(self) -> None:
        active = 0
        max_active = 0
        started: list[str] = []

        def transcribe(request: TranscriptionRequest, *, cancel_event: threading.Event) -> TranscriptionResult:
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            started.append(request.media_path.stem)
            time.sleep(0.001)
            active -= 1
            return TranscriptionResult(request.srt_path)

        result = run_batch(self._items(), settings={"model": "shared"}, manifest_path=self.root / "manifest.json", cancel_event=threading.Event(), transcribe=transcribe)

        self.assertEqual(started, ["clip-0", "clip-1", "clip-2"])
        self.assertEqual(max_active, 1)
        self.assertEqual([item["status"] for item in result["outcomes"]], ["done"] * 3)

    def test_failure_isolated_and_later_item_runs(self) -> None:
        started: list[str] = []

        def transcribe(request: TranscriptionRequest, *, cancel_event: threading.Event) -> TranscriptionResult:
            started.append(request.media_path.stem)
            if request.media_path.stem == "clip-1":
                raise RuntimeError("provider failed")
            return TranscriptionResult(request.srt_path)

        result = run_batch(self._items(), settings={}, manifest_path=self.root / "manifest.json", cancel_event=threading.Event(), transcribe=transcribe)

        self.assertEqual(started, ["clip-0", "clip-1", "clip-2"])
        self.assertEqual([item["status"] for item in result["outcomes"]], ["done", "failed", "done"])
        self.assertEqual(result["outcomes"][1]["error"], "provider failed")

    def test_cancel_marks_remaining_items_without_running_them(self) -> None:
        cancel = threading.Event()
        started: list[str] = []

        def transcribe(request: TranscriptionRequest, *, cancel_event: threading.Event) -> TranscriptionResult:
            started.append(request.media_path.stem)
            cancel.set()
            return TranscriptionResult(request.srt_path)

        result = run_batch(self._items(), settings={}, manifest_path=self.root / "manifest.json", cancel_event=cancel, transcribe=transcribe)

        self.assertEqual(started, ["clip-0"])
        self.assertEqual([item["status"] for item in result["outcomes"]], ["done", "cancelled", "cancelled"])
        self.assertEqual(result["status"], "cancelled")

    def test_batch_allocates_duplicate_requested_outputs(self) -> None:
        requested = self.root / "same.srt"
        items = tuple(BatchItem(str(index), TranscriptionRequest(self.root / f"clip-{index}.mp3", requested)) for index in range(2))
        for item in items:
            item.request.media_path.write_bytes(b"media")

        seen: list[Path] = []

        def transcribe(request: TranscriptionRequest, *, cancel_event: threading.Event) -> TranscriptionResult:
            seen.append(request.srt_path)
            return TranscriptionResult(request.srt_path)

        run_batch(items, settings={}, manifest_path=self.root / "manifest.json", cancel_event=threading.Event(), transcribe=transcribe)

        self.assertEqual(len(set(seen)), 2)

    def test_manifest_excludes_secrets(self) -> None:
        manifest = manifest_payload(self._items(1), {"apiKey": "secret", "nested": {"token": "private", "model": "qwen"}})

        text = json.dumps(manifest)
        self.assertNotIn("secret", text)
        self.assertNotIn("private", text)
        self.assertIn("qwen", text)

    def test_manifest_records_per_item_outcomes_atomically(self) -> None:
        item = self._items(1)[0]
        result = run_batch((item,), settings={}, manifest_path=self.root / "nested" / "manifest.json", cancel_event=threading.Event(), transcribe=lambda request, *, cancel_event: TranscriptionResult(request.srt_path))

        manifest = json.loads((self.root / "nested" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "done")
        self.assertEqual(manifest["outcomes"], result["outcomes"])
        self.assertEqual(list((self.root / "nested").glob("*.tmp")), [])

    def test_preflight_failure_isolated_to_one_item(self) -> None:
        valid = self._items(2)
        raw = (
            BatchItem("bad", None, "Media file does not exist."),
            valid[1],
        )
        started: list[str] = []

        def transcribe(request: TranscriptionRequest, *, cancel_event: threading.Event) -> TranscriptionResult:
            started.append(request.media_path.stem)
            return TranscriptionResult(request.srt_path)

        result = run_batch(raw, settings={}, manifest_path=self.root / "manifest.json", cancel_event=threading.Event(), transcribe=transcribe)

        self.assertEqual(started, ["clip-1"])
        self.assertEqual([item["status"] for item in result["outcomes"]], ["failed", "done"])

    def test_request_none_without_preflight_error_is_isolated(self) -> None:
        valid = self._items(1)[0]
        started: list[str] = []

        def transcribe(request: TranscriptionRequest, *, cancel_event: threading.Event) -> TranscriptionResult:
            started.append(request.media_path.stem)
            return TranscriptionResult(request.srt_path)

        result = run_batch((BatchItem("invalid", None), valid), settings={}, manifest_path=self.root / "manifest.json", cancel_event=threading.Event(), transcribe=transcribe)

        self.assertEqual(started, ["clip-0"])
        self.assertEqual([item["status"] for item in result["outcomes"]], ["failed", "done"])
        self.assertTrue(result["outcomes"][0]["error"])

    def test_outcome_only_reports_srt_path(self) -> None:
        def transcribe(request: TranscriptionRequest, *, cancel_event: threading.Event) -> TranscriptionResult:
            return TranscriptionResult(request.srt_path)

        result = run_batch(self._items(1), settings={}, manifest_path=self.root / "manifest.json", cancel_event=threading.Event(), transcribe=transcribe)

        outcome = result["outcomes"][0]
        self.assertEqual(outcome["srtPath"], str(self.root / "clip-0.srt"))
        self.assertNotIn("jsonPath", outcome)
        self.assertNotIn("htmlPath", outcome)


class BatchApiTests(unittest.TestCase):
    @staticmethod
    def _blocked_batch_runner(error: Exception | None = None) -> tuple[threading.Event, threading.Event, object]:
        started = threading.Event()
        release = threading.Event()

        def run_batch(*_args: object, **_kwargs: object) -> None:
            started.set()
            release.wait(timeout=5)
            if error is not None:
                raise error

        return started, release, run_batch

    def test_choose_file_returns_all_paths_for_multiple(self) -> None:
        api = LauncherApi(paths=LauncherPaths(Path("."), Path(".env"), Path("launcher.html")), window_getter=lambda: None)
        with mock.patch("maw.gui_web._file_dialog", return_value=("a.mp3", "b.mp3")):
            result = api.choose_file({"kind": "media", "multiple": True})
        self.assertEqual(result, {"ok": True, "path": "a.mp3", "paths": ["a.mp3", "b.mp3"]})
        api.shutdown()

    def test_start_and_cancel_batch_api_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            media = root / "clip.mp3"
            media.write_bytes(b"media")
            api = LauncherApi(paths=LauncherPaths(root, root / ".env", root / "launcher.html"), window_getter=lambda: None)
            with mock.patch("maw.gui_web._request_from_payload") as request_from_payload:
                request_from_payload.return_value = TranscriptionRequest(media, root / "clip.srt")
                with mock.patch("maw.gui_web.run_batch") as run_batch:
                    run_batch.side_effect = lambda *args, **kwargs: None
                    result = api.start_batch_transcription({"items": [{"id": "a", "mediaPath": str(media), "srtPath": str(root / "clip.srt")}], "apiKey": "secret"})
                    self.assertTrue(result["ok"])
                    self.assertEqual(result["itemCount"], 1)
                    cancel_result = api.cancel_batch_transcription()
                    self.assertTrue(cancel_result["ok"])
            api.shutdown()

    def test_start_batch_derives_output_path_when_item_omits_srt_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            media = root / "clip.mp3"
            media.write_bytes(b"media")
            api = LauncherApi(paths=LauncherPaths(root, root / ".env", root / "launcher.html"), window_getter=lambda: None)
            started, release, runner = self._blocked_batch_runner()
            with mock.patch("maw.gui_web.run_batch", side_effect=runner) as run_batch:
                result = api.start_batch_transcription({"items": [{"id": "a", "mediaPath": str(media)}], "apiKey": "secret"})
                self.assertTrue(result["ok"])
                self.assertTrue(started.wait(timeout=5))
                worker = api.batch_worker
                self.assertIsNotNone(worker)
                release.set()
                assert worker is not None
                worker.join(timeout=5)
                items = run_batch.call_args.args[0]
                self.assertEqual(items[0].request.srt_path, root / "clip.qwen-audio.srt")
            api.shutdown()

    def test_batch_main_emits_done_event_when_runner_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            media = root / "clip.mp3"
            media.write_bytes(b"media")
            api = LauncherApi(paths=LauncherPaths(root, root / ".env", root / "launcher.html"), window_getter=lambda: None)
            started, release, runner = self._blocked_batch_runner(RuntimeError("worker exploded"))
            with mock.patch.object(api, "_emit") as emit, mock.patch("maw.gui_web.run_batch", side_effect=runner):
                result = api.start_batch_transcription({"items": [{"id": "a", "mediaPath": str(media), "srtPath": str(root / "clip.srt")}], "apiKey": "secret"})
                self.assertTrue(result["ok"])
                self.assertTrue(started.wait(timeout=5))
                worker = api.batch_worker
                self.assertIsNotNone(worker)
                release.set()
                assert worker is not None
                worker.join(timeout=5)
                self.assertIsNone(api.batch_worker)
                self.assertTrue(any(call.args[0].get("type") == "batch_done" and call.args[0].get("status") == "failed" and "worker exploded" in str(call.args[0].get("error")) for call in emit.call_args_list))
            api.shutdown()

    def test_batch_default_manifest_path_avoids_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            media = root / "clip.mp3"
            media.write_bytes(b"media")
            existing = root / "maw-batch-manifest.json"
            existing.write_text("existing", encoding="utf-8")
            api = LauncherApi(paths=LauncherPaths(root, root / ".env", root / "launcher.html"), window_getter=lambda: None)
            with mock.patch("maw.gui_web._request_from_payload", return_value=TranscriptionRequest(media, root / "clip.srt")), mock.patch("maw.gui_web.run_batch"):
                result = api.start_batch_transcription({"items": [{"id": "a", "mediaPath": str(media), "srtPath": str(root / "clip.srt")}], "apiKey": "secret"})
            self.assertTrue(result["ok"])
            self.assertEqual(result["manifestPath"], str(root / "maw-batch-manifest-1.json"))
            api.shutdown()


if __name__ == "__main__":
    unittest.main()
