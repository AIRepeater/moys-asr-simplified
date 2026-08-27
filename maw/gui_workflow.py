# pyright: reportAny=false, reportUnusedCallResult=false

from __future__ import annotations

import locale
import os
import queue
import subprocess
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import BinaryIO, Final, TextIO, final

from maw.console import configure_utf8_environment
from maw.gui_config import QWEN_AUDIO_MODEL_ID, DEFAULT_MODEL_ID, DEFAULT_ENV_PATH, load_env
from maw.gui_platform import asset_path, popen_process_tree, process_group_kwargs, release_process_tree, terminate_process_tree
from maw.qwen_audio import split_qwen_audio_hotwords


@dataclass(frozen=True, slots=True)
class OutputPaths:
    srt: Path


@dataclass(frozen=True, slots=True)
class TranscriptionRequest:
    media_path: Path
    srt_path: Path
    model: str = DEFAULT_MODEL_ID
    language: str = ""
    api_key: str = ""
    length_limit: str = ""
    max_len: str = ""
    min_len: str = ""
    gap_split: str = ""
    qwen_audio_context: str = ""
    qwen_audio_hotwords: str = ""
    qwen_audio_hotwords_file: str = ""
    qwen_audio_vocabulary_id: str = ""
    qwen_audio_hotword_weight: str = ""
    region: str = ""
    workspace_id: str = ""
    provider: str = "qwen"
    speaker_colors: bool = False
    ui_language: str = "zh"
    debug_raw: bool = False


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    srt_path: Path
    raw_path: Path | None = None


ProgressCallback = Callable[[str], None]
ProcessStartCallback = Callable[[int], None]


MACOS_FFMPEG_CANDIDATE_DIRECTORIES: Final[tuple[str, ...]] = (
    "/opt/homebrew/bin",
    "/usr/local/bin",
)


@final
class TranscriptionCancelledError(Exception):
    """Raised after a user requests cancellation."""

    def __init__(self) -> None:
        super().__init__("Transcription cancelled")


@final
class TranscriptionProcessError(Exception):
    """Raised when the transcription subprocess exits unsuccessfully."""

    exit_code: int
    output: tuple[str, ...]

    def __init__(self, exit_code: int, output: Sequence[str] = ()) -> None:
        self.exit_code = exit_code
        self.output = tuple(output)
        detail = _tail_output(self.output)
        message = f"Transcription failed with exit code {exit_code}"
        if detail:
            message += f": {detail}"
        super().__init__(message)


def _tail_output(output: Sequence[str], limit: int = 1) -> str:
    """取子进程失败输出的最后若干行，用于透传具体失败原因。"""
    lines = [line.strip() for line in output if line.strip()]
    if not lines:
        return ""
    return " | ".join(lines[-limit:])


@final
class MissingOutputError(Exception):
    """Raised when a successful child process omits a promised artifact."""

    label: str
    path: Path

    def __init__(self, label: str, path: Path) -> None:
        self.label = label
        self.path = path
        super().__init__(f"{label} output was not created: {path}")


def build_output_paths(srt_path: Path) -> OutputPaths:
    srt = Path(srt_path).expanduser().resolve()
    return OutputPaths(srt=srt)


def raw_response_path(srt_path: Path) -> Path:
    return Path(srt_path).expanduser().resolve().with_suffix(".asr-response.json")


def unique_output_path(srt_path: Path) -> Path:
    """为已有输出选择一个不会覆盖文件的新路径。"""
    original = Path(srt_path).expanduser()

    def occupied(candidate: Path) -> bool:
        return build_output_paths(candidate).srt.exists()

    if not occupied(original):
        return original

    index = 1
    while True:
        candidate = original.with_name(f"{original.stem}-{index}{original.suffix}")
        if not occupied(candidate):
            return candidate
        index += 1


PROVIDER_SRT_TAGS: Final = {
    "qwen": ".qwen3-asr-api",
}


def with_test_suffix(path: Path) -> Path:
    """Append the test marker before the extension without duplicating it."""
    path = Path(path)
    if path.stem.lower().endswith("-test"):
        return path
    return path.with_name(f"{path.stem}-test{path.suffix}")


