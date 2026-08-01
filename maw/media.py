"""Shared media-path resolution for MAW project loading."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class MediaStatus(str, Enum):
    SUCCESS = "success"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"
    CONVERSION_NEEDED = "conversion_needed"
    CONFLICT = "conflict"


VIDEO_EXTENSIONS = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".ts", ".m4v",
})
AUDIO_EXTENSIONS = frozenset({
    ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".opus",
})
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS
CONVERSION_EXTENSIONS = frozenset({".flv"})


@dataclass(frozen=True, slots=True)
class MediaResolution:
    status: MediaStatus
    project_path: Path
    requested_path: Path | None = None
    resolved_path: Path | None = None
    candidates: tuple[Path, ...] = ()
    message: str = ""

    @property
    def loadable(self) -> bool:
        return self.resolved_path is not None and self.status in {
            MediaStatus.SUCCESS,
            MediaStatus.CONVERSION_NEEDED,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "projectPath": str(self.project_path),
            "requestedPath": str(self.requested_path) if self.requested_path else "",
            "resolvedPath": str(self.resolved_path) if self.resolved_path else "",
            "candidates": [str(path) for path in self.candidates],
            "message": self.message,
        }


class MediaResolutionError(ValueError):
    def __init__(self, resolution: MediaResolution) -> None:
        self.resolution = resolution
        super().__init__(resolution.message or resolution.status.value)


class MediaConversionError(ValueError):
    """The source media was found, but could not be prepared for browser playback."""


def find_ffmpeg(configured_path: str | os.PathLike[str] | None = None) -> Path | None:
    """Find ffmpeg from an explicit setting or the current process PATH."""

    configured = str(configured_path or os.environ.get("FFMPEG_PATH", "")).strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_dir():
            candidate = candidate / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if candidate.is_file():
            return candidate.resolve()
    found = shutil.which("ffmpeg")
    return Path(found).resolve() if found else None


def _conversion_cache_path(source: Path, cache_dir: Path | None = None) -> Path:
    stat = source.stat()
    signature = f"{source.resolve()}\0{stat.st_size}\0{stat.st_mtime_ns}".encode("utf-8")
    digest = hashlib.sha256(signature).hexdigest()[:20]
    root = cache_dir or (Path(tempfile.gettempdir()) / "moys-asr-workflow-media")
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{source.stem}.{digest}.mp4"


def convert_media_for_browser(
    source: Path,
    *,
    ffmpeg_path: str | os.PathLike[str] | None = None,
    cache_dir: Path | None = None,
) -> Path:
    """Remux/transcode a browser-incompatible source into a cached MP4."""

    source = source.expanduser().resolve()
    if source.suffix.lower() not in CONVERSION_EXTENSIONS:
        return source
    executable = find_ffmpeg(ffmpeg_path)
    if executable is None:
        raise MediaConversionError(
            "检测到 FLV 媒体，但找不到 FFmpeg；请配置 FFMPEG_PATH 或将 ffmpeg 加入 PATH"
        )

    output = _conversion_cache_path(source, cache_dir)
    if output.is_file() and output.stat().st_size > 0:
        return output

    commands = (
        [
            str(executable), "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-i", str(source), "-map", "0:v:0?", "-map", "0:a:0?", "-c", "copy",
            "-movflags", "+faststart", str(output),
        ],
        [
            str(executable), "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-i", str(source), "-map", "0:v:0?", "-map", "0:a:0?", "-c:v", "libx264",
            "-preset", "ultrafast", "-c:a", "aac", "-movflags", "+faststart", str(output),
        ],
    )
    errors: list[str] = []
    for command in commands:
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
        except OSError as error:
            raise MediaConversionError(f"启动 FFmpeg 失败：{error}") from error
        if result.returncode == 0 and output.is_file() and output.stat().st_size > 0:
            return output
        if output.exists():
            output.unlink()
        detail = (result.stderr or result.stdout or "FFmpeg 未生成可播放文件").strip()
        errors.append(detail[-1000:])
    raise MediaConversionError(
        f"FFmpeg 无法将 {source.name} 转换为浏览器可播放的 MP4：{errors[-1]}"
    )


def _path_from_value(value: str, base_dir: Path, *, cwd_relative: bool = False) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (Path.cwd() if cwd_relative else base_dir / path).resolve()


def _media_stem(value: str) -> str:
    stem = Path(value).stem
    lowered = stem.lower()
    for tag in (
        ".qwen3-asr.", ".qwen3-asr-api.", ".funasr.", ".glm-asr.",
        ".paraformer.", ".sensevoice.", ".nano.",
    ):
        index = lowered.find(tag)
        if index >= 0:
            return lowered[:index]
    return lowered


def _classify_existing(
    project_path: Path,
    path: Path,
    *,
    requested_path: Path | None = None,
) -> MediaResolution:
    suffix = path.suffix.lower()
    if suffix not in MEDIA_EXTENSIONS:
        return MediaResolution(
            MediaStatus.UNSUPPORTED,
            project_path,
            requested_path=requested_path or path,
            message=f"不支持的媒体格式：{path.suffix or '无扩展名'}",
        )
    status = MediaStatus.CONVERSION_NEEDED if suffix in CONVERSION_EXTENSIONS else MediaStatus.SUCCESS
    message = "该媒体格式可能需要转换后才能在浏览器中播放" if status is MediaStatus.CONVERSION_NEEDED else ""
    return MediaResolution(
        status,
        project_path,
        requested_path=requested_path or path,
        resolved_path=path,
        message=message,
    )


def _same_name_candidates(project_path: Path, data: dict[str, Any]) -> tuple[Path, ...]:
    raw_media = data.get("media")
    source_name = Path(str(raw_media)).name if isinstance(raw_media, str) and raw_media.strip() else project_path.name
    expected_stem = _media_stem(source_name)
    if not expected_stem:
        return ()
    try:
        entries = project_path.parent.iterdir()
    except OSError:
        return ()
    candidates = [
        path.resolve()
        for path in entries
        if path.is_file()
        and path.suffix.lower() in MEDIA_EXTENSIONS
        and _media_stem(path.name) == expected_stem
    ]
    return tuple(sorted(candidates, key=lambda path: path.name.casefold()))


def resolve_project_media(
    project_path: Path,
    data: dict[str, Any],
    explicit_media: str | None = None,
) -> MediaResolution:
    """Resolve explicit/project media, then one exact same-stem local fallback."""

    project_path = project_path.expanduser().resolve()
    base_dir = project_path.parent

    if explicit_media:
        requested = _path_from_value(explicit_media, base_dir, cwd_relative=True)
        if not requested.is_file():
            return MediaResolution(
                MediaStatus.MISSING,
                project_path,
                requested_path=requested,
                message=f"找不到指定媒体文件：{requested}",
            )
        return _classify_existing(project_path, requested, requested_path=requested)

    raw_media = data.get("media")
    requested: Path | None = None
    if isinstance(raw_media, str) and raw_media.strip():
        requested = _path_from_value(raw_media.strip(), base_dir)
        if requested.is_file():
            return _classify_existing(project_path, requested, requested_path=requested)

    candidates = _same_name_candidates(project_path, data)
    if len(candidates) == 1:
        return _classify_existing(project_path, candidates[0], requested_path=requested)
    if len(candidates) > 1:
        return MediaResolution(
            MediaStatus.CONFLICT,
            project_path,
            requested_path=requested,
            candidates=candidates,
            message="工程目录存在多个同名媒体文件，请手动指定一个",
        )
    return MediaResolution(
        MediaStatus.MISSING,
        project_path,
        requested_path=requested,
        message="找不到工程关联媒体文件，请手动指定媒体",
    )
