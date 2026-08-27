(function () {
  "use strict";

  const STRINGS = {
    zh: { media_output: "1️⃣ 媒体与输出", recognition: "2️⃣ 识别设置", logs: "3️⃣ 日志", provider: "识别方式", test_run: "快速测试", test_run_title: "仅截取前2分钟内容，用于快速测试功能和 API", test_run_override: "快速测试已限定前 2 分钟", debug_raw: "调试运行（保存完整返回数据）", debug_raw_title: "额外保存 ASR 服务端返回的原始 JSON，便于排查断句、标点和时间码问题", hero_desc: "📺 本地媒体 ➜  🤖 AI 转写 ➜ 📝 SRT 字幕", project_home: "项目官网", media: "媒体文件", srt_output: "SRT 输出", choose: "选择", model: "模型", region: "地域", workspace: "工作空间 ID", workspace_hint: "北京地域选填（推荐），新加坡地域必填。", language: "语言", length_limit: "时长上限", language_reset: "重置（自动识别）", language_multi_hint: "可多选；不选即自动识别（仅偏向，不限制）。", language_filter_hint: "默认仅显示常用语言，其余可在「配置」中开启。", settings_language: "语言", show_rare_langs: "显示相对小众的语言", show_rare_langs_hint: "开启后，「语言」列表显示供应商支持的全部语种；关闭时只显示 8 种常用语言。", key: "API Key", save_key: "存入本地环境", key_hint_prefix: "在", key_hint_suffix: "获取 API Key ↗", advanced: "高级选项", start: "✨ 生成字幕", open_folder: "📁 打开输出文件夹", demo_mode: "演示模式", settings_title: "配置", settings_appearance: "外观", theme_light: "明亮模式", theme_dark: "暗色模式", theme_system: "跟随系统设置", settings_ffmpeg: "FFmpeg", ffmpeg_found: "成功定位到 ffmpeg", ffmpeg_path: "FFmpeg 路径", ffmpeg_placeholder: "ffmpeg.exe / ffprobe.exe 所在 bin 目录，或 ffmpeg.exe", ffmpeg_help: "如何安装 FFmpeg ↗", ffmpeg_missing: "未找到 ffmpeg / ffprobe", ffmpeg_need: "需要依赖 ffmpeg 先将视频转成音频后才能发送给服务器转录", change: "更改", ready: "就绪", running: "转写中…", saved: "设置已保存", failed: "失败", done: "完成", key_empty: "未配置密钥", key_loaded: "已加载密钥 {key}", other_language: "English", drop_hint: "拖入音频/视频文件，或点击选择。", flv_media_hint: "flv 无法预览，将会自动转换成 mp4 格式", drop_reject_media: "仅支持以下媒体文件类型：\n{extensions}", drop_reject_txt: "热词来源只支持 .txt 文本文件。", output_collision: "检测到同名输出文件，为避免覆盖，生成的新文件已自动添加后缀。", speaker: "说话人分离", speaker_title: "转写时按说话人切分字幕（仅支持的模型）" },
    en: { media_output: "1️⃣ Media & Output", recognition: "2️⃣ Recognition Settings", logs: "3️⃣ Logs", provider: "Recognition source", test_run: "Quick test", test_run_title: "Trim to the first 2 minutes for a quick workflow and API test", test_run_override: "Quick test is limited to the first 2 minutes", debug_raw: "Debug run (save full response)", debug_raw_title: "Also save the raw ASR service response as JSON for investigating segmentation, punctuation, and timestamps.", hero_desc: "Local media ➜ AI transcription ➜ SRT subtitles", project_home: "Project", media: "Media file", srt_output: "SRT output", choose: "Choose", model: "Model", region: "Region", workspace: "Workspace ID", workspace_hint: "Optional (recommended) for Beijing; required for Singapore.", language: "Language", length_limit: "Length limit", language_reset: "Reset (auto-detect)", language_multi_hint: "Multi-select; empty = auto (bias only).", language_filter_hint: "Only common languages are shown by default. Enable the rest in Settings.", settings_language: "Language", show_rare_langs: "Show less common languages", show_rare_langs_hint: "When enabled, the language list shows every supported language; otherwise it shows 8 common languages.", key: "API Key", save_key: "Save locally", key_hint_prefix: "Get an API Key from", key_hint_suffix: "↗", advanced: "Advanced options", start: "✨ Generate subtitles", open_folder: "📁 Open output folder", demo_mode: "Demo mode", settings_title: "Settings", settings_appearance: "Appearance", theme_light: "Light", theme_dark: "Dark", theme_system: "Follow system", settings_ffmpeg: "FFmpeg", ffmpeg_found: "Located ffmpeg successfully", ffmpeg_path: "FFmpeg path", ffmpeg_placeholder: "bin directory containing ffmpeg/ffprobe, or ffmpeg executable", ffmpeg_help: "How to install FFmpeg ↗", ffmpeg_missing: "ffmpeg / ffprobe not found", ffmpeg_need: "ffmpeg is required to convert video to audio before sending it to the transcription server", change: "Change", ready: "Ready", running: "Running…", saved: "Settings saved", failed: "Failed", done: "Done", key_empty: "No key configured", key_loaded: "Loaded key {key}", other_language: "中文", drop_hint: "Drop an audio/video file here, or choose one.", flv_media_hint: "flv cannot be previewed and will be converted to mp4 automatically", drop_reject_media: "Only the following media file types are supported:\n{extensions}", drop_reject_txt: "Hotword source only accepts .txt text files.", output_collision: "An output file with the same name already exists. To avoid overwriting it, the new output has been given a suffix.", speaker: "Speaker diarization", speaker_title: "Split subtitles by speaker during transcription (supported models only)" }
  };
  Object.assign(STRINGS.zh, {
    mode_label: "转写模式",
    mode_single: "单文件",
    mode_batch: "批量",
    mode_single_hint: "一次处理一个媒体文件。",
    mode_batch_hint: "按队列顺序逐个转写，所有文件共用识别设置。",
    batch_drop_zone: "拖入多个音频/视频文件，或点击添加。",
    batch_queue: "文件队列",
    batch_queue_label: "批量转写队列",
    batch_add: "添加文件",
    batch_clear: "清空",
    batch_drop_hint: "拖入多个音频/视频文件，或反复添加文件；所有文件共用下方识别设置。",
    batch_empty: "尚未添加媒体文件。",
    batch_rejected: "已忽略 {count} 个不支持的文件。",
    batch_duplicate: "文件已在当前列表内",
    batch_outcome_missing: "批量结束时未收到该文件的结果。",
    batch_start: "✨ 开始批量生成",
    batch_stop: "停止全部",
    batch_skip_completed_confirm: "队列中有已处理完成的文件。是否跳过已处理完成的文件？",
    batch_confirm_title: "确认",
    batch_confirm_yes: "是",
    batch_confirm_no: "否",
    stop: "停止",
    batch_starting: "正在启动批量转写……",
    batch_running: "批量转写中……",
    batch_progress: "正在处理第 {current}/{total} 个文件：{name}",
    batch_item_done: "第 {index} 个文件处理完成：{name}",
    batch_item_failed: "第 {index} 个文件处理失败：{name}（详见上方“查看错误”）",
    batch_item_cancelled: "第 {index} 个文件已取消：{name}",
    batch_progress_done: "批量处理完成：成功 {done} 个，失败 {failed} 个。",
    batch_stopping: "正在停止批量转写……",
    batch_complete: "批量转写完成",
    batch_cancelled: "批量转写已停止",
    batch_status_queued: "等待中",
    batch_status_running: "转写中",
    batch_status_done: "已完成",
    batch_status_failed: "失败",
    batch_status_cancelled: "已取消",
    batch_status_skipped: "已跳过",
    batch_log_details: "查看日志",
    batch_error_details: "查看错误",
    batch_open_folder: "打开文件夹",
    batch_remove: "移除",
  });
  Object.assign(STRINGS.en, {
    mode_label: "Transcription mode",
    mode_single: "Single file",
    mode_batch: "Batch",
    mode_single_hint: "Process one media file at a time.",
    mode_batch_hint: "Transcribe the queue sequentially with shared settings.",
    batch_drop_zone: "Drop multiple audio/video files, or click Add files.",
    batch_queue: "File queue",
    batch_queue_label: "Batch transcription queue",
    batch_add: "Add files",
    batch_clear: "Clear",
    batch_drop_hint: "Drop multiple audio/video files or add them repeatedly. Every file uses the shared recognition settings below.",
    batch_empty: "No media files added yet.",
    batch_rejected: "Ignored {count} unsupported file(s).",
    batch_duplicate: "The file is already in the current list.",
    batch_outcome_missing: "No result was reported for this file when the batch finished.",
    batch_start: "✨ Generate batch",
    batch_stop: "Stop all",
    batch_skip_completed_confirm: "Some files in the queue are already complete. Skip completed files?",
    batch_confirm_title: "Confirm",
    batch_confirm_yes: "Yes",
    batch_confirm_no: "No",
    stop: "Stop",
    batch_starting: "Starting batch transcription…",
    batch_running: "Batch transcription in progress…",
    batch_progress: "Processing file {current}/{total}: {name}",
    batch_item_done: "File {index} completed: {name}",
    batch_item_failed: "File {index} failed: {name} (see ‘View error’ above)",
    batch_item_cancelled: "File {index} cancelled: {name}",
    batch_progress_done: "Batch complete: {done} succeeded, {failed} failed.",
    batch_stopping: "Stopping batch transcription…",
    batch_complete: "Batch transcription complete",
    batch_cancelled: "Batch transcription stopped",
    batch_status_queued: "Queued",
    batch_status_running: "Transcribing",
    batch_status_done: "Done",
    batch_status_failed: "Failed",
    batch_status_cancelled: "Cancelled",
    batch_status_skipped: "Skipped",
    batch_log_details: "View log",
    batch_error_details: "View error",
    batch_open_folder: "Open folder",
    batch_remove: "Remove",
  });
  Object.assign(STRINGS.zh, {
    advanced_params: "识别参数",
    advanced_misc: "其他",
    segmentation: "字幕切句",
    max_len: "最大字数",
    min_len: "短句合并阈值",
    gap_split: "停顿切句（毫秒）",
    max_len_placeholder: "默认 21",
    min_len_placeholder: "默认 5",
    gap_split_placeholder: "默认 1500",
    segmentation_hint: "留空使用模型默认值（停顿切句默认 1500ms）；最大/最小字数主要作用于中文，停顿阈值单位为毫秒。",
    qwen_audio_options_title: "Qwen 上下文与热词",
    qwen_audio_context: "附加上下文（Prompt）",
    qwen_audio_context_placeholder: "额外用来辅助 AI 判断的上下文提示词，例如：这是一段关于医药公司的会议记录，参与人员有阿米娅、凯尔希、M3 等人，他们讨论的主要话题是……",
    qwen_audio_context_hint: "领域词表或前文提示；本次任务最多发送 400 个字符，不是通用系统指令。",
    qwen_audio_context_count: "当前字符数：{count}/400",
    qwen_audio_hotwords: "即时热词",
    qwen_audio_hotwords_mode_text: "直接输入",
    qwen_audio_hotwords_mode_file: "从文件读取",
    qwen_audio_hotwords_placeholder: "哔哩哔哩\nMoy\n扑热息痛\nWubba Lubba Dub Dub",
    qwen_audio_hotwords_hint: "如果有容易识别错的单词，可以在此填入，每行一个。模型会在解码过程中提高它们的匹配概率（也可拖入 .txt 文件自动填入）",
    qwen_audio_hotwords_file_placeholder: "拖入或选择 .txt 热词文件",
    qwen_audio_hotwords_file_hint: "支持 UTF-8 编码的 .txt 文件，每行一个热词。",
    qwen_audio_hotwords_weight_override_hint: "支持用“热词: 权重”单独指定某个词的权重，如“obsidian: 5”（中英文冒号皆可）；未指定的热词使用默认权重。",
    qwen_audio_hotwords_loaded: "已将热词文件内容添加到输入框。",
    qwen_audio_hotwords_warning: "有 {count} 项热词不符合规范，发送时会忽略：",
    qwen_audio_hotword_issue_empty: "未填写热词名称",
    qwen_audio_hotword_issue_invalid_weight: "单项权重只能是 1–5 或 50",
    qwen_audio_hotword_issue_text_too_long: "含非 ASCII 字符时最多 15 个字符",
    qwen_audio_hotword_issue_too_many_ascii_words: "纯 ASCII 热词最多 7 个空格分隔的单词",
    qwen_audio_hotword_issue_too_many: "即时热词最多 2000 个",
    qwen_audio_hotword_issue_too_many_super: "权重 50 的热词最多 50 个",
    qwen_audio_hotword_warning_item: "{label}：{reason}",
    qwen_audio_hotword_warning_index: "第 {index} 项",
    qwen_audio_hotword_warning_more: "……其余项目也会在发送时忽略。",
    qwen_audio_hotword_weight: "默认热词权重",
    qwen_audio_hotword_weight_hint: "权重 50 适合少量必须命中的词，最多 50 个。"
  });
  Object.assign(STRINGS.en, {
    advanced_params: "Parameters",
    advanced_misc: "Other",
    segmentation: "Subtitle segmentation",
    max_len: "Max characters",
    min_len: "Short-phrase merge threshold",
    gap_split: "Pause split (ms)",
    max_len_placeholder: "Default: 21",
    min_len_placeholder: "Default: 5",
    gap_split_placeholder: "Default: 1500",
    segmentation_hint: "Leave blank to use the model defaults (pause split defaults to 1500 ms); character thresholds mainly apply to CJK, and the pause threshold is in milliseconds.",
    qwen_audio_options_title: "Qwen context & hotwords",
    qwen_audio_context: "Prompt / context",
    qwen_audio_context_placeholder: "An additional context prompt to help the AI interpret the audio, e.g.: This is a meeting transcript from a pharmaceutical company. Participants include Amiya, Kal'tsit, M3, and others. Their main topic is…",
    qwen_audio_context_hint: "Domain terms or prior context; at most 400 characters per request, not a general system prompt.",
    qwen_audio_context_count: "Characters: {count}/400",
    qwen_audio_hotwords: "Instant hotwords",
    qwen_audio_hotwords_mode_text: "Direct input",
    qwen_audio_hotwords_mode_file: "Load from file",
    qwen_audio_hotwords_placeholder: "Bilibili\nMoy\nParacetamol\nWubba Lubba Dub Dub",
    qwen_audio_hotwords_hint: "If there are words that are easy to misrecognize, enter them here, one per line. The model will increase their matching probability during decoding (you can also drop a .txt file here to fill them in automatically).",
    qwen_audio_hotwords_file_placeholder: "Drop or choose a .txt hotword file",
    qwen_audio_hotwords_file_hint: "UTF-8 .txt files are supported; one hotword per line.",
    qwen_audio_hotwords_weight_override_hint: "Use “hotword: weight” to override one term, e.g. “obsidian: 5” (English or Chinese colon); other terms use the default weight.",
    qwen_audio_hotwords_loaded: "Hotword file content was added to the input.",
    qwen_audio_hotwords_warning: "{count} hotword entries do not meet the format rules and will be ignored:",
    qwen_audio_hotword_issue_empty: "hotword text is empty",
    qwen_audio_hotword_issue_invalid_weight: "individual weight must be 1–5 or 50",
    qwen_audio_hotword_issue_text_too_long: "terms containing non-ASCII characters may have at most 15 characters",
    qwen_audio_hotword_issue_too_many_ascii_words: "ASCII-only terms may contain at most 7 space-separated words",
    qwen_audio_hotword_issue_too_many: "at most 2,000 instant hotwords are supported",
    qwen_audio_hotword_issue_too_many_super: "at most 50 weight-50 hotwords are supported",
    qwen_audio_hotword_warning_item: "{label}: {reason}",
    qwen_audio_hotword_warning_index: "Item {index}",
    qwen_audio_hotword_warning_more: "…the remaining items will also be ignored.",
    qwen_audio_hotword_weight: "Default hotword weight",
    qwen_audio_hotword_weight_hint: "Weight 50 is for a small number of must-hit terms; up to 50 terms."
  });
  const ERROR_TEXT = {
    zh: {
      media_not_found: "媒体文件不存在，请重新选择。",
      api_key_missing: "请填写 API Key，或先在 ⚙ 配置/密钥区保存。",
      workspace_missing: "新加坡地域需要 Workspace ID。",
      context_too_long: "Qwen-Audio 上下文最多 400 个字符。",
      hotwords_file_missing: "请选择存在且为 UTF-8 编码的 .txt 热词文件。",
      output_missing: "请填写 SRT 输出路径。",
      segmentation_invalid: "切句参数无效：请输入整数，并确保最大字数不小于短句合并阈值。",
      ffmpeg_start_failed: "FFmpeg 启动失败（Windows 错误 0xC0000142）。请检查 FFmpeg 是否完整、可执行文件是否被安全软件拦截；本次任务已停止，可以修复后重新尝试。",
      transcription_failed: "转写失败，本次任务已停止。请查看日志后修正问题，再重新尝试。",
      transcription_cancelled: "转写已停止。",
      ffprobe_start_failed: "ffprobe 启动失败（Windows 错误 0xC0000142）。请重新运行 MAW；如果仍然失败，请重新下载并完整解压 MAW，并检查 Windows 安全中心是否拦截了 ffprobe.exe。",
      config_save_failed: (detail) => `无法保存本地配置：${detail || "请检查应用数据目录权限后重试。"}`
    },
    en: {
      media_not_found: "Media file does not exist. Choose it again.",
      api_key_missing: "Enter an API Key, or save one first in Settings / API key.",
      workspace_missing: "Singapore region requires a Workspace ID.",
      context_too_long: "Qwen-Audio context is limited to 400 characters.",
      hotwords_file_missing: "Choose an existing UTF-8 .txt hotword file.",
      output_missing: "Enter an SRT output path.",
      segmentation_invalid: "Invalid segmentation settings: enter integers and ensure max characters is at least the merge threshold.",
      ffmpeg_start_failed: "FFmpeg failed to start (Windows error 0xC0000142). Check that FFmpeg is complete and not blocked by security software, then retry.",
      transcription_failed: "Transcription failed and this run has stopped. Check the log, fix the problem, and retry.",
      transcription_cancelled: "Transcription stopped.",
      ffprobe_start_failed: "ffprobe failed to start (Windows error 0xC0000142). Please run MAW again. If it keeps happening, download and fully extract MAW again, and check Windows Security for a blocked ffprobe.exe.",
      config_save_failed: (detail) => `Could not save local configuration: ${detail || "check the app-data directory permissions and try again."}`
    }
  };

  // Launcher 暂时面向国内用户默认北京；地域和 Workspace 仍保留在请求契约中，后续可重新开放。
  const SHOW_REGIONAL_FIELDS = false;
  // 界面暂不开放时长上限，底层参数保留。
  const SHOW_LENGTH_LIMIT_FIELD = false;

  const HOME_URL = "https://github.com/Moyf/moys-asr-workflow";
  const LAST_MODEL_KEY = "MAW_GUI_LAST_MODEL";
  const LAST_LANGUAGE_KEY = "MAW_GUI_LAST_LANGUAGE";
  const ZOOM_PERCENT_KEY = "MAW_GUI_ZOOM_PERCENT";
  const ZOOM_DEFAULT = 100;
  const ZOOM_STEP = 5;
  const ZOOM_MIN = 80;
  const ZOOM_MAX = 150;
  const THEME_KEY = "MAW_GUI_THEME";
  const $ = (id) => document.getElementById(id);
  const HOTWORD_WEIGHTS = new Set([1, 2, 3, 4, 5, 50]);
  const MAX_HOTWORDS = 2000;
  const MAX_SUPER_HOTWORDS = 50;
  const MEDIA_EXTS = new Set([".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".ts", ".m4v", ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"]);
  const state = { lang: "zh", running: false, lastLogMessage: "", result: null, config: null, srtAuto: true, testSuffixAdded: false, dropTarget: "", theme: "system" };
  const dragState = { depth: 0 };
  let api = null;
  let prefsTimer = 0;

  function mockApi() {
    let saved = { apiKey: "", region: "beijing", language: "", workspaceId: "", guiLang: "zh" };
    return {
      get_config: async () => ({
        apiKey: saved.apiKey,
        maskedApiKey: saved.apiKey ? "sk-…demo" : "",
        providerId: "qwen",
        modelId: "qwen-audio-3.0-asr-flash-filetrans",
        lastModel: localStorage.getItem(LAST_MODEL_KEY),
        lastLanguage: localStorage.getItem(LAST_LANGUAGE_KEY),
        zoomPercent: Number(localStorage.getItem(ZOOM_PERCENT_KEY)) || ZOOM_DEFAULT,
        region: saved.region,
        language: saved.language,
        workspaceId: saved.workspaceId,
        guiLang: saved.guiLang,
        showRareLangs: saved.showRareLangs || false,
        appVersion: "1.5.0-beta.4",
        providers: [
          {
            id: "qwen",
            label: "阿里云百炼（Qwen）",
            keyUrl: "https://help.aliyun.com/zh/model-studio/get-api-key",
            apiKey: saved.apiKey,
            maskedApiKey: saved.apiKey ? "sk-…demo" : "",
            supportsSpeaker: true,
            multiLanguage: false,
            commonLanguages: ["", "zh", "yue", "en"],
            models: [
              { id: "qwen-audio-3.0-asr-flash-filetrans", label: "qwen-audio-3.0-asr（热词 / 上下文）", envKey: "DASHSCOPE_API_KEY", note: "支持即时热词、上下文与说话人分离", supportsSpeaker: true, supportsContext: true, supportsHotwords: true, supportsVocabulary: true, languages: [{ id: "", label: "自动识别" }, { id: "zh", label: "中文 / Chinese" }, { id: "yue", label: "粤语 / Cantonese" }, { id: "en", label: "英语 / English" }] },
              { id: "fun-asr", label: "fun-asr（支持说话人）", envKey: "DASHSCOPE_API_KEY", note: "支持说话人分离与词级时间戳", supportsSpeaker: true, languages: [{ id: "", label: "自动识别" }, { id: "zh", label: "中文 / Chinese" }, { id: "en", label: "英语 / English" }] },
              { id: "qwen3-asr-flash-filetrans", label: "qwen3-asr（准确率更高）", envKey: "DASHSCOPE_API_KEY", note: "", supportsSpeaker: false, languages: [{ id: "", label: "自动识别" }, { id: "zh", label: "中文 / Mandarin" }, { id: "en", label: "英语 / English" }] }
            ],
            regions: [{ id: "beijing", label: "北京（华北 2，默认）" }, { id: "singapore", label: "新加坡（需要 Workspace ID）" }],
            languages: [{ id: "", label: "自动识别" }, { id: "zh", label: "中文 / Mandarin" }, { id: "en", label: "英语 / English" }, { id: "da", label: "丹麦语 / Danish" }]
          }
        ]
      }),
      default_output: async ({ mediaPath, modelId, testRun }) => ({ ok: true, path: mediaPath ? mediaPath.replace(/\.[^.\\/]+$/, `${modelId === "fun-asr" ? ".fun-asr" : (modelId === "qwen-audio-3.0-asr-flash-filetrans" ? ".qwen-audio" : ".qwen3-asr-api")}${testRun ? "-test" : ""}.srt`) : "" }),
      choose_file: async ({ kind }) => ({ ok: true, path: kind === "hotwords" ? "D:\\Demo\\hotwords.txt" : "D:\\Demo\\clip.mp4" }),
      read_hotword_file: async () => ({ ok: true, path: "D:\\Demo\\hotwords.txt", text: "张三\n阿里云百炼\n专业术语\n" }),
      save_settings: async (payload) => { saved = { ...saved, ...payload }; return { ok: true, maskedApiKey: payload.apiKey ? "sk-…mock" : "", message: "mock saved" }; },
      save_prefs: async (payload) => { if (Object.prototype.hasOwnProperty.call(payload, "modelId")) localStorage.setItem(LAST_MODEL_KEY, payload.modelId || ""); if (Object.prototype.hasOwnProperty.call(payload, "language")) localStorage.setItem(LAST_LANGUAGE_KEY, payload.language || ""); if (Object.prototype.hasOwnProperty.call(payload, "showRareLangs")) saved.showRareLangs = Boolean(payload.showRareLangs); if (Object.prototype.hasOwnProperty.call(payload, "zoomPercent")) localStorage.setItem(ZOOM_PERCENT_KEY, String(payload.zoomPercent)); return { ok: true, zoomPercent: Number(localStorage.getItem(ZOOM_PERCENT_KEY)) || ZOOM_DEFAULT }; },
      open_url: async ({ url }) => { window.open(url, "_blank"); return { ok: true }; },
      check_ffmpeg: async () => ({ ok: true, found: true, directory: "D:\\FFmpeg\\bin", ffmpeg: "D:\\FFmpeg\\bin\\ffmpeg.exe", ffprobe: "D:\\FFmpeg\\bin\\ffprobe.exe" }),
      save_ffmpeg_path: async ({ path }) => ({ ok: Boolean(path), found: Boolean(path), directory: path || "", ffmpeg: path || "", ffprobe: path || "" }),
      choose_folder: async () => ({ ok: true, path: "D:\\Demo" }),
      open_file: async ({ path }) => ({ ok: Boolean(path) }),
      open_containing_folder: async ({ path }) => ({ ok: Boolean(path) }),
      start_transcription: async () => { setTimeout(() => window.MAWLauncher.onBackendEvent({ type: "log", message: "[mock] 上传完成" }), 250); setTimeout(() => window.MAWLauncher.onBackendEvent({ type: "done", result: { srtPath: "D:\\Demo\\clip.srt" } }), 900); return { ok: true }; },
      cancel_transcription: async () => { setTimeout(() => window.MAWLauncher.onBackendEvent({ type: "error", code: "transcription_cancelled", detail: "Transcription cancelled" }), 120); return { ok: true }; },
      start_batch_transcription: async ({ items }) => {
        window.MAWLauncher.onBackendEvent({ type: "batchStarted", total: items.length });
        items.forEach((item, index) => {
          setTimeout(() => window.MAWLauncher.onBackendEvent({ type: "batchItem", itemId: item.id, index, mediaPath: item.mediaPath, status: "running" }), index * 650 + 100);
          setTimeout(() => window.MAWLauncher.onBackendEvent({ type: "batchItemLog", itemId: item.id, index, message: `[mock] ${item.mediaPath}` }), index * 650 + 250);
          setTimeout(() => window.MAWLauncher.onBackendEvent({ type: "batchItem", itemId: item.id, index, mediaPath: item.mediaPath, status: "done", result: { srtPath: item.mediaPath.replace(/\.[^.\\/]+$/u, ".srt") } }), index * 650 + 550);
        });
        setTimeout(() => window.MAWLauncher.onBackendEvent({ type: "batchDone", total: items.length, cancelled: false }), items.length * 650 + 600);
        return { ok: true };
      },
      cancel_batch_transcription: async () => { setTimeout(() => window.MAWLauncher.onBackendEvent({ type: "batchDone", cancelled: true }), 120); return { ok: true }; },
      open_output_folder: async () => ({ ok: true }),
      get_emoji_font_path: async () => ({ ok: true, path: "" })
    };
  }

  const t = (key) => STRINGS[state.lang][key] || key;
  function compactDetail(detail) { return String(detail || "").replace(/\s+/g, " ").trim(); }
  function errText(code, detail) { const entry = ERROR_TEXT[state.lang][code]; const compact = compactDetail(detail); if (typeof entry === "function") return entry(compact); return entry || compact || t("failed"); }
  const ext = (path) => (path.match(/\.[^.\\/]+$/)?.[0] || "").toLowerCase();
  const provider = () => state.config.providers.find((item) => item.id === $("provider").value) || state.config.providers[0];
  const selectedModel = () => provider().models.find((item) => item.id === $("model").value) || provider().models[0];
  function appendMessageText(container, text) {
    String(text).split("\n").forEach((part, index) => {
      if (index > 0) container.append(document.createElement("br"));
      if (part) container.append(document.createTextNode(part));
    });
  }
  function renderMessage(container, message) {
    container.replaceChildren();
    const value = String(message || "");
    const urlPattern = /https?:\/\/[^\s<>"'|)\]}，。；：！？）】》」』]+/gi;
    let cursor = 0;
    for (const match of value.matchAll(urlPattern)) {
      const index = match.index ?? cursor;
      const rawUrl = match[0];
      const url = rawUrl.replace(/[),.;:!?，。；：！？）】》]+$/u, "");
      const trailing = rawUrl.slice(url.length);
      if (index > cursor) appendMessageText(container, value.slice(cursor, index));
      if (!url) {
        appendMessageText(container, rawUrl);
      } else {
        const link = document.createElement("a");
        link.href = url;
        link.textContent = url;
        link.className = "status-link";
        link.addEventListener("click", (event) => { event.preventDefault(); bridge("open_url", { url }); });
        container.append(link);
        if (trailing) appendMessageText(container, trailing);
      }
      cursor = index + rawUrl.length;
    }
    if (cursor < value.length) appendMessageText(container, value.slice(cursor));
  }
  const setStatus = (message) => { renderMessage($("status"), message); };
  const appendLog = (text, { inline = false } = {}) => { const log = $("log"); const needsSpace = inline && log.textContent && !log.textContent.endsWith("\n"); log.textContent += `${needsSpace ? " " : ""}${text}${inline ? "" : "\n"}`; log.scrollTop = log.scrollHeight; state.lastLogMessage = text; const latest = $("logLatest"); const inlineLatest = inline && latest.dataset.inline === "true"; latest.textContent = inlineLatest ? `${latest.textContent} ${text}` : text; latest.dataset.inline = String(inline); latest.classList.remove("hidden"); };
  function confirmAction(message) { $("batchConfirmMessage").textContent = String(message || ""); $("batchConfirmModal").classList.remove("hidden"); $("batchConfirmYes").focus(); return new Promise((resolve) => { window.MAWLauncher.confirmResolve = resolve; }); }
  function finishConfirm(value) { const resolve = window.MAWLauncher.confirmResolve; window.MAWLauncher.confirmResolve = null; $("batchConfirmModal").classList.add("hidden"); resolve?.(value); }

  function resolveTheme() { if (state.theme === "light" || state.theme === "dark") return state.theme; return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; }
  function applyTheme() { if (resolveTheme() === "light") document.documentElement.dataset.theme = "light"; else delete document.documentElement.dataset.theme; $("themeLight").classList.toggle("active", state.theme === "light"); $("themeDark").classList.toggle("active", state.theme === "dark"); $("themeSystem").classList.toggle("active", state.theme === "system"); }
  function setTheme(pref) { state.theme = pref; try { localStorage.setItem(THEME_KEY, pref); } catch (error) { /* localStorage 不可用时仅作用于本次会话 */ } applyTheme(); }

  // keycap 表情（1️⃣ 等）依赖彩色 emoji 字体：后端把 Noto Color Emoji 缓存到本机
  // 后提供 file:// URI，这里注入 @font-face；注入一次即可，重复事件会被跳过。
  function injectEmojiFont(uri) {
    if (!uri || document.querySelector("style[data-emoji-font]")) return;
    const style = document.createElement("style");
    style.dataset.emojiFont = "1";
    style.textContent = `@font-face{font-family:"MAW Emoji";src:url("${uri}") format("truetype");font-weight:400;font-display:swap;}`;
    document.head.appendChild(style);
  }

  async function bridge(method, payload = {}) {
    try {
      return await api[method](payload);
    } catch (error) {
      const message = `${method}: ${error && error.message ? error.message : error}`;
      appendLog(`[bridge] ${message}`);
      setStatus(message);
      return { ok: false, error: message };
    }
  }

  function waitForBackend(timeoutMs = 1800) {
    if (window.pywebview && window.pywebview.api) return Promise.resolve(window.pywebview.api);
    return new Promise((resolve) => {
      let settled = false;
      const finish = (value) => { if (!settled) { settled = true; resolve(value); } };
      window.addEventListener("pywebviewready", () => finish(window.pywebview && window.pywebview.api ? window.pywebview.api : null), { once: true });
      setTimeout(() => finish(window.pywebview && window.pywebview.api ? window.pywebview.api : null), timeoutMs);
    });
  }

  function setRunning(running) { state.running = running; $("progress").classList.toggle("hidden", !running); $("start").classList.toggle("hidden", running); $("stop").classList.toggle("hidden", !running); $("start").disabled = running; $("stop").disabled = !running; setStatus(running ? t("running") : t("ready")); }
  function fillSelect(id, items, value) { const el = $(id); el.innerHTML = ""; items.forEach((item) => el.add(new Option(item.label, item.id))); el.value = value ?? ""; }
  function setError(field, message) { const input = $(field); const hint = $(`${field}Error`); if (input) input.classList.toggle("invalid", Boolean(message)); if (hint) { renderMessage(hint, message); hint.classList.toggle("visible", Boolean(message)); } }
  function setOutputNotice(message) { const notice = $("srtPathNotice"); if (!notice) return; renderMessage(notice, message); notice.classList.toggle("hidden", !message); }
  function mediaDropError() { const separator = state.lang === "zh" ? "、" : ", "; return t("drop_reject_media").replace("{extensions}", Array.from(MEDIA_EXTS).join(separator)); }
  function clearErrors() { ["mediaPath", "srtPath", "apiKey", "workspaceId", "maxLen", "minLen", "gapSplit", "qwenAudioContext", "qwenAudioHotwords", "qwenAudioHotwordsFile", "ffmpegPath"].forEach((field) => setError(field, "")); }
  function formPayload() { return { providerId: $("provider").value, modelId: $("model").value, mediaPath: $("mediaPath").value.trim(), srtPath: $("srtPath").value.trim(), apiKey: $("apiKey").value.trim(), region: $("region").value, workspaceId: $("workspaceId").value.trim(), language: languageValue(), lengthLimit: $("lengthLimit").value.trim(), maxLen: $("maxLen").value.trim(), minLen: $("minLen").value.trim(), gapSplit: $("gapSplit").value.trim(), qwenAudioContext: $("qwenAudioContext").value.trim(), qwenAudioHotwordsMode: $("qwenAudioHotwordsMode").value, qwenAudioHotwords: $("qwenAudioHotwords").value.trim(), qwenAudioHotwordsFile: $("qwenAudioHotwordsFile").value.trim(), qwenAudioHotwordWeight: $("qwenAudioHotwordWeight").value, testRun: $("testRun").checked, debugRaw: $("debugRaw").checked, speaker: $("speaker").checked, guiLang: state.lang }; }
  function renderChevron(id) { const arrow = $(id)?.querySelector(".chevron"); if (arrow) arrow.textContent = $(id).classList.contains("collapsed") ? "▸" : "▾"; }
  function renderKeyStatus() { const masked = state.config ? provider().maskedApiKey : ""; $("keyStatus").textContent = masked ? t("key_loaded").replace("{key}", masked) : t("key_empty"); }
  function syncQwenAudioOptions(model) { const enabled = provider().id === "qwen" && Boolean(model?.supportsContext || model?.supportsHotwords); $("qwenAudioOptions").classList.toggle("hidden", !enabled); $("qwenAudioContextField").classList.toggle("hidden", !(provider().id === "qwen" && model?.supportsContext)); $("qwenAudioHotwordsSection").classList.toggle("hidden", !(provider().id === "qwen" && model?.supportsHotwords)); syncQwenAudioHotwordsMode(); }
  function renderPromptCharacterCount() { const count = Array.from($("qwenAudioContext").value).length; const counter = $("qwenAudioContextCount"); counter.textContent = t("qwen_audio_context_count").replace("{count}", String(count)); counter.classList.toggle("over-limit", count > 400); }
  function splitHotwordEntries(value, ignoreComments = false) { return String(value || "").split(/[\n,，;；]+/u).map((word) => word.trim()).filter((word) => word && (!ignoreComments || !word.startsWith("#"))); }
  function parseHotwordEntry(value, defaultWeight) { const match = value.match(/^(.+?)\s*[:：]\s*(\d+)\s*$/u); const text = (match ? match[1] : value).trim(); if (!text) return { code: "empty" }; const weight = match ? Number(match[2]) : defaultWeight; if (!HOTWORD_WEIGHTS.has(weight)) return { code: "invalid_weight" }; const chars = Array.from(text).length; if (Array.from(text).some((char) => char.codePointAt(0) > 127) && chars > 15) return { code: "text_too_long" }; if (!Array.from(text).some((char) => char.codePointAt(0) > 127) && text.split(/\s+/u).filter(Boolean).length > 7) return { code: "too_many_ascii_words" }; return { text, weight }; }
  function collectHotwordWarnings(value, weight, ignoreComments = false) { const parsed = new Map(); const issues = []; splitHotwordEntries(value, ignoreComments).forEach((raw, index) => { const entry = parseHotwordEntry(raw, weight); if (entry.code) { issues.push({ index: index + 1, code: entry.code, text: raw }); return; } parsed.set(entry.text, { index: index + 1, entry }); }); let validCount = 0; let superCount = 0; Array.from(parsed.values()).sort((left, right) => left.index - right.index).forEach(({ index, entry }) => { if (validCount >= MAX_HOTWORDS) { issues.push({ index, code: "too_many", text: entry.text }); return; } if (entry.weight === 50 && superCount >= MAX_SUPER_HOTWORDS) { issues.push({ index, code: "too_many_super", text: entry.text }); return; } validCount += 1; if (entry.weight === 50) superCount += 1; }); return issues; }
  function hotwordWarningLabel(issue) { const text = String(issue.text || "").trim(); if (!text) return t("qwen_audio_hotword_warning_index").replace("{index}", String(issue.index)); const chars = Array.from(text); const truncated = chars.length > 16 ? `${chars.slice(0, 16).join("")}…` : text; return state.lang === "zh" ? `「${truncated}」` : `“${truncated}”`; }
  function renderHotwordWarnings(value = $("qwenAudioHotwords").value, weight = Number($("qwenAudioHotwordWeight").value), ignoreComments = false) { const warning = $("qwenAudioHotwordsWarning"); const issues = collectHotwordWarnings(value, weight, ignoreComments); if (!issues.length) { warning.textContent = ""; warning.classList.remove("visible"); return; } const details = issues.slice(0, 5).map((issue) => t("qwen_audio_hotword_warning_item").replace("{label}", hotwordWarningLabel(issue)).replace("{reason}", t(`qwen_audio_hotword_issue_${issue.code}`))); if (issues.length > details.length) details.push(t("qwen_audio_hotword_warning_more")); warning.textContent = `${t("qwen_audio_hotwords_warning").replace("{count}", String(issues.length))}\n${details.join("\n")}`; warning.classList.add("visible"); }
  function syncQwenAudioHotwordsMode() { const fileMode = $("qwenAudioHotwordsMode").value === "file"; $("qwenAudioHotwordsTextField").classList.toggle("hidden", fileMode); $("qwenAudioHotwordsFileField").classList.toggle("hidden", !fileMode); renderHotwordWarnings(fileMode ? "" : $("qwenAudioHotwords").value, Number($("qwenAudioHotwordWeight").value)); }
  function setHotwordsMode(mode) { $("qwenAudioHotwordsMode").value = mode; $("qwenAudioHotwordsModeText").classList.toggle("active", mode === "text"); $("qwenAudioHotwordsModeFile").classList.toggle("active", mode === "file"); syncQwenAudioHotwordsMode(); }
  function clearDropState() { dragState.depth = 0; state.dropTarget = ""; setDropHighlight(false); ["qwenAudioHotwords", "qwenAudioHotwordsFile"].forEach((id) => $(id)?.classList.remove("drag-over")); }
  function setQwenAudioHotwordsFile(path) { if (ext(path) !== ".txt") { setError("qwenAudioHotwordsFile", errText("hotwords_file_missing", "")); return false; } $("qwenAudioHotwordsFile").value = path; setHotwordsMode("file"); setError("qwenAudioHotwordsFile", ""); return true; }
  async function loadHotwordFile(path, appendToText = false) { if (ext(path) !== ".txt") { setError("qwenAudioHotwordsFile", errText("hotwords_file_missing", "")); clearDropState(); return; } const result = await bridge("read_hotword_file", { path }); if (!result.ok) { applyErrorResult(result, false); clearDropState(); return; } if (appendToText) { const incoming = String(result.text || "").trim(); if (incoming) { const current = $("qwenAudioHotwords").value.trimEnd(); $("qwenAudioHotwords").value = current ? `${current}\n${incoming}` : incoming; } setHotwordsMode("text"); renderHotwordWarnings($("qwenAudioHotwords").value); setStatus(t("qwen_audio_hotwords_loaded")); } else { setQwenAudioHotwordsFile(result.path || path); renderHotwordWarnings(String(result.text || ""), Number($("qwenAudioHotwordWeight").value), true); } clearDropState(); }
  function renderLanguage() { document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en"; document.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = t(node.dataset.i18n); }); document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => { node.placeholder = t(node.dataset.i18nPlaceholder); }); document.querySelectorAll("[data-i18n-title]").forEach((node) => { node.title = t(node.dataset.i18nTitle); }); document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => { node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel)); }); $("langToggle").textContent = t("other_language"); $("demoBadge").textContent = t("demo_mode"); renderKeyStatus(); renderPromptCharacterCount(); renderHotwordWarnings(); window.MAWLauncher?.onLanguageChanged?.(); }
  function applyProvider(persistReset = false) { const current = provider(); const preferred = state.config.lastModel; const fallback = state.config.modelId || current.models[0]?.id; const modelValue = current.models.some((item) => item.id === preferred) ? preferred : (current.models.some((item) => item.id === fallback) ? fallback : current.models[0]?.id); fillSelect("model", current.models, modelValue); fillSelect("region", current.regions, state.config.region || "beijing"); $("apiKeyField").classList.toggle("hidden", current.requiresApiKey === false); $("openKeyUrl").classList.toggle("hidden", current.requiresApiKey === false); $("apiKey").value = current.apiKey || ""; $("openKeyUrl").textContent = current.label; $("providerNote").textContent = current.note || ""; $("providerNote").classList.toggle("hidden", !current.note); applySelectedModel(persistReset); $("regionField").classList.toggle("hidden", !SHOW_REGIONAL_FIELDS || current.regions.length === 0); renderKeyStatus(); syncWorkspace(); syncAdvancedParamsGroup(); }
  function syncSpeakerField(model) { $("speakerField").classList.toggle("hidden", !Boolean(model?.supportsSpeaker)); if (!model?.supportsSpeaker) $("speaker").checked = false; }
  function applySelectedModel(persistReset = false) { const current = provider(); const model = selectedModel(); $("modelNote").textContent = model.note || ""; applyProviderLanguages(current, model, persistReset); syncQwenAudioOptions(model); syncSpeakerField(model); syncDefaultOutput(); if (persistReset) savePrefsDebounced({ modelId: model.id, language: languageValue() }); }
  function applyProviderLanguages(current, model, persistReset = false) { const el = $("language"); $("languageGroup").classList.toggle("hidden", current.supportsLanguage === false); const previous = el.multiple ? Array.from(el.selectedOptions).map((o) => o.value) : (el.value ? [el.value] : []); const remembered = state.config.lastLanguage; const wanted = previous.length && persistReset ? previous : (remembered !== null && remembered !== undefined ? (remembered ? remembered.split(",") : []) : [state.config.language].filter(Boolean)); el.multiple = Boolean(current.multiLanguage); $("advancedOptionsGrid").classList.toggle("single-language", !current.multiLanguage); if (current.multiLanguage) el.size = 6; else el.removeAttribute("size"); const showRare = Boolean(state.config.showRareLangs); const commons = current.commonLanguages || []; const available = model.languages?.length ? model.languages : current.languages; const visible = !showRare && commons.length ? available.filter((item) => commons.includes(item.id)) : available; fillSelect("language", visible, ""); const codes = new Set(visible.map((item) => item.id)); const restored = wanted.filter((code) => code && codes.has(code)); if (current.multiLanguage) { Array.from(el.options).forEach((o) => { o.selected = restored.includes(o.value); }); } else { el.value = restored[0] || ""; } $("languageHint").classList.toggle("hidden", !current.multiLanguage); $("languageFilterHint").classList.toggle("hidden", showRare || commons.length === 0); $("languageReset").classList.toggle("hidden", !current.multiLanguage); }
  function languageValue() { const el = $("language"); if (el.multiple) return Array.from(el.selectedOptions).map((o) => o.value).filter(Boolean).join(","); return el.value; }
  function syncWorkspace() { $("workspaceField").classList.toggle("hidden", !SHOW_REGIONAL_FIELDS || provider().regions.length === 0); }
  function syncAdvancedParamsGroup() { const group = $("advancedParamsGroup"); group.classList.toggle("hidden", !Array.from(group.querySelectorAll(".field")).some((field) => !field.classList.contains("hidden"))); }
  function appendTestSuffix(path) { const value = String(path || "").trim(); if (!value || /-test(?=\.[^./\\]+$)/iu.test(value)) return value; const separator = Math.max(value.lastIndexOf("/"), value.lastIndexOf("\\")); const dot = value.lastIndexOf("."); if (dot <= separator) return `${value}-test`; return `${value.slice(0, dot)}-test${value.slice(dot)}`; }
  function removeTestSuffix(path) { return String(path || "").replace(/-test(?=\.[^./\\]+$)/iu, ""); }
  function syncTestRun() { const on = $("testRun").checked; $("testRunHint").classList.toggle("hidden", !on); $("lengthLimit").disabled = on; if (state.srtAuto) { void syncDefaultOutput(); return; } const current = $("srtPath").value.trim(); if (on) { const next = appendTestSuffix(current); state.testSuffixAdded = Boolean(current && next !== current); $("srtPath").value = next; } else if (state.testSuffixAdded) { $("srtPath").value = removeTestSuffix(current); state.testSuffixAdded = false; } }
  function savePrefsDebounced(payload) { clearTimeout(prefsTimer); prefsTimer = setTimeout(() => bridge("save_prefs", payload), 300); }
  function normalizeZoomPercent(value) { const parsed = Number(value); if (!Number.isFinite(parsed)) return ZOOM_DEFAULT; return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(parsed / ZOOM_STEP) * ZOOM_STEP)); }
  function applyZoomPercent(value) { const zoomPercent = normalizeZoomPercent(value); document.documentElement.style.zoom = `${zoomPercent}%`; state.config.zoomPercent = zoomPercent; return zoomPercent; }
  function viewportPixelsToPage(value) { return value / (normalizeZoomPercent(state.config?.zoomPercent) / 100); }
  function persistZoomPercent(value) { const zoomPercent = applyZoomPercent(value); savePrefsDebounced({ zoomPercent }); }
  function handleZoomWheel(event) { if (!event.ctrlKey) return; const direction = Math.sign(event.deltaY); if (!direction) return; event.preventDefault(); const zoomPercent = applyZoomPercent(state.config.zoomPercent - direction * ZOOM_STEP); savePrefsDebounced({ zoomPercent }); }
  function handleZoomKeydown(event) {
    if (!event.ctrlKey || event.altKey || event.metaKey || event.target?.closest?.("input, textarea, select, [contenteditable]")) return;
    const direction = event.key === "=" || event.key === "+" ? 1 : (event.key === "-" ? -1 : 0);
    if (!direction && event.key !== "0") return;
    event.preventDefault();
    persistZoomPercent(event.key === "0" ? ZOOM_DEFAULT : state.config.zoomPercent + direction * ZOOM_STEP);
  }
  async function syncDefaultOutput() { const result = await bridge("default_output", { mediaPath: $("mediaPath").value.trim(), providerId: $("provider").value, modelId: $("model").value, testRun: $("testRun").checked }); const path = result.ok ? result.path : ""; $("srtPath").placeholder = path; if (state.srtAuto) { $("srtPath").value = path; if (path) setError("srtPath", ""); setOutputNotice(result.renamed ? t("output_collision") : ""); } else setOutputNotice(""); }
  function syncFlvHints() { $("mediaPathFlvHint")?.classList.toggle("hidden", ext($("mediaPath").value.trim()) !== ".flv"); }
  function setMedia(path) { $("mediaPath").value = path; setError("mediaPath", ""); setOutputNotice(""); syncFlvHints(); syncDefaultOutput(); }
  function applyErrorResult(result, logDetail = true) { const message = errText(result.code, result.detail || result.error); if (result.field) setError(result.field, message); setStatus(message); if (logDetail && (result.detail || result.error)) appendLog(`[error] ${result.code || "backend_error"}: ${result.detail || result.error}`); }
  function validateSegmentation(data) { for (const [field, minimum] of [["maxLen", 1], ["minLen", 1], ["gapSplit", 0]]) { const value = data[field]; if (!value) continue; if (!/^\d+$/u.test(value) || !Number.isSafeInteger(Number(value)) || Number(value) < minimum) return fail(field, errText("segmentation_invalid", "")); } if (data.maxLen && data.minLen && Number(data.maxLen) < Number(data.minLen)) return fail("maxLen", errText("segmentation_invalid", "")); return true; }
  function validateForm() { clearErrors(); const data = formPayload(); if (!data.mediaPath) return fail("mediaPath", errText("media_not_found", "")); if (!data.srtPath) return fail("srtPath", errText("output_missing", "")); if (!validateSegmentation(data)) return false; if (provider().requiresApiKey !== false && !data.apiKey && !provider().apiKey) return fail("apiKey", errText("api_key_missing", "")); if (provider().regions.length > 0 && data.region === "singapore" && !data.workspaceId) return fail("workspaceId", errText("workspace_missing", "")); if (provider().id === "qwen" && selectedModel().supportsContext && Array.from(data.qwenAudioContext).length > 400) return fail("qwenAudioContext", errText("context_too_long", "")); if (provider().id === "qwen" && selectedModel().supportsHotwords && data.qwenAudioHotwordsMode === "file" && ext(data.qwenAudioHotwordsFile) !== ".txt") return fail("qwenAudioHotwordsFile", errText("hotwords_file_missing", "")); return true; }
  function fail(field, message) { setError(field, message); setStatus(message); const input = $(field); if (input && input.scrollIntoView) input.scrollIntoView({ behavior: "smooth", block: "center" }); return false; }
  function toggle(id) { $(id).classList.toggle("collapsed"); renderChevron(id); }
  function setupScrollbarFlash() {
    const VISIBLE_MS = 900;
    const bind = (target, host) => { let timer = 0; target.addEventListener("scroll", () => { host.classList.add("scrolling"); clearTimeout(timer); timer = setTimeout(() => host.classList.remove("scrolling"), VISIBLE_MS); }, { passive: true }); };
    bind(window, document.documentElement);
    document.querySelectorAll(".log, .modal-card, .settings-scroll, textarea").forEach((el) => bind(el, el));
  }
  function hasFileDrag(event) { return !event.dataTransfer || Array.from(event.dataTransfer.types || []).includes("Files"); }
  function setDropHighlight(active) { $("mediaCard").classList.toggle("drag-over", active); }
  function isInsideMediaCard(node) { return node instanceof Node && $("mediaCard").contains(node); }
  function onDragEnter(event) { if (!hasFileDrag(event) || !isInsideMediaCard(event.target)) return; event.preventDefault(); if (isInsideMediaCard(event.relatedTarget)) return; dragState.depth += 1; setDropHighlight(true); }
  function onDragLeave(event) { if (!isInsideMediaCard(event.target)) return; if (isInsideMediaCard(event.relatedTarget)) return; dragState.depth = Math.max(0, dragState.depth - 1); if (dragState.depth === 0) setDropHighlight(false); }
  function bindDropField(id, target, controlId) { const field = $(id); const control = $(controlId || id); field.addEventListener("dragenter", (event) => { if (!hasFileDrag(event)) return; event.preventDefault(); state.dropTarget = target; control.classList.add("drag-over"); }); field.addEventListener("dragover", (event) => { if (!hasFileDrag(event)) return; event.preventDefault(); state.dropTarget = target; control.classList.add("drag-over"); }); field.addEventListener("dragleave", (event) => { if (!field.contains(event.relatedTarget)) { control.classList.remove("drag-over"); if (state.dropTarget === target) state.dropTarget = ""; } }); }
  function handleRoutedDrop(path) { const target = state.dropTarget; clearDropState(); const suffix = ext(path || ""); if (target === "text" || target === "file") { if (suffix === ".txt") { void loadHotwordFile(path, target === "text"); } else setError(target === "text" ? "qwenAudioHotwords" : "qwenAudioHotwordsFile", t("drop_reject_txt")); return; } if (suffix === ".txt") { void loadHotwordFile(path, false); return; } if (MEDIA_EXTS.has(suffix)) { setMedia(path); setStatus(t("media")); return; } setError("mediaPath", mediaDropError()); }
  async function refreshFfmpeg() { const result = await bridge("check_ffmpeg"); $("modalFfmpegFound").classList.toggle("hidden", !result.found); $("modalFfmpegMissing").classList.toggle("hidden", Boolean(result.found)); $("ffmpegPathBox").classList.toggle("hidden", Boolean(result.found)); $("settingsDot").classList.toggle("hidden", Boolean(result.found)); $("modalFfmpegFound").title = result.directory || ""; $("ffmpegDir").textContent = result.directory || ""; return result; }
  function ffmpegSaveError(result) { if (result.code) return errText(result.code, result.detail || result.error); if (result.found === false) return t("ffmpeg_missing"); return compactDetail(result.error) || t("failed"); }
  function openSettings() {
    $("settingsModal").classList.remove("hidden");
    refreshFfmpeg();
    $("showRareLangs").checked = Boolean(state.config.showRareLangs);
  }
  function closeSettings() { $("settingsModal").classList.add("hidden"); }

  async function init() {
    const realApi = await waitForBackend();
    api = realApi || mockApi();
    window.MAWLauncher.backend = realApi ? "real" : "mock";
    const savedTheme = localStorage.getItem(THEME_KEY);
    state.theme = savedTheme === "light" || savedTheme === "dark" || savedTheme === "system" ? savedTheme : "system";
    applyTheme();
    $("lengthLimitField").classList.toggle("hidden", !SHOW_LENGTH_LIMIT_FIELD);
    $("demoBadge").classList.toggle("hidden", window.MAWLauncher.backend !== "mock");
    state.config = await bridge("get_config");
    state.config.zoomPercent = applyZoomPercent(state.config.zoomPercent);
    window.MAWLauncher.config = state.config;
    const emojiFont = await bridge("get_emoji_font_path");
    if (emojiFont && emojiFont.ok && emojiFont.path) injectEmojiFont(emojiFont.path);
    state.lang = state.config.guiLang || "zh";
    fillSelect("provider", state.config.providers, state.config.providerId || "qwen");
    applyProvider(false);
    $("workspaceId").value = state.config.workspaceId || "";
    syncWorkspace(); syncTestRun(); renderChevron("advancedCard"); renderLanguage(); refreshFfmpeg();
    appendLog(window.MAWLauncher.backend === "real" ? "MAW launcher ready." : "[mock] Static browser demo mode enabled."); setStatus(t("ready")); window.dispatchEvent(new CustomEvent("mawlauncherready"));
  }

  function handleBackendEvent(event) {
    if (["batchStarted", "batchItem", "batchItemLog", "batchDone", "batch_started", "batch_item", "batch_item_log", "batch_done"].includes(event.type)) window.MAWLauncher?.onBatchEvent?.(event);
    if (event.type === "emojiFontReady" && event.path) injectEmojiFont(event.path);
    if (event.type === "log") appendLog(event.message);
    if (event.type === "error") {
      setRunning(false);
      const detail = event.detail || event.message || "";
      const message = event.code ? errText(event.code, detail) : detail || t("failed");
      setStatus(message);
      appendLog(`[error] ${message}`);
      if (detail && detail !== message) appendLog(`[detail] ${detail}`);
    }
    if (event.type === "done") {
      state.result = event.result;
      setRunning(false);
      if (event.result?.srtPath) $("srtPath").value = event.result.srtPath;
      $("openFolder").classList.remove("hidden");
      appendLog(t("done"));
    }
    if (event.type === "dropMedia" && window.MAWLauncher?.onBatchDrop?.(event.path || "")) return;
    if (event.type === "dropReject" && window.MAWLauncher?.onBatchDropReject?.(event.path || "")) return;
    if (event.type === "dropMedia" || event.type === "dropHotwordFile" || event.type === "dropReject") handleRoutedDrop(event.path || "");
  }
  window.MAWLauncher = { backend: "pending", config: null, callBackend: bridge, translate: t, viewportPixelsToPage, openSettings, closeSettings, getTranscriptionPayload: formPayload, appendLog, confirm: confirmAction, confirmResolve: null, onBackendEvent: handleBackendEvent, onBackendEvents(events) { events.forEach(handleBackendEvent); }, onLanguageChanged() {} };

  $("langToggle").addEventListener("click", async () => { state.lang = state.lang === "zh" ? "en" : "zh"; renderLanguage(); const result = await bridge("save_settings", formPayload()); if (!result.ok) applyErrorResult(result); });
  $("themeLight").addEventListener("click", () => setTheme("light")); $("themeDark").addEventListener("click", () => setTheme("dark")); $("themeSystem").addEventListener("click", () => setTheme("system"));
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (state.theme === "system") applyTheme(); });
  $("homeLink").addEventListener("click", () => bridge("open_url", { url: HOME_URL }));
  $("provider").addEventListener("change", () => applyProvider(true)); $("model").addEventListener("change", () => applySelectedModel(true)); $("language").addEventListener("change", () => savePrefsDebounced({ language: languageValue() })); $("region").addEventListener("change", syncWorkspace); $("advancedToggle").addEventListener("click", () => toggle("advancedCard"));
  $("testRun").addEventListener("change", syncTestRun);
  $("mediaPath").addEventListener("input", () => { setError("mediaPath", ""); setOutputNotice(""); syncFlvHints(); syncDefaultOutput(); }); $("srtPath").addEventListener("input", () => { state.srtAuto = false; state.testSuffixAdded = false; setError("srtPath", ""); setOutputNotice(""); });
  $("pickMedia").addEventListener("click", async () => { const result = await bridge("choose_file", { kind: "media" }); if (!result.ok) return; if (!MEDIA_EXTS.has(ext(result.path))) { setError("mediaPath", mediaDropError()); return; } setMedia(result.path); });
  $("qwenAudioHotwordsModeText").addEventListener("click", () => { setHotwordsMode("text"); setError("qwenAudioHotwordsFile", ""); }); $("qwenAudioHotwordsModeFile").addEventListener("click", () => { setHotwordsMode("file"); setError("qwenAudioHotwordsFile", ""); }); $("pickQwenAudioHotwordsFile").addEventListener("click", async () => { const result = await bridge("choose_file", { kind: "hotwords" }); if (result.ok) await loadHotwordFile(result.path || "", false); });
  ["apiKey", "workspaceId", "qwenAudioContext", "qwenAudioHotwords", "qwenAudioHotwordsFile", "qwenAudioHotwordWeight", "ffmpegPath"].forEach((field) => { const el = $(field); el?.addEventListener("input", () => { setError(field, ""); if (field === "qwenAudioContext") renderPromptCharacterCount(); if (field === "qwenAudioHotwords") renderHotwordWarnings(); if (field === "qwenAudioHotwordWeight") renderHotwordWarnings(); }); el?.addEventListener("change", () => { setError(field, ""); if (field === "qwenAudioHotwordWeight") renderHotwordWarnings(); }); });
  $("openKeyUrl").addEventListener("click", () => bridge("open_url", { url: provider().keyUrl }));
  $("ffmpegHelp").addEventListener("click", () => bridge("open_url", { url: "https://ffmpeg.org/download.html" }));
  $("settingsButton").addEventListener("click", openSettings); $("settingsClose").addEventListener("click", closeSettings); $("settingsBackdrop").addEventListener("click", closeSettings); document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeSettings(); });
  $("batchConfirmYes").addEventListener("click", () => finishConfirm(true)); $("batchConfirmNo").addEventListener("click", () => finishConfirm(false));
  $("changeFfmpeg").addEventListener("click", () => $("ffmpegPathBox").classList.remove("hidden"));
  $("saveFfmpeg").addEventListener("click", async () => { const result = await bridge("save_ffmpeg_path", { path: $("ffmpegPath").value.trim() }); if (!result.ok) { const message = ffmpegSaveError(result); setError("ffmpegPath", message); setStatus(message); return; } setError("ffmpegPath", ""); await refreshFfmpeg(); setStatus(t("saved")); });
  $("showRareLangs").addEventListener("change", async () => { state.config.showRareLangs = $("showRareLangs").checked; applyProviderLanguages(provider(), selectedModel()); const result = await bridge("save_prefs", { showRareLangs: state.config.showRareLangs }); if (result.ok) setStatus(t("saved")); else applyErrorResult(result); });
  $("languageReset").addEventListener("click", () => { const el = $("language"); Array.from(el.options).forEach((o) => { o.selected = false; }); savePrefsDebounced({ language: "" }); });
  $("saveSettings").addEventListener("click", async () => { const result = await bridge("save_settings", formPayload()); if (result.ok) { const current = provider(); current.apiKey = $("apiKey").value.trim(); current.maskedApiKey = result.maskedApiKey; state.config.apiKey = current.apiKey; state.config.maskedApiKey = result.maskedApiKey; renderKeyStatus(); setStatus(t("saved")); } else applyErrorResult(result); });
  $("start").addEventListener("click", async () => { if (!validateForm()) return; $("log").textContent = ""; state.lastLogMessage = ""; const latest = $("logLatest"); latest.textContent = ""; latest.classList.add("hidden"); setRunning(true); $("logTitle").scrollIntoView({ behavior: "smooth", block: "start" }); const result = await bridge("start_transcription", formPayload()); if (!result.ok) { setRunning(false); applyErrorResult(result, false); } else if (result.outputPath) { $("srtPath").value = result.outputPath; if (result.outputRenamed) setOutputNotice(t("output_collision")); } });
  $("stop").addEventListener("click", async () => { if (!state.running) return; $("stop").disabled = true; setStatus(t("batch_stopping")); const result = await bridge("cancel_transcription"); if (!result.ok) { $("stop").disabled = false; setStatus(result.detail || result.error || t("failed")); } });
  $("openFolder").addEventListener("click", () => bridge("open_output_folder"));
  $("mediaCard").addEventListener("dragenter", onDragEnter); $("mediaCard").addEventListener("dragleave", onDragLeave);
  bindDropField("qwenAudioHotwordsTextField", "text", "qwenAudioHotwords"); bindDropField("qwenAudioHotwordsFileField", "file", "qwenAudioHotwordsFile");
  document.addEventListener("dragover", (event) => { if (hasFileDrag(event)) event.preventDefault(); });
  document.addEventListener("dragend", clearDropState);
  document.addEventListener("dragleave", (event) => { if (!event.relatedTarget && event.target === document.documentElement) clearDropState(); });
  // 真实后端模式下 drop 由 Python 侧异步回传事件，不能在这里清理 dropTarget，否则 handleRoutedDrop 读不到目标。
  document.addEventListener("drop", (event) => { event.preventDefault(); if (window.MAWLauncher.backend === "real") return; const files = Array.from(event.dataTransfer?.files || []); let handled = false; if (window.MAWLauncher?.onBatchDrop) files.forEach((file) => { handled = window.MAWLauncher.onBatchDrop(file.path || file.name || "") || handled; }); if (handled) return; const file = files[0]; handleRoutedDrop(file?.path || file?.name || ""); });
  setupScrollbarFlash();
  document.addEventListener("DOMContentLoaded", init);
  document.addEventListener("keydown", handleZoomKeydown);
  document.addEventListener("wheel", handleZoomWheel, { passive: false });
})();
