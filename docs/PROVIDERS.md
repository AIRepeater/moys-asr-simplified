# ASR 服务与配置

MAW 本身不托管转写服务。你选择的模型会直接接收待转写媒体；MAW 只负责本地流程与 SRT 生成。

## 选择转写方式

| 模型 | 适合场景 | 备注 |
| --- | --- | --- |
| `qwen-audio-3.0-asr` | 默认选择；支持附加上下文与即时热词 | Launcher 默认模型；支持说话人分离。 |
| `fun-asr` | 需要说话人分离与词级时间戳 | 与 Qwen-Audio 共用百炼 API Key。 |
| `qwen3-asr` | 追求更高识别准确率 | 不支持说话人分离。 |

三个模型都通过阿里云百炼（DashScope）异步文件转写接口调用，使用同一个 `DASHSCOPE_API_KEY`。

## API Key 配置

- 图形版：在 Launcher 中填写并保存到本机环境。
- 源码运行：复制 `.env.example` 为 `.env`，填写 `DASHSCOPE_API_KEY`。
- API Key 只应保存在环境变量或本机 `.env` 中，不要放进命令行、日志、截图或 AI 对话。
- Key 申请见[阿里云百炼官方文档](https://help.aliyun.com/zh/model-studio/get-api-key)。

区域（北京 / 新加坡）、语言、热词、上下文和完整参数见[完整工作流](WORKFLOW.md)。

## 费用

- 免费额度、计费方式与价格会变化，请以[阿里云模型定价](https://help.aliyun.com/zh/model-studio/model-pricing)为准。

## 数据与隐私边界

- MAW 没有自己的云端服务器；转写时媒体直接发送给阿里云百炼。
- 转写结果以 UTF-8 SRT 输出在本机；开启调试运行时另存原始 API 返回 JSON。
- 使用任何第三方服务前，请自行确认其数据保留、训练使用和账户政策。
