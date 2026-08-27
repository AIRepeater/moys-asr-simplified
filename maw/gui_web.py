# pyright: reportAny=false, reportAttributeAccessIssue=false, reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnusedCallResult=false

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import sys
import threading
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Event
from typing import Final, final

from maw.gui_config import DEFAULT_ENV_PATH, DEFAULT_MODEL_ID, MODELS, PROVIDERS, ModelConfig, ProviderConfig, api_key_for_provider, effective_config, masked_secret, model_by_label, provider_by_id, provider_for_model, save_env
from maw.gui_platform import apply_dark_title_bar, asset_path
from maw.gui_workflow import TranscriptionCancelledError, TranscriptionProcessError, TranscriptionRequest, TranscriptionResult, _bundled_ffmpeg_directory, _ffmpeg_search_path, default_srt_path, raw_response_path, run_transcription, unique_output_path, with_test_suffix
from maw.launcher_batch import BatchItem, run_batch


OPEN_DIALOG = 10
SAVE_DIALOG = 30
FOLDER_DIALOG = 20
WINDOW_TITLE = "MAW Launcher"
MEDIA_EXTS: Final = frozenset({".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".ts", ".m4v", ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"})
# Keep this aligned with pyproject.toml; release workflows synchronize and verify it.
BUNDLED_APP_VERSION = "1.5.0-beta.4"


ERROR_MESSAGES: Final[dict[str, str]] = {
    "media_not_found": "Media file does not exist.",
    "api_key_missing": "API key is required.",
    "workspace_missing": "Workspace ID is required for Singapore region.",
    "output_missing": "SRT output path is required.",
    "segmentation_invalid": "Subtitle segmentation settings are invalid.",
    "ffmpeg_start_failed": "FFmpeg failed to start.",
    "transcription_failed": "Transcription failed.",
    "transcription_cancelled": "转写已取消。",
    "context_too_long": "Qwen-Audio context is limited to 400 characters.",
    "hotwords_file_missing": "Choose an existing UTF-8 .txt hotword file.",
    "config_save_failed": "Local configuration could not be saved.",
}


def _app_version(paths: object) -> str:
    """Read project.version from pyproject.toml for the hero wordmark; fall back to the bundled release."""
    root = getattr(paths, "root", None)
    pyproject = (root / "pyproject.toml") if root else Path("pyproject.toml")
    try:
        text = Path(pyproject).read_text(encoding="utf-8")
    except OSError:
        return BUNDLED_APP_VERSION
    match = re.search(r'(?m)^version = "([^"]+)"\r?$', text)
    return match.group(1) if match else BUNDLED_APP_VERSION


def _is_ffprobe_start_failure(lines: Sequence[str]) -> bool:
    """Recognise the Windows loader failure emitted by a nested ffprobe process."""
    detail = "\n".join(lines).lower()
    return "ffprobe" in detail and any(
        marker in detail for marker in ("3221225794", "0xc0000142", "c0000142")
    )


def _is_ffmpeg_start_failure(lines: Sequence[str]) -> bool:
    """Recognise the same Windows loader failure when FFmpeg is the child tool."""
    detail = "\n".join(lines).lower()
    return "ffmpeg" in detail and any(
        marker in detail for marker in ("3221225794", "0xc0000142", "c0000142")
    )


@final
class EventPump:
    def __init__(self, *, window_getter: Callable[[], object | None], interval: float = 0.1) -> None:
        self.window_getter = window_getter
        self.interval = interval
        self.events: queue.Queue[Mapping[str, object]] = queue.Queue()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.lock = threading.Lock()

    def start(self) -> None:
        with self.lock:
            if self.thread and self.thread.is_alive():
                return
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def enqueue(self, event: Mapping[str, object]) -> None:
        self.events.put(dict(event))

    def flush(self) -> None:
        batch: list[Mapping[str, object]] = []
        while True:
            try:
                batch.append(self.events.get_nowait())
            except queue.Empty:
                break
        if not batch:
            return
        window = self.window_getter()
        if window is None:
            return
        script = f"window.MAWLauncher && window.MAWLauncher.onBackendEvents({json.dumps(batch, ensure_ascii=False)})"
        window.evaluate_js(script)

    def shutdown(self) -> None:
        self.stop_event.set()
        self.flush()

    def _run(self) -> None:
        while not self.stop_event.wait(self.interval):
            self.flush()


@dataclass(frozen=True, slots=True)
class LauncherPaths:
    root: Path
    env_path: Path
    launcher_html: Path


def default_paths() -> LauncherPaths:
    # 冻结（PyInstaller / AppImage）时资源在 sys._MEIPASS（如 dist/MAW/_internal），
    # 源码运行时在仓库根；与 maw.gui_platform.asset_path 的取法保持一致。
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return LauncherPaths(root=root, env_path=DEFAULT_ENV_PATH, launcher_html=root / "web" / "launcher" / "index.html")


