# Changelog

本项目采用 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 的记录方式。

## [1.0.1] - 2026-07-26

### Added

- 从 ASR 字幕工作流中导出的独立、可公开分发的 API-first 最小版本。
- Qwen ASR API 转写、JSON/SRT 输出、波形字幕编辑器、便携 HTML 和 localhost 编辑器。
- 新用户工作流、维护说明、隐私说明与第三方组件说明。

### Changed

- 去除本地模型、多 ASR 引擎、模型对比、达芬奇脚本与个人资产，只保留一条完整可用链路。
- 音频输入的临时复制改用 Python 标准库，避免依赖 Unix `cp` 命令，保证 Windows PowerShell 环境可用。