def default_srt_path(
    media_path: Path,
    provider: str = "qwen",
    model: str = DEFAULT_MODEL_ID,
    test_run: bool = False,
) -> Path:
    media = Path(media_path).expanduser()
    if provider == "qwen" and model.startswith("fun-asr"):
        tag = ".fun-asr"
    elif provider == "qwen" and model == QWEN_AUDIO_MODEL_ID:
        tag = ".qwen-audio"
    else:
        tag = PROVIDER_SRT_TAGS.get(provider, PROVIDER_SRT_TAGS["qwen"])
    output = media.with_name(f"{media.stem}{tag}.srt")
    return with_test_suffix(output) if test_run else output


def build_transcribe_command(
    request: TranscriptionRequest,
    *,
    executable: Path | str | None = None,
    frozen: bool | None = None,
) -> list[str]:
    exe = str(executable or sys.executable)
    is_frozen = bool(getattr(sys, "frozen", False) if frozen is None else frozen)
    script = Path(__file__).resolve().parents[1] / "generate_subtitle_qwen_api.py"
    if is_frozen:
        command = [exe, "--transcribe"]
    else:
        command = [exe, str(script)]
    command.append(str(request.media_path))
    command.extend(["--output", str(build_output_paths(request.srt_path).srt)])
    if request.debug_raw:
        command.append("--debug-raw")
    _append_option(command, "--model", request.model or DEFAULT_MODEL_ID)
    _append_option(command, "--region", request.region)
    if request.speaker_colors and (
        request.model.startswith("fun-asr")
        or request.model == QWEN_AUDIO_MODEL_ID
    ):
        command.append("--speaker-colors")
    _append_option(command, "--language", request.language)
    _append_option(command, "--length-limit", request.length_limit)
    _append_option(command, "--max-len", request.max_len)
    _append_option(command, "--min-len", request.min_len)
    _append_option(command, "--gap-split", request.gap_split)
    if request.provider == "qwen" and request.model == QWEN_AUDIO_MODEL_ID:
        _append_option(command, "--vocabulary-id", request.qwen_audio_vocabulary_id)
        _append_option(command, "--hotword-weight", request.qwen_audio_hotword_weight)
        _append_option(command, "--context", request.qwen_audio_context)
        if request.qwen_audio_hotwords_file:
            _append_option(command, "--hotword-file", request.qwen_audio_hotwords_file)
        else:
            for hotword in split_qwen_audio_hotwords(request.qwen_audio_hotwords):
                command.extend(["--hotword", hotword])
    return command


def run_transcription(
    request: TranscriptionRequest,
    *,
    on_event: ProgressCallback | None = None,
    cancel_event: Event | None = None,
    executable: Path | str | None = None,
    frozen: bool | None = None,
    on_process_start: ProcessStartCallback | None = None,
) -> TranscriptionResult:
    if cancel_event and cancel_event.is_set():
        raise TranscriptionCancelledError
    paths = build_output_paths(request.srt_path)
    paths.srt.parent.mkdir(parents=True, exist_ok=True)
    env = _child_environment(
        os.environ,
        request.api_key,
        request.workspace_id,
    )
    command = build_transcribe_command(request, executable=executable, frozen=frozen)
    process = popen_process_tree(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=str(Path(__file__).resolve().parents[1]),
        **process_group_kwargs(),
    )
    if on_process_start is not None:
        on_process_start(process.pid)
    collected: list[str] = []

    def forward(line: str) -> None:
        collected.append(line)
        if on_event:
            on_event(line)

    try:
        _stream_process(process, forward, cancel_event)
    finally:
        release_process_tree(process)
    if process.returncode != 0:
        raise TranscriptionProcessError(process.returncode, output=collected)
    _require_output(paths.srt, "SRT")
    raw_path = raw_response_path(paths.srt) if request.debug_raw else None
    if raw_path is not None:
        _require_output(raw_path, "raw ASR response")
    return TranscriptionResult(
        srt_path=paths.srt,
        raw_path=raw_path,
    )


