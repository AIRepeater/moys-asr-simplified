# Third-party notices

本仓库不打包模型或云端 API 服务。默认的 `MAW-Windows` 与 `MAW-macOS-arm64` 包会附带对应平台的 `ffmpeg` 与 `ffprobe`；可选的 `MAW-lite` 包不含 FFmpeg；Linux 的 `MAW-Linux-x86_64.AppImage` 始终内置静态 `ffmpeg`/`ffprobe`（BtbN 构建）。运行时可能使用下列外部组件；许可证和服务条款以各项目及服务方的最新文本为准。

| Component | Purpose | License / terms |
|---|---|---|
| [requests](https://requests.readthedocs.io/) | HTTP requests to the ASR API | Apache-2.0 |
| [jieba](https://github.com/fxsjy/jieba) | Chinese subtitle segmentation | MIT |
| [PyQt6](https://riverbankcomputing.com/software/pyqt/) / [QtPy](https://github.com/spyder-ide/qtpy) | Linux desktop GUI backend for pywebview (Launcher) | PyQt6: GPL-3.0 or a commercial license from Riverbank Computing; Qt: LGPL-3.0 |
| [Noto Color Emoji](https://github.com/googlefonts/noto-emoji) | Color emoji font for the Linux launcher keycap headers (1️⃣ etc.). On first launch the app downloads it to the user cache directory (`MAW_EMOJI_FONT_URL` can override the source), then the page references it locally; subsequent runs are offline. Not bundled or shipped. File sha256 at integration time: `72a635cb3d2f3524c51620cdde406b217204e8a6a06c6a096ff8ed4b5fd6e27b` | SIL OFL 1.1 |
| [PyInstaller](https://pyinstaller.org/) | Build the optional Windows application bundle | GPL-2.0-or-later with a bootloader exception that permits distributing bundled applications |
| [Python](https://www.python.org/) | Runtime embedded in the optional Windows application bundle | Python Software Foundation License |
| [FFmpeg](https://ffmpeg.org/) / [Gyan Windows build](https://www.gyan.dev/ffmpeg/builds/) / [OSXExperts macOS build](https://www.osxexperts.net/) / [BtbN Linux build](https://github.com/BtbN/FFmpeg-Builds) | Inspect media and extract audio before transcription | `MAW-Windows` includes FFmpeg 8.1.2 Essentials executables under GPL-3.0; `MAW-macOS-arm64` includes FFmpeg 8.1 Apple Silicon static `ffmpeg` and `ffprobe` binaries; the optional `MAW-lite` packages do not bundle FFmpeg; the Linux `MAW-Linux-x86_64.AppImage` bundles the BtbN `linux64-gpl` static `ffmpeg`/`ffprobe` build. The bundled `ffmpeg/` directory includes FFmpeg license files and source/provider references. |
| Alibaba Cloud Model Studio / Qwen ASR | Speech recognition API | External service; subject to Alibaba Cloud terms, billing, and privacy policy |

The Launcher frontend, Python scripts, and documentation in this repository are distributed under the repository's `AGPL-3.0-only` license unless a file states otherwise.
