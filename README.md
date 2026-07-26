# Moy's ASR Workflow（MAW）

把一个视频或音频交给 Qwen ASR API，得到可编辑的字幕工程、SRT 和浏览器字幕编辑器。

**MAW** 是 Moy's ASR Workflow 的简称。这是一个 **最小可用复刻版**：优先让没有 GPU、刚接触命令行的用户跑通完整流程。它目前只支持 Qwen / 阿里云百炼的云端 API，不包含本地模型、其他 ASR 引擎或自动下载模型。

> 之后会有更完整的 **Moy's Open Subtitle Editor（MOSE）**：网页、桌面和便携 HTML 三种形态共享同一个工程格式。这个仓库会保持小而可用，并为将来导入 MOSE 留出工程 JSON 的兼容路径；详见 [docs/MOSE.md](docs/MOSE.md)。

## 这套工具能做什么

1. 用 Qwen ASR API 把本地视频或音频转为字幕。
2. 一次生成 `.srt`、含字级时间戳的 `.json` 工程和单文件 `.edit.html`。
3. 在浏览器中校正文本、时间、波形、静音空隙和字幕布局。
4. 导出 SRT、工程 JSON，以及编辑器支持的额外格式。

所有编辑都在本机浏览器完成。转写时，脚本会把待识别媒体直接上传到你配置的阿里云百炼账户；本项目没有自己的服务器、不会代管你的 API Key 或媒体。

## 你需要准备

- Windows 10/11（目前主要在 Windows 上验证）；macOS/Linux 也可尝试。
- Python 3.11 或更新版本。
- [uv](https://docs.astral.sh/uv/getting-started/installation/)（推荐）或普通 Python 虚拟环境。
- [FFmpeg](https://ffmpeg.org/download.html)，并确保 `ffmpeg` 与 `ffprobe` 能在终端直接运行。
- 一个阿里云百炼 Qwen API Key。申请入口：[获取 API Key](https://help.aliyun.com/zh/model-studio/get-api-key)。

## 最快上手（推荐）

在 PowerShell 中执行：

```powershell
git clone <这个仓库的地址> moys-asr-workflow
cd moys-asr-workflow
uv sync
Copy-Item .env.example .env
```

打开新建的 `.env`，填入这一行：

```ini
DASHSCOPE_API_KEY=sk-替换成你的真实密钥
```

然后转写一个文件：

```powershell
uv run python generate_subtitle_qwen_api.py "D:\Videos\example.mp4" --json
```

首次成功会在媒体同目录生成：

- `…qwen3-asr-api….srt`：可导入播放器或剪辑软件的字幕；
- 同名 `.json`：**工程真源**，以后继续编辑请保留它；
- 同名 `.edit.html`：可双击离线打开的自包含编辑器。

建议先只处理两分钟，确认 API、FFmpeg 与输出目录都正确：

```powershell
uv run python generate_subtitle_qwen_api.py "D:\Videos\example.mp4" -ll 2m --json
```

如果不使用 uv，请看 [docs/WORKFLOW.md](docs/WORKFLOW.md) 的普通 Python 安装方式。

## 编辑字幕

推荐使用本地服务器编辑器，它能稳定拖动大型媒体、自动载入 JSON 中记录的媒体路径，并支持安全保存工程：

```powershell
uv run python server-editor\serve.py "D:\Videos\example.qwen3-asr-api.json"
```

浏览器会自动打开 `http://127.0.0.1:8765`。编辑完成后点“保存工程”；覆盖前会留下同目录 `.json.bak` 备份。按 `Ctrl+C` 停止服务。

也可以直接双击转写生成的 `.edit.html`，或双击仓库里的 `blank-editor.html` 后用“打开工程”同时选择 JSON 和媒体。单文件模式更适合离线携带；本地服务器模式更适合日常编辑。

常用编辑操作：

- 双击字幕：改文字；`Enter` 保存，`Shift+Enter` 换行。
- 单击字幕或波形：定位播放头；双击波形：播放/暂停。
- 拖动波形字幕块或边缘：移动字幕、调整起止时间。
- `Alt + 点击` 字幕块：切换该条禁用状态。
- 右键菜单：拆分、合并、批量替换、颜色、导出等。

完整步骤、常用参数与排错见 [docs/WORKFLOW.md](docs/WORKFLOW.md)。工程 JSON 结构见 [JSON_SCHEMA.md](JSON_SCHEMA.md)。

## API、隐私与费用

- 这是 **API-first** 工具，不含模型下载和本地 Qwen 推理。
- API Key 仅读取自环境变量或本机 `.env`；`.env` 已被 Git 忽略，绝不要提交、截图或发给别人。
- 每次转写会使用你的 Key 调用阿里云百炼服务，费用、文件大小与保留政策以官方当前说明为准：[Qwen ASR 文档](https://help.aliyun.com/zh/model-studio/qwen-asr-api-reference)。
- 当前 API 端点面向 `qwen3-asr-flash-filetrans`，支持北京与新加坡地域；配置项说明在 `.env.example`。

## 项目边界

本仓库刻意不包含：本地模型与 GPU 依赖、其他 ASR 引擎、模型对比工具、剪辑软件脚本、样例媒体、缓存、个人表情包和任何密钥。

如果你准备修改或维护它，请先读 [AGENTS.md](AGENTS.md)。第三方组件说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 许可证

本项目采用 [AGPL-3.0-only](LICENSE)。若你修改后把它作为网络服务提供给用户，AGPL 通常要求向这些用户提供对应的修改后源码；发布前请自行确认你的合规义务。
