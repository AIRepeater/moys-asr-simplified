# Moy's ASR Workflow（MAW）

[![English README](https://img.shields.io/badge/README-English-2563eb?style=flat-square)](README-en.md)

[![GitHub Release](https://img.shields.io/github/v/release/Moyf/moys-asr-workflow?display_name=tag&sort=semver)](https://github.com/Moyf/moys-asr-workflow/releases/latest)
[![GitHub Downloads](https://img.shields.io/github/downloads/Moyf/moys-asr-workflow/total?label=downloads)](https://github.com/Moyf/moys-asr-workflow/releases)
[![GitHub Stars](https://img.shields.io/github/stars/Moyf/moys-asr-workflow)](https://github.com/Moyf/moys-asr-workflow/stargazers)
[![License](https://img.shields.io/github/license/Moyf/moys-asr-workflow)](LICENSE)

> 本地媒体 → Qwen/DashScope AI 转写 → SRT 字幕直出（支持批量）。

官网：[MAW 官网](https://moyf.github.io/moys-asr-workflow/)

MAW 是一个刻意收窄的在线 ASR 工作流：选择本地音视频文件，经阿里云百炼（Qwen / Fun-ASR）云端转写后直接生成 SRT 字幕。它提供 Windows/macOS/Linux 图形版 Launcher，也保留命令行入口 `generate_subtitle_qwen_api.py` 供脚本化使用。

## 快速开始

1. [下载最新版](https://github.com/Moyf/moys-asr-workflow/releases/latest)。默认下载带 FFmpeg 的 `MAW-Windows-x64-v*.zip`；如果已安装 `ffmpeg` / `ffprobe`，也可以选择体积更小的 `MAW-lite-Windows-x64-v*.zip`，macOS 下载对应的 `MAW.app` 或 `MAW-lite.app`。
2. 解压并启动 `MAW.exe` 或 `MAW.app`。
3. 在 Launcher 配置阿里云百炼的 API Key，选择媒体文件并点击「生成字幕」。
4. 在输出路径得到 UTF-8 SRT 字幕；批量模式可一次转写多个文件。

第一次使用、API 配置和排错：请从[完整工作流](docs/WORKFLOW.md)开始。

## 核心能力

- 使用阿里云百炼的 `qwen-audio-3.0-asr`（支持上下文与即时热词）、`fun-asr`（说话人分离）或 `qwen3-asr` 转写，直接输出 SRT。
- 支持说话人字幕着色、快速测试（前 2 分钟）、调试运行（保留原始返回）。
- 支持批量转写：队列顺序逐个处理，共用识别设置，结果清单落盘。
- 根入口脚本 `generate_subtitle_qwen_api.py` 可用于批处理和自动化。

## 文档

- [完整工作流](docs/WORKFLOW.md) ：安装、配置、转写和排错。
- [常见问题](docs/FAQ.md) ：Windows 下载解压、启动故障与问题反馈。
- [ASR 服务与配置](docs/PROVIDERS.md) ：服务商选择、Key、费用和隐私边界。

## 重要说明

- 选择云端服务转写时，媒体会直接上传到对应服务商；MAW 没有自己的云端服务器，也不会代管 API Key。
- 费用、数据保留和服务可用性以服务商当前政策为准，详见[ASR 服务与配置](docs/PROVIDERS.md)。

## Star History

<a href="https://www.star-history.com/?repos=Moyf%2Fmoys-asr-workflow&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=Moyf/moys-asr-workflow&type=date&theme=dark&legend=top-left&sealed_token=_PToQhiZM0l9HWee443BsVO_Ent6c7W9XhetqS-GqzovCVxrR29_zMbiDuhZOZRQd-vsEaQhUvF262_K7KBgtzedaZ57WJ3lkgoDR9-QocuvQgw7_My_06JAPfChISW3AJh0fgpAJWVAi1XXRPs7I-5caimIiS5mNri_lJrB_9iBnvtf8_vvhtgAh-fL" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=Moyf/moys-asr-workflow&type=date&legend=top-left&sealed_token=_PToQhiZM0l9HWee443BsVO_Ent6c7W9XhetqS-GqzovCVxrR29_zMbiDuhZOZRQd-vsEaQhUvF262_K7KBgtzedaZ57WJ3lkgoDR9-QocuvQgw7_My_06JAPfChISW3AJh0fgpAJWVAi1XXRPs7I-5caimIiS5mNri_lJrB_9iBnvtf8_vvhtgAh-fL" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=Moyf/moys-asr-workflow&type=date&legend=top-left&sealed_token=_PToQhiZM0l9HWee443BsVO_Ent6c7W9XhetqS-GqzovCVxrR29_zMbiDuhZOZRQd-vsEaQhUvF262_K7KBgtzedaZ57WJ3lkgoDR9-QocuvQgw7_My_06JAPfChISW3AJh0fgpAJWVAi1XXRPs7I-5caimIiS5mNri_lJrB_9iBnvtf8_vvhtgAh-fL" />
 </picture>
</a>

## 反馈与许可

问题和建议请提 [GitHub Issues](https://github.com/Moyf/moys-asr-workflow/issues)；交流可加入 [QQ 群 1079160201](https://qm.qq.com/q/4YtxZIpzxC)。

本项目采用 [AGPL-3.0-only](LICENSE)。