def _stream_process(process: subprocess.Popen[bytes], on_event: ProgressCallback, cancel_event: Event | None) -> None:
    lines: queue.Queue[str | None] = queue.Queue()
    reader = threading.Thread(target=_read_process_lines, args=(process.stdout, lines), daemon=True)
    reader.start()
    while True:
        if cancel_event and cancel_event.is_set():
            _terminate(process)
            raise TranscriptionCancelledError
        try:
            line = lines.get(timeout=0.1)
        except queue.Empty:
            if process.poll() is not None and not reader.is_alive():
                break
            continue
        if line is None:
            break
        text = line.rstrip("\r\n")
        if text:
            on_event(text)
    process.wait()


def _decode_process_output(value: bytes | str) -> str:
    if isinstance(value, str):
        return value
    if value.startswith(b"\xef\xbb\xbf"):
        value = value[3:]
    utf8 = value.decode("utf-8", errors="replace")
    if "\ufffd" not in utf8:
        return utf8
    # On an English Windows runner, ``mbcs`` may decode GBK bytes as Latin-1
    # mojibake without replacement characters. Prefer the explicit GBK codec
    # before the locale-dependent Windows ANSI codec.
    encodings = ["cp936", "mbcs", locale.getpreferredencoding(False)]
    candidates = []
    for encoding in encodings:
        try:
            candidates.append(value.decode(encoding, errors="replace"))
        except (LookupError, UnicodeError):
            continue
    return min(candidates or [utf8], key=lambda text: text.count("\ufffd"))


def _read_process_lines(stdout: BinaryIO | TextIO | None, lines: queue.Queue[str | None]) -> None:
    if stdout is not None:
        for line in stdout:
            lines.put(_decode_process_output(line))
    lines.put(None)


def _child_environment(
    parent: Mapping[str, str],
    api_key: str,
    workspace_id: str = "",
) -> dict[str, str]:
    env = dict(parent)
    env["PYTHONUNBUFFERED"] = "1"
    configure_utf8_environment(env)
    configured_path = parent.get("FFMPEG_PATH") or load_env(DEFAULT_ENV_PATH).get("FFMPEG_PATH", "")
    configured = _prepend_ffmpeg_path(env, configured_path) if configured_path else False
    if not configured:
        bundled_directory = _bundled_ffmpeg_directory()
        if bundled_directory:
            _prepend_ffmpeg_path(env, str(bundled_directory))
    candidate_path = _ffmpeg_search_path(env.get("PATH", ""))
    if candidate_path:
        env["PATH"] = candidate_path
    if api_key:
        env["DASHSCOPE_API_KEY"] = api_key
    if workspace_id:
        env["DASHSCOPE_WORKSPACE_ID"] = workspace_id
    return env


def _prepend_ffmpeg_path(env: dict[str, str], configured_path: str) -> bool:
    if not configured_path.strip():
        return False
    candidate = Path(configured_path.strip()).expanduser()
    directory = candidate if candidate.is_dir() else candidate.parent
    if not directory.exists():
        return False
    old_path = env.get("PATH", "")
    env["PATH"] = str(directory) if not old_path else str(directory) + os.pathsep + old_path
    return True


def _ffmpeg_search_path(path: str | None = None) -> str | None:
    """Add common macOS Homebrew directories after the inherited PATH."""
    current = os.environ.get("PATH", "") if path is None else path
    entries = [entry for entry in current.split(os.pathsep) if entry]
    if sys.platform == "darwin":
        for directory in MACOS_FFMPEG_CANDIDATE_DIRECTORIES:
            if directory not in entries:
                entries.append(directory)
    return os.pathsep.join(entries) or None


def _bundled_ffmpeg_directory() -> Path | None:
    ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    candidates = [asset_path("ffmpeg/bin")]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys.executable).resolve().parent / "ffmpeg" / "bin")
    for directory in candidates:
        if (directory / ffmpeg_name).is_file() and (directory / ffprobe_name).is_file():
            return directory
    return None


def _terminate(process: subprocess.Popen[bytes]) -> None:
    terminate_process_tree(process)


def _require_output(path: Path, label: str) -> None:
    if not path.exists():
        raise MissingOutputError(label=label, path=path)


def _append_option(command: list[str], name: str, value: str) -> None:
    if value.strip():
        command.extend([name, value.strip()])
