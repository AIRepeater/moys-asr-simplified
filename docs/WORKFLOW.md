# MAW 完整工作流指南

这份指南按 Windows PowerShell 写；路径带空格时始终加双引号。MAW 是 Moy's ASR Workflow 的简称。它的功能范围很窄：把本地音视频发给阿里云百炼（Qwen-Audio / Fun-ASR）做在线语音识别，然后直接输出 UTF-8 SRT 字幕。

## 0. 安装依赖

如果使用 GitHub Releases 提供的 Windows 或 macOS 图形版，Python 运行环境与 FFmpeg、ffprobe 已由默认 `MAW` 包打包，不需要单独安装；体积更小的 `MAW-lite` 包不包含 FFmpeg，需要系统已安装并可在 PATH 中找到 `ffmpeg` 和 `ffprobe`。Windows 解压后双击 `MAW.exe`；macOS 解压后打开 `MAW.app` 或 `MAW-lite.app`，启动的即是 Launcher。

源码方式继续按下列步骤安装：

确认下列命令都有输出：

```powershell
python --version
ffmpeg -version
ffprobe -version
uv --version
```

需要 Python 3.11+。推荐安装 uv 后在仓库根目录执行：

```powershell
uv sync
```

不使用 uv 时，改用普通虚拟环境：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install "requests>=2.28" "jieba>=0.42" "pywebview>=6.2.1"
```

后文的 `uv run python` 可替换为 `.\.venv\Scripts\python`。命令行转写只需要 `requests` 与 `jieba`；`pywebview` 是启动 Launcher 图形界面所需。

## 1. 配置阿里云百炼 API

所有模型共用同一个百炼 API Key。图形版可在 Launcher 的遮罩输入框中填写并保存到本机环境；命令行方式使用脚本同目录的 `.env`：

```powershell
Copy-Item .env.example .env
notepad .env
```

最少填入：

```ini
DASHSCOPE_API_KEY=sk-你的密钥
```

北京地域默认使用 `DASHSCOPE_REGION=beijing`；`DASHSCOPE_WORKSPACE_ID` 在北京选填，填写后会使用官方推荐的业务空间专属域名。新加坡地域改为 `singapore` 并必须填写 Workspace ID。Launcher 目前面向国内用户隐藏地域和 Workspace 控件；如需海外地域或专属域名，请通过 `.env` 配置。环境变量优先于 `.env`。密钥申请和地域说明以[官方文档](https://help.aliyun.com/zh/model-studio/get-api-key)为准。

## 2. 先跑小样本

图形版的“Length limit”可填写 `2m`，效果等同于命令行 `-ll 2m`。

先用 `-ll 2m` 限制在两分钟，既减少费用也便于排错：

```powershell
uv run python generate_subtitle_qwen_api.py "D:\Videos\example.mp4" -ll 2m
```

未指定 `--model` 时默认使用 `qwen-audio-3.0-asr-flash-filetrans`。转写完成后，SRT 默认写到媒体同目录（可用 `-o` 指定输出路径）。

常用可选项：

```text
-o path.srt          指定输出 SRT 路径（默认与输入同目录）
--language zh        已知纯中文时指定；中英日韩混说时不要指定
--gap-split 1500     相邻字停顿超过 N 毫秒时强制切句
--keep-punct         保留每条字幕末尾的逗号和句号
-l / --max-len 21    每条字幕最大字数（仅 CJK 内容生效）
--min-len 5          句号间最短字数，不足则合并
--file-url URL       直接提供公网可访问音频 URL，跳过本地上传
--region beijing     覆盖 .env 的 DASHSCOPE_REGION
--debug              输出部分 API 原始结果，便于反馈问题
--debug-raw          单独保存完整 ASR 原始 JSON（<输出文件名>.asr-response.json）
```

输入视频会先由 FFmpeg 提取单声道 16kHz WAV；音频输入也会通过 FFprobe 获取时长。没有 FFmpeg/FFprobe 时，这一步无法完成。

## 热词与上下文（Qwen-Audio）

选择 Qwen-Audio 后，Launcher 的高级选项会显示 `Prompt / 上下文`、`即时热词` 和权重。预编译 `vocabulary_id` 暂不在 Launcher 开放，底层命令行 / `.env` 能力保留；Launcher 字段只随本次转写提交，不会写入 `.env`。

```text
--vocabulary-id ID       覆盖百炼预编译词表 ID
--hotword "词"           追加一个即时热词，可重复传入
--hotword-file path.txt  使用指定 UTF-8 文本文件作为即时热词来源
--hotword-weight 5       hotwords.txt 即时热词权重，可用 1-5 或 50
--context "领域词表"     发送最多 400 字符上下文
--context-file path.txt  从 UTF-8 文件读取上下文
```

热词文本支持 `热词: 权重` 或 `热词：权重`，单项权重可覆盖全局权重；未指定时使用 `--hotword-weight`。按百炼规则，含非 ASCII 字符的单项最多 15 个字符，纯 ASCII 单项最多 7 个空格分隔的单词，每次最多 2000 项，权重 50 最多 50 项。不合规项会提示警告并在发送时忽略。

也可以在 `.env` 中设置 `DASHSCOPE_QWEN_AUDIO_VOCABULARY_ID`、`DASHSCOPE_QWEN_AUDIO_HOTWORD_WEIGHT` 和 `DASHSCOPE_QWEN_AUDIO_CONTEXT_FILE`。预编译词表必须按目标模型创建；Fun-ASR 使用独立的 `DASHSCOPE_FUNASR_VOCABULARY_ID`。上下文参数形状和限制以[官方 HTTP API](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api)为准。

Prompt / 上下文用于提供领域背景、前文或会话信息；即时热词用于提高明确专有名词、人名、产品名的命中概率。需要随每次音频变化的背景优先用 Prompt，稳定且必须准确识别的短词优先用即时热词，二者可以同时配置。

### 退出码语义

转写脚本在成功时以退出码 `0` 退出；出错时以非零退出码退出，便于脚本与 CI 判断成败：

```text
退出码 0   成功，SRT 已产出
退出码 1   调用方错误，如输入文件不存在、未配置 API Key、时长超限
退出码 2   转写完成但未识别到任何内容（静音/无有效语音），不会产出 SRT
```

错误消息写在 stderr（图形版会合并读取并透传具体原因），脚本自身不把业务错误打成静默成功。

## 用 Fun-ASR 转写（支持说话人）

在 Launcher 中选择阿里云百炼 Provider，再把模型切换为 `fun-asr（支持说话人）`。它复用 `DASHSCOPE_API_KEY`、地域和 Workspace 配置，默认输出名标签为 `.fun-asr.`。

命令行示例：

```powershell
uv run python generate_subtitle_qwen_api.py "D:\Videos\example.mp4" --model fun-asr -ll 2m --speaker
```

常用可选项：

```text
--speaker            开启说话人分离，按说话人切分字幕
--language zh        只提供一个语种提示；默认自动识别
```

Fun-ASR 普通文件限制为 12 小时 / 2 GB；说话人分离只适用于单声道，官方建议启用时音频不超过 2 小时。MAW 提交前会提取单声道音频，且超过建议时长时给出警告。说话人标签是匿名 ID，不是现实姓名。

Fun-ASR 的 API 输入字段、轮询结果路径和 JSON 映射与 Qwen-Audio 不同，虽然二者共用同一个入口脚本。

## Launcher 批量转写

Launcher 的「批量」模式用于把多个本地媒体按顺序转写。切换到「批量」后，可以点击「添加文件」多选媒体，或直接拖入文件；重复路径会自动忽略，不支持的文件扩展名不会加入队列。

队列内所有文件共用当前的识别方式、模型、语言和热词设置。点击「开始全部」后，Launcher 按队列顺序逐个执行，同一时间只转写一个文件。运行期间可点击「停止全部」：当前任务和尚未开始的任务都会标记为已取消。

- 每个文件生成自己的 `.srt`。如果默认输出名已存在或与队列中其他文件冲突，Launcher 会自动加上 `-1`、`-2` 等后缀，源媒体不会被覆盖。
- 单个文件的预检或转写失败只会标记该行失败，后续文件仍会继续执行。完成的条目可直接打开所在文件夹。
- 每批会在第一个有效媒体的输出目录创建 `maw-batch-manifest.json`；文件名冲突时同样自动加后缀。它记录已脱敏的设置和每个文件的结果，并以原子方式更新，便于排查已完成、失败或取消的条目；它不是恢复或继续执行批次的入口。

## 3. 输出文件

转写只产出一个文件：UTF-8 编码的 `.srt`，可直接导入播放器与剪辑软件。默认输出名在媒体名后附加模型标签（例如 `example.qwen3-asr-api.srt`、`example.fun-asr.srt`），测试运行（Length limit）会额外带测试后缀。

加 `--debug-raw` 时还会把完整 ASR 原始 JSON 另存为 `<输出文件名>.asr-response.json`，便于反馈断句、标点和时间码问题。

## 常见问题

### 找不到 `ffmpeg` 或 `ffprobe`

安装 FFmpeg 后关闭并重开 PowerShell，再运行 `ffmpeg -version`。不要只把 `ffmpeg.exe` 放在仓库里；更稳妥的是把其 `bin` 目录加入系统 PATH。

macOS 从 Finder 启动 `.app` 时不一定会继承终端里的 PATH。Launcher 会额外尝试 Apple Silicon Homebrew 的 `/opt/homebrew/bin` 和 Intel Homebrew 的 `/usr/local/bin`；如果仍提示缺少 FFmpeg，可把对应目录填入「配置」中的 FFmpeg 路径，并确认其中同时存在 `ffmpeg` 和 `ffprobe`。macOS GUI 的配置会保存到 `~/Library/Application Support/Moy/MAW/.env`，不写入只读或被 App Translocation 隔离的 `.app` 包。

### 提示未配置 API Key

确认 `.env` 与脚本同级；Key 行没有引号、没有额外空格，且没有把 `.env.example` 当成 `.env` 使用。环境变量若存在会覆盖 `.env`。

### API 任务超时或上传失败

先确认网络与 API Key 地域；可在 `.env` 提高 `DASHSCOPE_POLL_TIMEOUT`。文件大小、时长、临时文件策略和计费以[官方百炼语音识别说明](https://help.aliyun.com/zh/model-studio/asr-model/)为准。

### Fun-ASR 提交返回 HTTP 403

MAW 会在 HTTP 状态后继续显示百炼返回的业务 `code`、`message` 和 `request_id`：

- `AllocationQuota.FreeTierOnly`：免费额度已用完且账户启用了“仅使用免费额度”，需要在百炼控制台关闭该开关或开通按量付费。
- `AccessDenied` + `Access denied by API-Key restrictions.`：当前 API Key 使用了自定义权限，但可访问模型范围不包含 Fun-ASR，或者 IP 白名单不允许当前网络。在百炼 API Key 页面编辑该 Key，把权限改为“全部”，或在“自定义”中加入 `fun-asr` 并核对 IP 白名单。若 Key 属于子业务空间，还要由超级管理员为该空间开放 Fun-ASR 模型调用。
- `Workspace.AccessDenied` / `WorkSpaceNotFound`：检查 API Key、地域和 Workspace ID 是否属于同一业务空间。
- 只有通用 `AccessDenied`：检查当前地域是否提供 Fun-ASR、账户是否有模型权限，以及 API Key 是否已失效。

北京地域不填写 Workspace ID 时仍使用兼容域名 `dashscope.aliyuncs.com`；填写后使用官方推荐的 `{WorkspaceId}.cn-beijing.maas.aliyuncs.com` 专属域名。新加坡地域必须填写 Workspace ID。通过 HTTP 提交临时 `oss://` URL 时，MAW 已自动附加官方要求的 `X-DashScope-OssResourceResolve: enable`，无需用户手动处理。
