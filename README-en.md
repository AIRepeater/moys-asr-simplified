# Moy's ASR Workflow (MAW)

[![中文 README](https://img.shields.io/badge/README-%E4%B8%AD%E6%96%87-2563eb?style=flat-square)](README.md)

[![GitHub Release](https://img.shields.io/github/v/release/Moyf/moys-asr-workflow?display_name=tag&sort=semver)](https://github.com/Moyf/moys-asr-workflow/releases/latest)
[![GitHub Downloads](https://img.shields.io/github/downloads/Moyf/moys-asr-workflow/total?label=downloads)](https://github.com/Moyf/moys-asr-workflow/releases)
[![GitHub Stars](https://img.shields.io/github/stars/Moyf/moys-asr-workflow)](https://github.com/Moyf/moys-asr-workflow/stargazers)
[![License](https://img.shields.io/github/license/Moyf/moys-asr-workflow)](LICENSE)

> Local media → Qwen/DashScope ASR → SRT subtitles (single file or batch).

MAW is a deliberately narrow online ASR workflow: pick a local audio/video file, transcribe it with Alibaba Cloud Model Studio (Qwen / Fun-ASR), and get a UTF-8 SRT file. It ships Windows/macOS/Linux Launcher packages and keeps the `generate_subtitle_qwen_api.py` entry script for scripted use.

## Quick start

1. [Download the latest release](https://github.com/Moyf/moys-asr-workflow/releases/latest). The default Windows package is `MAW-Windows-x64-v*.zip` and includes FFmpeg; if `ffmpeg` and `ffprobe` are already available, choose the smaller `MAW-lite-Windows-x64-v*.zip`. macOS users can choose the corresponding `MAW.app` or `MAW-lite.app` package.
2. Extract the package and launch `MAW.exe` or `MAW.app`.
3. Configure your Alibaba Cloud Model Studio API key in the Launcher, choose your media, and click “Generate subtitles”.
4. Collect the UTF-8 SRT at the output path; batch mode transcribes a queue of files.

For installation, provider setup, and troubleshooting, start with the [complete workflow guide](docs/WORKFLOW.md) (currently in Chinese).

## Core capabilities

- Transcribe with `qwen-audio-3.0-asr` (context and instant hotwords), `fun-asr` (speaker diarization), or `qwen3-asr`, straight to SRT.
- Optional speaker-aware subtitle splitting, quick test (first 2 minutes), and debug runs that keep the raw API response.
- Batch transcription: the queue runs sequentially with shared recognition settings and writes a result manifest.
- The root entry script `generate_subtitle_qwen_api.py` supports scripting and automation.

## Documentation

- [Complete workflow](docs/WORKFLOW.md) — installation, provider setup, transcription, and troubleshooting.
- [ASR providers and configuration](docs/PROVIDERS.md) — provider choices, API keys, pricing, and privacy boundaries (Chinese).

## Data and limitations

- When a cloud provider is selected, media is uploaded directly to that provider. MAW has no hosted transcription service and does not manage your API keys.
- Pricing, retention, and availability depend on each provider; see [ASR providers and configuration](docs/PROVIDERS.md).

## Support and license

Please use [GitHub Issues](https://github.com/Moyf/moys-asr-workflow/issues) for questions and bug reports. Chinese-language discussion is available in [QQ group 1079160201](https://qm.qq.com/q/4YtxZIpzxC).

Licensed under [AGPL-3.0-only](LICENSE).