# ---- Linux keycap 表情字体（Noto Color Emoji）----
# 段落标题的 keycap 表情（1️⃣ 等）由「数字 + U+FE0F + U+20E3」组成，需要彩色 emoji 字体
# 完整覆盖才可正常成型；部分 Linux 发行版（如 SteamOS 的 Twemoji）缺少 U+FE0F，会渲染成
# 「3x」。Windows / macOS 系统 emoji 字体已覆盖 keycap，无需额外处理。
# Linux 下首次启动时按顺序尝试以下地址下载到用户缓存目录，成功即缓存，之后离线可用；
# 可通过 MAW_EMOJI_FONT_URL 环境变量整体覆盖（例如指向其它可用镜像）。
_EMOJI_FONT_FILE_NAME = "NotoColorEmoji.ttf"
_EMOJI_FONT_MIN_BYTES = 1_000_000
_EMOJI_FONT_REMOTE_URLS: Final[Sequence[str]] = (
    "https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@main/fonts/NotoColorEmoji.ttf",
    "https://fastly.jsdelivr.net/gh/googlefonts/noto-emoji@main/fonts/NotoColorEmoji.ttf",
    "https://gcore.jsdelivr.net/gh/googlefonts/noto-emoji@main/fonts/NotoColorEmoji.ttf",
)


def _emoji_font_cache_path() -> Path:
    """返回平台对应的用户级缓存路径（与 macOS 的 .env 目录命名空间一致）。"""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Moy" / "MAW"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Moy" / "MAW"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "Moy" / "MAW"
    return base / _EMOJI_FONT_FILE_NAME


def _emoji_font_urls() -> list[str]:
    override = os.environ.get("MAW_EMOJI_FONT_URL", "").strip()
    return ([override] if override else []) + list(_EMOJI_FONT_REMOTE_URLS)


def _valid_emoji_font(path: Path) -> bool:
    """轻量校验：足够大且带 TrueType 魔数，避免把 HTML 错误页等垃圾当成字体缓存。"""
    try:
        if path.stat().st_size < _EMOJI_FONT_MIN_BYTES:
            return False
        with path.open("rb") as handle:
            return handle.read(4) == b"\x00\x01\x00\x00"
    except OSError:
        return False


