# Qwen-Audio Filetrans 开发计划

> 计划分支：`codex/qwen-audio-filetrans`
> 基线：`main`（2026-08-03）
> 当前状态：实现完成，离线测试通过，等待真实短音频验收

## 目标

在现有 `generate_subtitle_qwen_api.py` 的 DashScope 异步文件转写流程中增加
`qwen-audio-3.0-asr-flash-filetrans`，并让它可以在命令行和 Launcher 中选择。
本次只扩展 Qwen API，不引入新的 SDK、模型下载器或本地识别引擎。

## API 差异与实现边界

| 能力 | Qwen3 ASR Filetrans | Qwen-Audio 3.0 ASR Filetrans | MAW 处理方式 |
|---|---|---|---|
| 输入 | `input.file_url` | `input.file_urls`（单元素数组） | 按模型构造请求 |
| 完成结果 | `output.result.transcription_url` | `output.results[].transcription_url` | 按模型轮询 |
| 字/词时间戳开关 | `enable_words` | 固定提供字/词时间戳，不发送旧开关 | 复用现有 items 解析 |
| 预编译热词 | 当前入口未发送 | `parameters.vocabulary_id` | `.env` 或 `--vocabulary-id` |
| 即时热词 | 不支持 | `parameters.vocabulary` | 从 `hotwords.txt` 读取，默认权重 5 |
| 上下文增强 | 当前入口未发送 | `input.context` | `--context` 或 `--context-file` |
| 说话人分离 | 当前入口不支持 | `diarization_enabled` | `--speaker` / `--speaker-colors` |

字段形状和限制以[官方 Qwen-Audio/Fun-ASR HTTP API](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api)
为准。预编译词表需要先按目标模型创建，不能把 Fun-ASR 的 `vocabulary_id`
直接套给 Qwen-Audio；详见[官方热词说明](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy)。

## 实施阶段

1. 模型与请求适配：增加模型识别、`file_urls` 提交、Qwen-Audio 参数和结果轮询。
2. 识别增强配置：增加预编译 `vocabulary_id`、即时热词权重和 context 文件配置。
3. 产品入口：在 Launcher 的百炼模型列表中加入 Qwen-Audio，更新输出文件名标签。
4. 契约测试：覆盖请求 payload、轮询 URL、speaker/时间戳解析和上下文长度限制。
5. 文档与验收：更新 README、工作流、`.env.example`、调研记录和 changelog。

## Launcher 后续改进

Launcher 在选择 Qwen-Audio 后提供以下单次任务字段：

- `Prompt / 上下文`：对应 API 的 `input.context`，最多 400 字符；它是领域词表/前文增强，不是通用 system prompt。
- `即时热词`：每行或逗号分隔，转成 `parameters.vocabulary`；不需要先创建词表。
- `预编译热词 ID`：对应 `parameters.vocabulary_id`，必须先在百炼控制台按 Qwen-Audio 创建。
- `即时热词权重`：支持 1–5 和 50；50 是超级热词，适合少量必须命中的词。

这些字段只进入当前子进程命令行，不保存到 `.env` 或工程 JSON。

## 配置约定

```ini
DASHSCOPE_QWEN_AUDIO_VOCABULARY_ID=
DASHSCOPE_QWEN_AUDIO_HOTWORD_WEIGHT=5
DASHSCOPE_QWEN_AUDIO_CONTEXT_FILE=
DASHSCOPE_FUNASR_VOCABULARY_ID=
```

`DASHSCOPE_QWEN_AUDIO_VOCABULARY_ID` 只对 Qwen-Audio 生效，
`DASHSCOPE_FUNASR_VOCABULARY_ID` 只对 Fun-ASR 生效。即时热词和预编译词表同时
配置时，以服务端对即时热词的处理规则为准；MAW 不会把本地 `.env`、热词内容或
API Key 写入工程 JSON。

## 验收清单

- [x] 旧 Qwen3 和 Fun-ASR 的请求/解析契约不变。
- [x] Qwen-Audio 请求不携带旧的 `enable_words` / `enable_itn` 字段。
- [x] Qwen-Audio 的热词、上下文、预编译词表和 speaker 字段有离线测试。
- [ ] 使用真实短音频验证 API Key、模型权限、地域和词表目标模型配置。
- [ ] 在真实浏览器 Launcher 中确认模型选择、默认输出名和 speaker 颜色开关。
- [x] 合并前运行项目规定的完整 Python/Node 测试和 `git diff --check`。
