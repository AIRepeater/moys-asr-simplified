# pyright: reportImplicitOverride=false, reportPrivateUsage=false, reportUnannotatedClassAttribute=false, reportUninitializedInstanceVariable=false, reportUnusedCallResult=false, reportUnusedParameter=false

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from threading import Event
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from maw.gui_workflow import (  # noqa: E402
    TranscriptionProcessError,
    TranscriptionRequest,
    build_output_paths,
    build_transcribe_command,
    raw_response_path,
    unique_output_path,
    _child_environment,
    _decode_process_output,
    run_transcription,
)
from maw.gui_platform import _terminate_registered_job, terminate_process_tree  # noqa: E402


class GuiWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        # Windows CI may expose %TEMP% as an 8.3 short path while production code resolves it.
        self.root = Path(self.temp_dir.name).resolve()
        self.media_path = self.root / "clip.mp3"
        self.media_path.write_bytes(b"placeholder")
        self.srt_path = self.root / "out.srt"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_output_paths_derive_exact_srt_path(self) -> None:
        paths = build_output_paths(self.srt_path)

        self.assertEqual(paths.srt, self.srt_path)

    def test_unique_output_path_adds_suffix_for_existing_output(self) -> None:
        self.srt_path.write_text("1\n", encoding="utf-8")

        self.assertEqual(unique_output_path(self.srt_path), self.root / "out-1.srt")

        self.srt_path.with_name("out-1.srt").write_text("1\n", encoding="utf-8")
        self.assertEqual(unique_output_path(self.srt_path), self.root / "out-2.srt")

    def test_build_transcribe_command_source_mode_uses_qwen_script(self) -> None:
        request = TranscriptionRequest(
            media_path=self.media_path,
            srt_path=self.srt_path,
            model="qwen3-asr-flash-filetrans",
            language="zh",
            api_key="secret-key",
        )

        command = build_transcribe_command(request, executable=Path("python.exe"), frozen=False)

        self.assertEqual(command[0], "python.exe")
        self.assertIn("generate_subtitle_qwen_api.py", command[1])
        self.assertEqual(command[2], str(self.media_path))
        self.assertEqual(command[command.index("--output") + 1], str(self.srt_path))
        self.assertEqual(command[command.index("--model") + 1], "qwen3-asr-flash-filetrans")
        self.assertEqual(command[command.index("--language") + 1], "zh")
        self.assertNotIn("--json", command)
        self.assertNotIn("--no-html", command)
        self.assertNotIn("--with-waveform", command)
        self.assertNotIn("secret-key", " ".join(command))

    def test_build_transcribe_command_passes_segmentation_options(self) -> None:
        request = TranscriptionRequest(
            media_path=self.media_path,
            srt_path=self.srt_path,
            max_len="14",
            min_len="3",
            gap_split="800",
        )

        command = build_transcribe_command(request, executable=Path("python.exe"), frozen=False)

        self.assertEqual(command[command.index("--max-len") + 1], "14")
        self.assertEqual(command[command.index("--min-len") + 1], "3")
        self.assertEqual(command[command.index("--gap-split") + 1], "800")

    def test_build_transcribe_command_debug_raw_saves_full_response(self) -> None:
        request = TranscriptionRequest(
            media_path=self.media_path,
            srt_path=self.srt_path,
            debug_raw=True,
        )

        command = build_transcribe_command(request, executable=Path("python.exe"), frozen=False)

        self.assertIn("--debug-raw", command)
        self.assertEqual(raw_response_path(self.srt_path), self.srt_path.with_suffix(".asr-response.json"))

    def test_build_transcribe_command_speaker_appends_flag(self) -> None:
        request = TranscriptionRequest(
            media_path=self.media_path,
            srt_path=self.srt_path,
            speaker=True,
        )

        command = build_transcribe_command(request, executable=Path("python.exe"), frozen=False)

        self.assertIn("--speaker", command)
        self.assertNotIn("--speaker-colors", command)

    def test_build_transcribe_command_qwen_audio_passes_one_shot_context_hotwords_and_vocabulary(self) -> None:
        request = TranscriptionRequest(
            media_path=self.media_path,
            srt_path=self.srt_path,
            model="qwen-audio-3.0-asr-flash-filetrans",
            qwen_audio_context="产品名和专业术语",
            qwen_audio_hotwords="张三\n李四,阿里云",
            qwen_audio_vocabulary_id="vocab-qwen-audio",
            qwen_audio_hotword_weight="50",
        )

        command = build_transcribe_command(request, executable=Path("python.exe"), frozen=False)

        self.assertEqual(command[command.index("--context") + 1], "产品名和专业术语")
        self.assertEqual(command[command.index("--vocabulary-id") + 1], "vocab-qwen-audio")
        self.assertEqual(command[command.index("--hotword-weight") + 1], "50")
        hotword_positions = [index for index, value in enumerate(command) if value == "--hotword"]
        self.assertEqual([command[index + 1] for index in hotword_positions], ["张三", "李四", "阿里云"])

    def test_build_transcribe_command_qwen_audio_uses_hotword_file_mode(self) -> None:
        hotwords_file = self.root / "hotwords.txt"
        hotwords_file.write_text("张三\n阿里云\n", encoding="utf-8")
        request = TranscriptionRequest(
            media_path=self.media_path,
            srt_path=self.srt_path,
            model="qwen-audio-3.0-asr-flash-filetrans",
            qwen_audio_hotwords_file=str(hotwords_file),
            qwen_audio_hotwords="不会被使用",
        )

        command = build_transcribe_command(request, executable=Path("python.exe"), frozen=False)

        self.assertEqual(command[command.index("--hotword-file") + 1], str(hotwords_file))
        self.assertNotIn("--hotword", command)

    def test_build_transcribe_command_frozen_mode_dispatches_same_executable(self) -> None:
        request = TranscriptionRequest(media_path=self.media_path, srt_path=self.srt_path)

        command = build_transcribe_command(request, executable=Path("MAW.exe"), frozen=True)

        self.assertEqual(command[:3], ["MAW.exe", "--transcribe", str(self.media_path)])
        self.assertNotIn("--json", command)
        self.assertNotIn("--with-waveform", command)

    def test_build_transcribe_command_funasr_uses_dashscope_script(self) -> None:
        request = TranscriptionRequest(
            media_path=self.media_path,
            srt_path=self.srt_path,
            provider="qwen",
            model="fun-asr",
            language="zh",
            region="beijing",
        )

        command = build_transcribe_command(
            request,
            executable=Path("python.exe"),
            frozen=False,
        )

        self.assertIn("generate_subtitle_qwen_api.py", command[1])
        self.assertEqual(command[command.index("--model") + 1], "fun-asr")
        self.assertEqual(command[command.index("--language") + 1], "zh")
        self.assertEqual(command[command.index("--region") + 1], "beijing")
        self.assertNotIn("--speaker-colors", command)

    def test_run_transcription_passes_api_key_only_in_child_environment(self) -> None:
        request = TranscriptionRequest(
            media_path=self.media_path,
            srt_path=self.srt_path,
            api_key="secret-key",
            workspace_id="workspace-123",
        )
        self.srt_path.write_text("1\n", encoding="utf-8")
        events: list[str] = []

        class FakeProcess:
            returncode = 0
            stdout = ["started\n", "done\n"]

            def poll(self) -> int | None:
                return 0

            def wait(self, timeout: float | None = None) -> int:
                return 0

        with mock.patch("maw.gui_workflow.popen_process_tree", return_value=FakeProcess()) as popen:
            result = run_transcription(request, on_event=events.append)

        kwargs = popen.call_args.kwargs
        self.assertEqual(kwargs["env"]["DASHSCOPE_API_KEY"], "secret-key")
        self.assertEqual(kwargs["env"]["DASHSCOPE_WORKSPACE_ID"], "workspace-123")
        self.assertNotEqual(os.environ.get("DASHSCOPE_API_KEY"), "secret-key")
        self.assertEqual(events, ["started", "done"])
        self.assertEqual(result.srt_path, self.srt_path)
        self.assertIsNone(result.raw_path)

    def test_terminate_process_tree_uses_windows_taskkill_for_descendants(self) -> None:
        class FakeProcess:
            pid = 4321
            returncode: int | None = None

            def poll(self) -> int | None:
                return self.returncode

            def wait(self, timeout: float | None = None) -> int:
                self.returncode = 0
                return 0

            def terminate(self) -> None:
                self.returncode = -15

            def kill(self) -> None:
                self.returncode = -9

        fake = FakeProcess()
        with mock.patch("maw.gui_platform.sys.platform", "win32"):
            with mock.patch("maw.gui_platform.subprocess.run", return_value=mock.Mock(returncode=0)) as taskkill:
                terminate_process_tree(fake)

        taskkill.assert_called_once()
        self.assertEqual(taskkill.call_args.args[0], ["taskkill", "/PID", "4321", "/T", "/F"])

    def test_terminate_process_tree_reaps_an_already_exited_root(self) -> None:
        class FakeProcess:
            pid = 4321
            returncode: int | None = 0
            waited = False

            def poll(self) -> int | None:
                return self.returncode

            def wait(self, timeout: float | None = None) -> int:
                self.waited = True
                return 0

        fake = FakeProcess()
        with mock.patch("maw.gui_platform.sys.platform", "win32"):
            terminate_process_tree(fake)

        self.assertTrue(fake.waited)

    def test_terminate_registered_windows_job_closes_handle_after_kill(self) -> None:
        fake = mock.Mock()
        fake._maw_job_handle = 123
        kernel32 = mock.Mock()
        kernel32.TerminateJobObject.return_value = 1

        with mock.patch("maw.gui_platform.sys.platform", "win32"):
            with mock.patch("ctypes.WinDLL", return_value=kernel32, create=True):
                self.assertTrue(_terminate_registered_job(fake))

        kernel32.TerminateJobObject.assert_called_once_with(123, 1)
        kernel32.CloseHandle.assert_called_once_with(123)
        self.assertIsNone(fake._maw_job_handle)

    def test_decode_process_output_accepts_utf8_and_bom(self) -> None:
        self.assertEqual(_decode_process_output("已开始\n"), "已开始\n")
        self.assertEqual(
            _decode_process_output(b"\xef\xbb\xbf\xe5\xb7\xb2\xe5\xbc\x80\xe5\xa7\x8b\n"),
            "已开始\n",
        )

    def test_decode_process_output_falls_back_to_windows_gbk(self) -> None:
        value = "上传失败：文件格式不支持\n".encode("cp936")
        self.assertEqual(_decode_process_output(value), "上传失败：文件格式不支持\n")

    def test_child_environment_forces_unbuffered_python_stdout(self) -> None:
        env = _child_environment({"PYTHONUNBUFFERED": "0"}, "secret-key", "workspace-123")

        self.assertEqual(env["PYTHONUNBUFFERED"], "1")
        self.assertEqual(env["PYTHONUTF8"], "1")
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8:replace")
        self.assertEqual(env["DASHSCOPE_API_KEY"], "secret-key")
        self.assertEqual(env["DASHSCOPE_WORKSPACE_ID"], "workspace-123")

    def test_child_environment_prepends_ffmpeg_path_directory(self) -> None:
        ffmpeg_dir = self.root / "ffmpeg" / "bin"
        ffmpeg_dir.mkdir(parents=True)
        ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"
        ffmpeg_exe.write_bytes(b"exe")

        env = _child_environment({"PATH": "C:\\Windows", "FFMPEG_PATH": str(ffmpeg_exe)}, "", "")

        self.assertEqual(env["PATH"].split(os.pathsep)[0], str(ffmpeg_dir))

    def test_child_environment_uses_bundled_ffmpeg_when_no_path_is_configured(self) -> None:
        ffmpeg_dir = self.root / "ffmpeg" / "bin"
        ffmpeg_dir.mkdir(parents=True)
        (ffmpeg_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")).write_bytes(b"exe")
        (ffmpeg_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe")).write_bytes(b"exe")

        with mock.patch("maw.gui_workflow.asset_path", return_value=ffmpeg_dir):
            with mock.patch("maw.gui_workflow.load_env", return_value={}):
                env = _child_environment({"PATH": "C:\\Windows"}, "", "")

        self.assertEqual(env["PATH"].split(os.pathsep)[0], str(ffmpeg_dir))

    def test_child_environment_uses_release_root_ffmpeg_in_frozen_mode(self) -> None:
        app_root = self.root / "MAW"
        ffmpeg_dir = app_root / "ffmpeg" / "bin"
        ffmpeg_dir.mkdir(parents=True)
        (ffmpeg_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")).write_bytes(b"exe")
        (ffmpeg_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe")).write_bytes(b"exe")

        with mock.patch("maw.gui_workflow.sys.frozen", True, create=True):
            with mock.patch("maw.gui_workflow.sys.executable", str(app_root / "MAW.exe")):
                with mock.patch("maw.gui_workflow.load_env", return_value={}):
                    env = _child_environment({"PATH": "C:\\Windows"}, "", "")

        self.assertEqual(env["PATH"].split(os.pathsep)[0], str(ffmpeg_dir))

    def test_child_environment_appends_macos_candidate_directories(self) -> None:
        with mock.patch.object(sys, "platform", "darwin"):
            with mock.patch("maw.gui_workflow.MACOS_FFMPEG_CANDIDATE_DIRECTORIES", ("/opt/homebrew/bin", "/usr/local/bin")):
                with mock.patch("maw.gui_workflow.load_env", return_value={}):
                    with mock.patch("maw.gui_workflow._bundled_ffmpeg_directory", return_value=None):
                        env = _child_environment({"PATH": "/usr/bin"}, "", "")

        self.assertEqual(
            env["PATH"].split(os.pathsep),
            ["/usr/bin", "/opt/homebrew/bin", "/usr/local/bin"],
        )

    def test_run_transcription_reports_child_pid_after_popen(self) -> None:
        request = TranscriptionRequest(media_path=self.media_path, srt_path=self.srt_path)
        self.srt_path.write_text("1\n", encoding="utf-8")
        started: list[int] = []

        class FakeProcess:
            pid = 4321
            returncode = 0
            stdout = []

            def poll(self) -> int | None:
                return 0

            def wait(self, timeout: float | None = None) -> int:
                return 0

        with mock.patch("maw.gui_workflow.popen_process_tree", return_value=FakeProcess()):
            run_transcription(request, on_process_start=started.append)

        self.assertEqual(started, [4321])

    def test_run_transcription_failure_carries_child_output(self) -> None:
        request = TranscriptionRequest(media_path=self.media_path, srt_path=self.srt_path)
        events: list[str] = []

        class FakeProcess:
            pid = 4321
            returncode = 1
            stdout = ["[info] 提交任务...\n".encode(), "错误: 未识别到任何内容\n".encode()]

            def poll(self) -> int | None:
                return 1

            def wait(self, timeout: float | None = None) -> int:
                return 1

        with mock.patch("maw.gui_workflow.popen_process_tree", return_value=FakeProcess()):
            with self.assertRaises(TranscriptionProcessError) as raised:
                run_transcription(request, on_event=events.append)

        self.assertEqual(raised.exception.exit_code, 1)
        self.assertTrue(any("未识别到任何内容" in line for line in raised.exception.output))
        self.assertIn("未识别到任何内容", str(raised.exception))
        self.assertTrue(any("提交任务" in event for event in events))

    def test_run_transcription_cancels_running_process(self) -> None:
        request = TranscriptionRequest(media_path=self.media_path, srt_path=self.srt_path)
        cancel_event = Event()
        cancel_event.set()

        class FakeProcess:
            returncode = None
            stdout = []
            terminated = False

            def poll(self) -> int | None:
                return None

            def terminate(self) -> None:
                self.terminated = True

            def wait(self, timeout: float | None = None) -> int:
                self.returncode = -15
                return -15

            def kill(self) -> None:
                self.returncode = -9

        fake = FakeProcess()
        with mock.patch("maw.gui_workflow.popen_process_tree", return_value=fake) as popen:
            with self.assertRaises(Exception) as raised:
                run_transcription(request, cancel_event=cancel_event)

        popen.assert_not_called()
        self.assertFalse(fake.terminated)
        self.assertIn("cancelled", str(raised.exception).lower())

    def test_run_transcription_cancels_quiet_process_promptly(self) -> None:
        request = TranscriptionRequest(media_path=self.media_path, srt_path=self.srt_path)
        cancel_event = Event()
        outcome: list[BaseException] = []
        release_stdout = Event()

        class QuietStdout:
            def __iter__(self) -> "QuietStdout":
                return self

            def __next__(self) -> str:
                release_stdout.wait()
                raise StopIteration

        class QuietProcess:
            returncode = None
            stdout = QuietStdout()

            def poll(self) -> int | None:
                return self.returncode

            def wait(self, timeout: float | None = None) -> int:
                self.returncode = 0
                return 0

            def terminate(self) -> None:
                self.returncode = -15
                release_stdout.set()

            def kill(self) -> None:
                self.returncode = -9
                release_stdout.set()

        def run() -> None:
            try:
                run_transcription(request, cancel_event=cancel_event)
            except BaseException as exc:
                outcome.append(exc)

        with mock.patch("maw.gui_workflow.popen_process_tree", return_value=QuietProcess()):
            worker = threading.Thread(target=run)
            worker.start()
            time.sleep(0.2)
            cancel_event.set()
            worker.join(timeout=0.5)
            ignored_cancellation = worker.is_alive()
            release_stdout.set()
            worker.join(timeout=1)

        self.assertFalse(ignored_cancellation, "quiet subprocess ignored cancellation")
        self.assertEqual(len(outcome), 1)
        self.assertIn("cancelled", str(outcome[0]).lower())

    def test_default_srt_path_uses_provider_tag(self) -> None:
        from maw.gui_workflow import default_srt_path

        self.assertEqual(default_srt_path(Path("clip.mp4")).name, "clip.qwen-audio.srt")
        self.assertEqual(
            default_srt_path(Path("clip.mp4"), model="fun-asr").name,
            "clip.fun-asr.srt",
        )
        self.assertEqual(
            default_srt_path(Path("clip.mp4"), model="qwen3-asr-flash-filetrans").name,
            "clip.qwen3-asr-api.srt",
        )
        self.assertEqual(
            default_srt_path(Path("clip.mp4"), test_run=True).name,
            "clip.qwen-audio-test.srt",
        )

    def test_entrypoint_smoke_import_argument_does_not_open_window(self) -> None:
        import maw_gui

        with mock.patch("maw.gui_web.run_app") as run_app, mock.patch("maw_gui.configure_utf8_stdio") as configure:
            exit_code = maw_gui.main(["--smoke-import"])

        self.assertEqual(exit_code, 0)
        run_app.assert_not_called()
        configure.assert_called_once_with()

    def test_entrypoint_debug_aliases_configure_launcher_debug_modes(self) -> None:
        import maw_gui

        for argv, expected in (
            (["-dbg"], mock.call(debug=True, devtools=False)),
            (["--debug"], mock.call(debug=True, devtools=False)),
            (["-dt"], mock.call(debug=True, devtools=True)),
            (["--devtools"], mock.call(debug=True, devtools=True)),
        ):
            with self.subTest(argv=argv), mock.patch("maw.gui_web.run_app") as run_app:
                self.assertEqual(maw_gui.main(argv), 0)
                run_app.assert_called_once_with(**expected.kwargs)

    def test_entrypoint_help_subprocess_is_headless_safe(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "maw_gui.py"), "--help"],
            check=False,
            capture_output=True,
        )
        stdout = completed.stdout.decode("utf-8", errors="replace")

        self.assertEqual(completed.returncode, 0)
        self.assertIn("Moy's ASR Workflow GUI", stdout)
        self.assertNotIn("--serve", stdout)


if __name__ == "__main__":
    unittest.main()