def download_emoji_font(urls: Sequence[str], dest: Path, timeout: float = 20.0) -> Path | None:
    """按顺序尝试下载 Noto Color Emoji 到 dest；全部失败时清理临时文件并返回 None。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    for url in urls:
        if not url:
            continue
        try:
            # URLs are restricted to the HTTPS-only CDN allowlist by the caller.
            with urlopen(url, timeout=timeout) as response:  # noqa: S310
                if getattr(response, "status", None) != 200:
                    continue
                size = 0
                with partial.open("wb") as handle:
                    while True:
                        chunk = response.read(1 << 16)
                        if not chunk:
                            break
                        handle.write(chunk)
                        size += len(chunk)
                if size < _EMOJI_FONT_MIN_BYTES:
                    continue
            partial.replace(dest)
            return dest
        except (OSError, URLError, ValueError):
            continue
    try:
        partial.unlink(missing_ok=True)
    except OSError:
        pass
    return None


@final
class LauncherApi:
    def __init__(self, *, paths: LauncherPaths | None = None, window_getter: Callable[[], object | None] | None = None) -> None:
        self.paths = paths or default_paths()
        self.window_getter = window_getter or _active_window
        self.cancel_event: Event | None = None
        self.worker: threading.Thread | None = None
        self.batch_worker: threading.Thread | None = None
        self.batch_cancel_event: Event | None = None
        self._emoji_font_worker: threading.Thread | None = None
        self.result: TranscriptionResult | None = None
        self.pump = EventPump(window_getter=self.window_getter)

    def get_emoji_font_path(self, _payload: Mapping[str, object] | None = None) -> dict[str, object]:
        """返回本地可用的 Noto Color Emoji 路径（file:// URI；未就绪或非 Linux 为空字符串）。

        仅 Linux 需要：缓存已存在时直接返回；否则启动后台下载，完成后通过
        emojiFontReady 事件通知页面注入 @font-face（期间回退系统字体）。
        """
        if sys.platform != "linux":
            return {"ok": True, "path": ""}
        dest = _emoji_font_cache_path()
        if _valid_emoji_font(dest):
            return {"ok": True, "path": dest.as_uri()}
        self._start_emoji_font_download(dest)
        return {"ok": True, "path": ""}

    def _start_emoji_font_download(self, dest: Path) -> None:
        worker = self._emoji_font_worker
        if worker is not None and worker.is_alive():
            return
        worker = threading.Thread(
            target=self._download_emoji_font_worker,
            args=(dest,),
            daemon=True,
            name="emoji-font-download",
        )
        self._emoji_font_worker = worker
        worker.start()

    def _download_emoji_font_worker(self, dest: Path) -> None:
        path = download_emoji_font(_emoji_font_urls(), dest)
        if path is not None:
            self.pump.enqueue({"type": "emojiFontReady", "path": path.as_uri()})

    def get_config(self, _payload: Mapping[str, object] | None = None) -> dict[str, object]:
        config = effective_config(self.paths.env_path)
        remembered_model = config.last_model or MODELS[0].id
        provider = provider_for_model(remembered_model)
        selected_model = next(
            (item for item in provider.models if item.id == remembered_model),
            MODELS[0],
        )
        if selected_model.id != remembered_model:
            provider = provider_for_model(selected_model.id)
        selected_api_key = api_key_for_provider(provider.id, self.paths.env_path)
        return {
            "providerId": provider.id,
            "modelId": selected_model.id,
            "apiKey": selected_api_key,
            "maskedApiKey": masked_secret(selected_api_key),
            "region": config.region,
            "workspaceId": config.workspace_id,
            "language": config.language,
            "guiLang": config.gui_lang,
            "appVersion": _app_version(self.paths),
            "showRareLangs": config.show_rare_langs,
            "lastModel": config.last_model,
            "lastLanguage": config.last_language,
            "models": [_model_payload(item) for item in provider.models],
            "regions": [{"id": value, "label": label} for value, label in provider.regions],
            "languages": [{"id": value, "label": label} for value, label in provider.languages],
            "providers": [_provider_payload(item, self.paths.env_path) for item in PROVIDERS],
            "zoomPercent": config.zoom_percent,
        }

    def default_output(self, payload: Mapping[str, object]) -> dict[str, object]:
        media_text = str(payload.get("mediaPath") or "").strip()
        provider_id = str(payload.get("providerId") or "qwen")
        model_id = str(payload.get("modelId") or DEFAULT_MODEL_ID)
        test_run = bool(payload.get("testRun"))
        requested = (
            default_srt_path(Path(media_text), provider=provider_id, model=model_id, test_run=test_run)
            if media_text else Path()
        )
        selected = unique_output_path(requested) if media_text else requested
        return {
            "ok": bool(media_text),
            "path": str(selected) if media_text else "",
            "renamed": bool(media_text and selected != requested),
        }

    def save_settings(self, payload: Mapping[str, object]) -> dict[str, object]:
        api_key = str(payload.get("apiKey") or "").strip()
        provider = provider_by_id(str(payload.get("providerId") or "qwen"))
        model_id = str(payload.get("modelId") or "")
        model = next((item for item in provider.models if model_id in (item.id, item.label)), provider.models[0] if provider.models else model_by_label(model_id))
        updates = {"MAW_GUI_LANG": _gui_lang(payload)}
        if provider.requires_api_key and model.env_key:
            updates[model.env_key] = api_key
        if provider.id == "qwen":
            updates["DASHSCOPE_REGION"] = str(payload.get("region") or "beijing")
            updates["DASHSCOPE_DEFAULT_LANGUAGE"] = str(payload.get("language") or "")
            updates["DASHSCOPE_WORKSPACE_ID"] = str(payload.get("workspaceId") or "").strip()
        try:
            save_env(self.paths.env_path, updates)
        except (OSError, UnicodeError, ValueError) as error:
            return _error_result("", "config_save_failed", f"{self.paths.env_path}: {error}")
        return {
            "ok": True,
            "maskedApiKey": masked_secret(api_key),
            "message": "settings saved",
        }

    def save_prefs(self, payload: Mapping[str, object]) -> dict[str, object]:
        updates: dict[str, str] = {}
        if "modelId" in payload:
            updates["MAW_GUI_LAST_MODEL"] = str(payload.get("modelId") or "")
        if "language" in payload:
            updates["MAW_GUI_LAST_LANGUAGE"] = str(payload.get("language") or "")
        if "showRareLangs" in payload:
            updates["MAW_GUI_SHOW_RARE_LANGS"] = "true" if payload.get("showRareLangs") else "false"
        if "zoomPercent" in payload:
            from maw.gui_config import normalize_zoom_percent

            zoom_percent = normalize_zoom_percent(payload.get("zoomPercent"))
            updates["MAW_GUI_ZOOM_PERCENT"] = str(zoom_percent)
        else:
            zoom_percent = effective_config(self.paths.env_path).zoom_percent
        if updates:
            try:
                save_env(self.paths.env_path, updates)
            except (OSError, UnicodeError, ValueError) as error:
                return _error_result("", "config_save_failed", f"{self.paths.env_path}: {error}")
        return {"ok": True, "zoomPercent": zoom_percent}

    def choose_file(self, payload: Mapping[str, object]) -> dict[str, object]:
        kind = str(payload.get("kind") or "media")
        if kind == "subtitle":
            file_types = ("Subtitle files (*.srt)",)
        elif kind == "video":
            file_types = ("Video files (*.mp4;*.mkv;*.avi;*.mov;*.wmv;*.flv;*.webm;*.ts;*.m4v)", "All files (*.*)")
        elif kind == "hotwords":
            file_types = ("Text files (*.txt)", "All files (*.*)")
        else:
            file_types = ("Media files (*.mp4;*.mkv;*.avi;*.mov;*.wmv;*.flv;*.webm;*.ts;*.m4v;*.mp3;*.wav;*.m4a;*.flac;*.aac;*.ogg)", "All files (*.*)")
        multiple = bool(payload.get("multiple"))
        chosen = _file_dialog(open_dialog=True, file_types=file_types, multiple=multiple)
        return _dialog_result(chosen, include_paths=multiple)

    def read_hotword_file(self, payload: Mapping[str, object]) -> dict[str, object]:
        value = str(payload.get("path") or "").strip()
        path = Path(value).expanduser()
        if not value or not path.is_file() or path.suffix.lower() != ".txt":
            return _error_result("qwenAudioHotwordsFile", "hotwords_file_missing", value)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            return _error_result("qwenAudioHotwordsFile", "hotwords_file_missing", str(error))
        return {"ok": True, "path": str(path), "text": text}

    def choose_folder(self, _payload: Mapping[str, object] | None = None) -> dict[str, object]:
        chosen = _folder_dialog()
        return _dialog_result(chosen)

    def choose_save_srt(self, payload: Mapping[str, object]) -> dict[str, object]:
        current = str(payload.get("currentPath") or "").strip()
        media = str(payload.get("mediaPath") or "").strip()
        filename = Path(current or str(default_srt_path(Path(media or "output.mp3")))).name
        chosen = _file_dialog(open_dialog=False, save_filename=filename, file_types=("SRT (*.srt)",))
        return _dialog_result(chosen)

    def open_url(self, payload: Mapping[str, object]) -> dict[str, object]:
        url = str(payload.get("url") or "").strip()
        if not url.startswith(("https://", "http://")):
            return {"ok": False, "error": "Invalid URL."}
        webbrowser.open(url)
        return {"ok": True}

    def open_file(self, payload: Mapping[str, object]) -> dict[str, object]:
        path = Path(str(payload.get("path") or "").strip()).expanduser()
        if not path.is_file():
            return {"ok": False, "error": f"File does not exist: {path}"}
        return _open_existing_path(path)

    def open_containing_folder(self, payload: Mapping[str, object]) -> dict[str, object]:
        path = Path(str(payload.get("path") or "").strip()).expanduser()
        if not path.is_file():
            return {"ok": False, "error": f"File does not exist: {path}"}
        return _open_existing_path(path.resolve().parent)

    def start_transcription(self, payload: Mapping[str, object]) -> dict[str, object]:
        if self.batch_worker and self.batch_worker.is_alive():
            return {"ok": False, "error": "A batch transcription is already running."}
        if self.worker and self.worker.is_alive():
            return {"ok": False, "error": "Transcription is already running."}
        try:
            request = _request_from_payload(payload, self.paths.env_path)
        except PreflightError as error:
            return error.as_result()
        selected_output = unique_output_path(request.srt_path)
        output_renamed = selected_output != request.srt_path
        if output_renamed:
            request = replace(request, srt_path=selected_output)
        self.result = None
        self.cancel_event = Event()
        self.pump.start()
        self.worker = threading.Thread(target=self._worker_main, args=(request, self.cancel_event), daemon=True)
        self.worker.start()
        return {
            "ok": True,
            "outputPath": str(request.srt_path),
            "outputRenamed": output_renamed,
            "rawPath": str(raw_response_path(request.srt_path)) if request.debug_raw else "",
        }

    def start_batch_transcription(self, payload: Mapping[str, object]) -> dict[str, object]:
        if self.worker and self.worker.is_alive() or self.batch_worker and self.batch_worker.is_alive():
            return {"ok": False, "error": "Transcription is already running."}
        raw_items = payload.get("items")
        if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)) or not raw_items:
            return {"ok": False, "field": "items", "code": "batch_items_required", "error": "Batch items are required."}
        shared = payload.get("settings")
        settings = dict(shared) if isinstance(shared, Mapping) else {key: value for key, value in payload.items() if key != "items"}
        items: list[BatchItem] = []
        reserved: set[Path] = set()
        for index, raw_item in enumerate(raw_items):
            item_id = str(raw_item.get("id") or index) if isinstance(raw_item, Mapping) else str(index)
            try:
                if not isinstance(raw_item, Mapping):
                    raise PreflightError("items", "batch_item_invalid", f"Batch item {index + 1} is invalid.")
                item_payload = {
                    **settings,
                    "mediaPath": raw_item.get("mediaPath"),
                    "srtPath": raw_item.get("srtPath") or raw_item.get("outputPath"),
                }
                merged = dict(item_payload)
                media_text = str(merged.get("mediaPath") or "").strip()
                if media_text and not str(merged.get("srtPath") or "").strip():
                    merged["srtPath"] = str(
                        default_srt_path(
                            Path(media_text),
                            provider=str(merged.get("providerId") or "qwen"),
                            model=str(merged.get("modelId") or DEFAULT_MODEL_ID),
                        )
                    )
                request = _request_from_payload(merged, self.paths.env_path)
                selected = _batch_unique_output_path(request.srt_path, reserved)
                items.append(BatchItem(str(raw_item.get("id") or index), replace(request, srt_path=selected)))
                reserved.add(selected)
            except PreflightError as error:
                items.append(BatchItem(item_id, None, error.message))
            except (OSError, ValueError) as error:
                items.append(BatchItem(item_id, None, str(error)))
        manifest_text = str(payload.get("manifestPath") or "").strip()
        first_request = next((item.request for item in items if item.request is not None), None)
        if first_request is None:
            details = "; ".join(
                f"{item.item_id}: {item.preflight_error}"
                for item in items
                if item.preflight_error
            )
            return {
                "ok": False,
                "field": "items",
                "code": "batch_items_invalid",
                "error": "No valid batch items were provided.",
                "detail": details,
            }
        manifest_path = Path(manifest_text).expanduser() if manifest_text else _unique_batch_manifest_path(first_request.srt_path.parent)
        self.batch_cancel_event = Event()
        self.pump.start()
        self.batch_worker = threading.Thread(
            target=self._batch_main,
            args=(tuple(items), settings, manifest_path, self.batch_cancel_event),
            daemon=True,
        )
        self.batch_worker.start()
        return {"ok": True, "manifestPath": str(manifest_path), "itemCount": len(items)}

    def cancel_batch_transcription(self, _payload: Mapping[str, object] | None = None) -> dict[str, object]:
        if self.batch_cancel_event:
            self.batch_cancel_event.set()
        if self.cancel_event:
            self.cancel_event.set()
        return {"ok": True}

    def _batch_main(self, items: Sequence[BatchItem], settings: Mapping[str, object], manifest_path: Path, cancel_event: Event) -> None:
        try:
            run_batch(
                items,
                settings=settings,
                manifest_path=manifest_path,
                cancel_event=cancel_event,
                on_event=self._emit,
            )
        # The background GUI boundary must unlock the batch controls after any failure.
        except Exception as error:  # noqa: BLE001
            self._emit(
                {
                    "type": "batch_done",
                    "status": "failed",
                    "error": str(error),
                    "outcomes": [],
                    "manifestPath": str(manifest_path),
                }
            )
        finally:
            if self.batch_worker is threading.current_thread():
                self.batch_worker = None
            self.pump.flush()

    def cancel_transcription(self, _payload: Mapping[str, object] | None = None) -> dict[str, object]:
        if self.cancel_event:
            self.cancel_event.set()
        return {"ok": True}

    def open_output_folder(self, _payload: Mapping[str, object] | None = None) -> dict[str, object]:
        if self.result:
            return _open_existing_path(self.result.srt_path.parent)
        return {"ok": False, "error": "No result yet."}

    def check_ffmpeg(self, _payload: Mapping[str, object] | None = None) -> dict[str, object]:
        return _check_ffmpeg(self.paths.env_path)

    def save_ffmpeg_path(self, payload: Mapping[str, object]) -> dict[str, object]:
        value = str(payload.get("path") or "").strip()
        try:
            save_env(self.paths.env_path, {"FFMPEG_PATH": value})
        except (OSError, UnicodeError, ValueError) as error:
            return _error_result("ffmpegPath", "config_save_failed", f"{self.paths.env_path}: {error}")
        result = _check_ffmpeg(self.paths.env_path, override=value)
        result["ok"] = bool(result["found"])
        return result

    def shutdown(self) -> None:
        self.cancel_transcription()
        self.cancel_batch_transcription()
        self.pump.shutdown()

    def _worker_main(self, request: TranscriptionRequest, cancel_event: Event) -> None:
        child_output: list[str] = []

        def on_child_event(line: str) -> None:
            child_output.append(line)
            self._emit({"type": "log", "message": line})

        try:
            result = run_transcription(
                request,
                on_event=on_child_event,
                cancel_event=cancel_event,
                on_process_start=lambda pid: self._emit({"type": "log", "message": f"[info] 转写进程已启动 (pid {pid})"}),
            )
        except TranscriptionCancelledError as error:
            self._emit({"type": "error", "code": "transcription_cancelled", "detail": str(error)})
            if self.worker is threading.current_thread():
                self.worker = None
            self.pump.flush()
            return
        except TranscriptionProcessError as error:
            if _is_ffprobe_start_failure(child_output):
                self._emit({
                    "type": "error",
                    "code": "ffprobe_start_failed",
                    "detail": str(error),
                })
            elif _is_ffmpeg_start_failure(child_output):
                self._emit({
                    "type": "error",
                    "code": "ffmpeg_start_failed",
                    "detail": str(error),
                })
            else:
                self._emit({"type": "error", "code": "transcription_failed", "detail": str(error)})
            if self.worker is threading.current_thread():
                self.worker = None
            self.pump.flush()
            return
        # The pywebview worker boundary must report every backend failure to JS.
        except Exception as error:  # noqa: BLE001
            self._emit({"type": "error", "code": "transcription_failed", "detail": str(error)})
            if self.worker is threading.current_thread():
                self.worker = None
            self.pump.flush()
            return
        self.result = result
        self._emit({"type": "done", "result": {"srtPath": str(result.srt_path), "rawPath": str(result.raw_path or "")}})
        if self.worker is threading.current_thread():
            self.worker = None
        self.pump.flush()

    def _emit(self, event: Mapping[str, object]) -> None:
        self.pump.enqueue(event)

    def handle_drop_paths(self, paths: Sequence[str]) -> None:
        for path in paths:
            if path:
                self._emit(_route_dropped_path(path))
                self.pump.flush()


def run_app(*, debug: bool = False, devtools: bool = False) -> None:
    import webview

    # pywebview opens DevTools automatically in debug mode when this setting is
    # enabled. Keep debug mode and automatic DevTools opening independently
    # controllable so normal development does not force an extra window.
    webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = devtools
    paths = default_paths()
    api = LauncherApi(paths=paths)
    window = webview.create_window(
        WINDOW_TITLE,
        url=paths.launcher_html.resolve().as_uri(),
        js_api=api,
        width=900,
        height=880,
        min_size=(760, 640),
        background_color="#16181d",
        text_select=True,
    )
    if window is not None:
        window.events.closing += lambda: api.shutdown()

        def _on_loaded() -> None:
            api.pump.start()
            apply_dark_title_bar(WINDOW_TITLE)

        window.events.loaded += _on_loaded
    icon = asset_path("assets/maw.ico")
    webview.start(
        lambda: bind_launcher_drop(window, api),
        debug=debug or devtools,
        icon=str(icon) if icon.exists() else None,
    )


def bind_launcher_drop(window: object | None, api: LauncherApi) -> None:
    if window is None:
        return
    try:
        from webview.dom import DOMEventHandler
    except ImportError:
        return

    def on_drop(event: Mapping[str, object]) -> None:
        api.handle_drop_paths(_drop_paths_from_event(event))

    window.dom.document.events.drop += DOMEventHandler(on_drop, True, True)


@dataclass(frozen=True, slots=True)
class PreflightError(Exception):
    field: str
    code: str
    message: str

    def as_result(self) -> dict[str, object]:
        return _error_result(self.field, self.code, self.message)


def _segmentation_option(
    payload: Mapping[str, object],
    *,
    field: str,
    label: str,
    minimum: int,
) -> str:
    text = str(payload.get(field) or "").strip()
    if not text:
        return ""
    try:
        value = int(text)
    except (TypeError, ValueError) as error:
        raise PreflightError(field, "segmentation_invalid", f"{label}必须是整数。") from error
    if value < minimum:
        raise PreflightError(field, "segmentation_invalid", f"{label}不能小于 {minimum}。")
    return str(value)


def _request_from_payload(payload: Mapping[str, object], env_path: Path) -> TranscriptionRequest:
    media_text = str(payload.get("mediaPath") or "").strip()
    srt_text = str(payload.get("srtPath") or "").strip()
    media = Path(media_text).expanduser()
    srt = Path(srt_text).expanduser()
    test_run = bool(payload.get("testRun"))
    if test_run:
        srt = with_test_suffix(srt)
    provider = provider_by_id(str(payload.get("providerId") or "qwen"))
    requested_model = str(payload.get("modelId") or "")
    model = next(
        (item for item in provider.models if requested_model in (item.id, item.label)),
        provider.models[0],
    )
    api_key = str(payload.get("apiKey") or "").strip() or api_key_for_provider(provider.id, env_path)
    region = str(payload.get("region") or "beijing") if provider.id == "qwen" else ""
    workspace_id = str(payload.get("workspaceId") or "").strip()
    if not media_text or not media.exists():
        raise PreflightError("mediaPath", "media_not_found", "Media file does not exist.")
    if not srt_text or not srt.name:
        raise PreflightError("srtPath", "output_missing", "SRT output path is required.")
    max_len = _segmentation_option(payload, field="maxLen", label="最大字数", minimum=1)
    min_len = _segmentation_option(payload, field="minLen", label="短句合并阈值", minimum=1)
    gap_split = _segmentation_option(payload, field="gapSplit", label="停顿切句阈值", minimum=0)
    if max_len and min_len and int(max_len) < int(min_len):
        raise PreflightError(
            "maxLen",
            "segmentation_invalid",
            "最大字数不能小于短句合并阈值。",
        )
    if provider.requires_api_key and not api_key:
        raise PreflightError("apiKey", "api_key_missing", "API key is required.")
    if provider.id == "qwen" and region == "singapore" and not workspace_id:
        raise PreflightError("workspaceId", "workspace_missing", "Workspace ID is required for Singapore region.")
    qwen_audio_context = (
        str(payload.get("qwenAudioContext") or "").strip()
        if provider.id == "qwen" and model.supports_context else ""
    )
    if len(qwen_audio_context) > 400:
        raise PreflightError(
            "qwenAudioContext",
            "context_too_long",
            "Qwen-Audio context is limited to 400 characters.",
        )
    qwen_audio_hotwords_mode = str(payload.get("qwenAudioHotwordsMode") or "text").strip().lower()
    qwen_audio_hotwords_file = ""
    qwen_audio_hotwords = ""
    if model.supports_hotwords and qwen_audio_hotwords_mode == "file":
        hotwords_file_text = str(payload.get("qwenAudioHotwordsFile") or "").strip()
        hotwords_file = Path(hotwords_file_text).expanduser()
        if not hotwords_file.is_file() or hotwords_file.suffix.lower() != ".txt":
            raise PreflightError(
                "qwenAudioHotwordsFile",
                "hotwords_file_missing",
                "Qwen-Audio hotword source must be an existing .txt file.",
            )
        qwen_audio_hotwords_file = str(hotwords_file)
    elif model.supports_hotwords:
        qwen_audio_hotwords = str(payload.get("qwenAudioHotwords") or "").strip()
    return TranscriptionRequest(
        media_path=media,
        srt_path=srt,
        model=model.model_ref or model.id,
        language=str(payload.get("language") or ""),
        api_key=api_key,
        length_limit="2m" if test_run else str(payload.get("lengthLimit") or "").strip(),
        max_len=max_len,
        min_len=min_len,
        gap_split=gap_split,
        qwen_audio_context=qwen_audio_context,
        qwen_audio_hotwords=qwen_audio_hotwords,
        qwen_audio_hotwords_file=qwen_audio_hotwords_file,
        qwen_audio_vocabulary_id=(
            str(payload.get("qwenAudioVocabularyId") or "").strip()
            if model.supports_vocabulary else ""
        ),
        qwen_audio_hotword_weight=(
            str(payload.get("qwenAudioHotwordWeight") or "").strip()
            if model.supports_hotwords else ""
        ),
        region=region,
        workspace_id=workspace_id,
        provider=provider.id,
        speaker_colors=bool(payload.get("speakerColors")) and model.supports_speaker,
        ui_language=_gui_lang(payload),
        debug_raw=bool(payload.get("debugRaw")),
    )


def _file_dialog(*, open_dialog: bool, file_types: tuple[str, ...], save_filename: str = "", multiple: bool = False) -> tuple[str, ...] | None:
    import webview

    if not webview.windows:
        return None
    dialog_type = OPEN_DIALOG if open_dialog else SAVE_DIALOG
    selected = webview.windows[0].create_file_dialog(dialog_type, save_filename=save_filename, file_types=file_types, allow_multiple=multiple)
    return tuple(selected) if selected else None


def _folder_dialog() -> tuple[str, ...] | None:
    import webview

    if not webview.windows:
        return None
    selected = webview.windows[0].create_file_dialog(FOLDER_DIALOG)
    return tuple(selected) if selected else None


def _dialog_result(selected: tuple[str, ...] | None, *, include_paths: bool = False) -> dict[str, object]:
    if not selected:
        return {"ok": False, "path": ""}
    result: dict[str, object] = {"ok": True, "path": selected[0]}
    if include_paths:
        result["paths"] = list(selected)
    return result


def _batch_unique_output_path(path: Path, reserved: set[Path]) -> Path:
    candidate = unique_output_path(path)
    counter = 1
    while candidate in reserved:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        counter += 1
    return candidate


def _unique_batch_manifest_path(directory: Path) -> Path:
    candidate = directory / "maw-batch-manifest.json"
    counter = 1
    while candidate.exists():
        candidate = directory / f"maw-batch-manifest-{counter}.json"
        counter += 1
    return candidate


def _active_window() -> object | None:
    import webview

    return webview.windows[0] if webview.windows else None


def _gui_lang(payload: Mapping[str, object]) -> str:
    return "en" if str(payload.get("guiLang") or "zh").lower() == "en" else "zh"


def _error_result(field: str, code: str, detail: str = "") -> dict[str, object]:
    return {"ok": False, "field": field, "code": code, "detail": detail, "error": ERROR_MESSAGES.get(code, detail or code)}


def _route_dropped_path(path: str) -> dict[str, object]:
    suffix = Path(path).suffix.lower()
    if suffix == ".txt":
        return {"type": "dropHotwordFile", "path": path}
    if suffix in MEDIA_EXTS:
        return {"type": "dropMedia", "path": path}
    return {"type": "dropReject", "path": path}


def _drop_paths_from_event(event: Mapping[str, object]) -> list[str]:
    data_transfer = event.get("dataTransfer")
    if not isinstance(data_transfer, Mapping):
        return []
    files = data_transfer.get("files")
    if not isinstance(files, Sequence) or isinstance(files, (str, bytes)):
        return []
    paths: list[str] = []
    for file_item in files:
        if not isinstance(file_item, Mapping):
            continue
        value = file_item.get("pywebviewFullPath")
        if isinstance(value, str) and value:
            paths.append(value)
    return paths


def _open_existing_path(path: Path) -> dict[str, object]:
    target = Path(path).expanduser()
    if not target.exists():
        return {"ok": False, "error": f"Path does not exist: {target}"}
    if os.name == "nt":
        os.startfile(str(target))
    else:
        webbrowser.open(target.resolve().as_uri())
    return {"ok": True}


def _check_ffmpeg(env_path: Path, override: str = "") -> dict[str, object]:
    ffmpeg_path = _which_ffmpeg_tool("ffmpeg")
    ffprobe_path = _which_ffmpeg_tool("ffprobe")
    configured_value = override or os.environ.get("FFMPEG_PATH", "") or effective_config_value(env_path, "FFMPEG_PATH")
    configured_dir = _ffmpeg_directory(configured_value)
    if override and configured_dir is None:
        return {"ok": True, "found": False, "ffmpeg": "", "ffprobe": "", "directory": ""}
    if configured_dir:
        ffmpeg_candidate = configured_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        ffprobe_candidate = configured_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if ffmpeg_candidate.exists() and ffprobe_candidate.exists():
            ffmpeg_path = str(ffmpeg_candidate)
            ffprobe_path = str(ffprobe_candidate)
    if not (ffmpeg_path and ffprobe_path):
        bundled_dir = _bundled_ffmpeg_directory()
        if bundled_dir:
            ffmpeg_path = str(bundled_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"))
            ffprobe_path = str(bundled_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe"))
    found = bool(ffmpeg_path and ffprobe_path)
    directory = str(Path(ffmpeg_path).parent) if ffmpeg_path else ""
    return {"ok": True, "found": found, "ffmpeg": ffmpeg_path or "", "ffprobe": ffprobe_path or "", "directory": directory}


def _which_ffmpeg_tool(name: str) -> str | None:
    if sys.platform != "darwin":
        return shutil.which(name)
    return shutil.which(name, path=_ffmpeg_search_path())


def effective_config_value(env_path: Path, key: str) -> str:
    from maw.gui_config import load_env

    return os.environ.get(key) or load_env(env_path).get(key, "")


def _ffmpeg_directory(value: str) -> Path | None:
    if not value.strip():
        return None
    candidate = Path(value.strip()).expanduser()
    if candidate.is_dir():
        return candidate
    if candidate.exists():
        return candidate.parent
    return None


def _provider_payload(
    provider: ProviderConfig,
    env_path: Path,
) -> dict[str, object]:
    api_key = api_key_for_provider(provider.id, env_path)
    return {
        "id": provider.id,
        "label": provider.label,
        "kind": provider.kind,
        "keyUrl": provider.key_url,
        "requiresApiKey": provider.requires_api_key,
        "apiKey": api_key,
        "maskedApiKey": masked_secret(api_key),
        "supportsSpeaker": provider.supports_speaker,
        "multiLanguage": provider.multi_language,
        "supportsLanguage": provider.supports_language,
        "note": provider.note,
        "commonLanguages": list(provider.common_languages),
        "models": [_model_payload(item) for item in provider.models],
        "regions": [{"id": value, "label": label} for value, label in provider.regions],
        "languages": [{"id": value, "label": label} for value, label in provider.languages],
    }


def _model_payload(model: ModelConfig) -> dict[str, object]:
    return {
        "id": model.id,
        "label": model.label,
        "envKey": model.env_key,
        "note": model.note,
        "supportsSpeaker": model.supports_speaker,
        "supportsContext": model.supports_context,
        "supportsHotwords": model.supports_hotwords,
        "supportsVocabulary": model.supports_vocabulary,
        "kind": model.kind,
        "modelRef": model.model_ref,
        "languages": [
            {"id": value, "label": label}
            for value, label in model.languages
        ],
    }
