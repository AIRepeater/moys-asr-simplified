# MAW 开发概览

本文件供后续维护者快速定位代码与数据边界。产品范围、约束和发布规则以仓库根目录的 `AGENTS.md` 为准。

## 产品与运行形态

MAW（Moy's ASR Workflow）是一个收窄的本地工作流：本地媒体经云端 ASR 生成 SRT 与 JSON 工程，再在本机浏览器编辑、导出。

- `generate_subtitle_qwen_api.py`：转写命令入口。
- `maw/gui_web.py`、`maw/gui_workflow.py` 与 `web/launcher/`：Launcher 图形界面及其后端桥接。
- `edit.py`：读取工程 JSON，渲染单文件 `.edit.html`；也生成 `blank-editor.html`。
- `server-editor/serve.py`：仅监听 `127.0.0.1` 的编辑器服务器，负责媒体 Range 响应、工程安全保存与本机设置。
- `web/`：唯一前端源码。`editor-template.html` 组合 `editor.css`、`waveform.css`、`editor.js`、`waveform.js` 与 i18n；禁止手改生成后的 `blank-editor.html`。

修改 `web/`、模板或内联资源后，必须执行：

```powershell
uv run python edit.py --blank
```

## 数据边界与持久化

| 数据 | 真源 / 存放位置 | 用途 |
|---|---|---|
| `segments` | 工程 JSON | 字幕真源；时间均为整数毫秒。 |
| `waveform` | 工程 JSON 或可重建 sidecar | 性能缓存，不是字幕真源。 |
| `layout` | 工程 JSON（可选） | 随工程携带的四面板布局。 |
| 自定义服务器布局 | 用户本机 `server-editor-settings.json` | 命名布局库，跨工程复用，不改写工程 JSON。 |
| 编辑器、波形偏好 | 浏览器 `localStorage` | 浏览器与 origin 级别偏好；`file://` 或隐私模式可能不可用。 |

服务器设置文件的位置由 `server-editor/serve.py:default_settings_path()` 决定：Windows 为 `%LOCALAPPDATA%/Moy/moys-asr-workflow/server-editor-settings.json`，其他系统为用户数据目录下的 `Moy/moys-asr-workflow/server-editor-settings.json`。它包含最近工程、自动打开开关、`preset_layouts`、`saved_layouts` 和 `active_layout_name`。

## 布局数据契约

布局 schema 是 `moy.asr.editor.layout.v1`。它只控制四个模块的摆放与分隔比例：

- `player`：媒体播放器
- `panel`：当前字幕编辑区
- `cues`：字幕列表
- `wave`：波形

典型数据如下：

```json
{
  "schema": "moy.asr.editor.layout.v1",
  "preset": "free",
  "selectedPreset": "wave-bottom",
  "waveformMode": "basic",
  "waveformSettings": { "visibleSeconds": 20, "secondsPerRow": 10, "rowHeight": 120, "waveformScale": 1 },
  "editorDisplay": { "cueListShowIndex": true, "cueEditorShowTimeActions": true },
  "splitPercent": 60,
  "columnPercent": 44,
  "rows": [42, 18, 40],
  "freeOrder": ["player", "panel", "cues", "wave"],
  "tree": {
    "type": "split",
    "direction": "row",
    "ratio": 44,
    "children": [
      {
        "type": "split",
        "direction": "column",
        "ratio": 42,
        "children": [
          { "type": "module", "id": "player" },
          {
            "type": "split",
            "direction": "column",
            "ratio": 31,
            "children": [
              { "type": "module", "id": "panel" },
              { "type": "module", "id": "cues" }
            ]
          }
        ]
      },
      { "type": "module", "id": "wave" }
    ]
  }
}
```

字段说明：

- `preset`：`classic`、`wave-right`、`wave-bottom`、`free`。前三者是内置布局；界面中的 `wave-bottom` 显示为“传统字幕编辑器”，内部保留键名以兼容旧工程，应用时会使用自由停靠结构；进入“编辑布局”会转换为 `free`。
- `selectedPreset`：最后在布局下拉框选择的项。它与实际渲染用的 `preset` 分开记录，确保内部用 `free` 渲染的传统字幕编辑器重开后仍会被识别为 `wave-bottom`；服务器自定义布局使用 `saved:<名称>`。
- `waveformMode`：`multi` 或 `basic`，记录波形显示模式；旧布局文件缺失该字段时，不覆盖当前浏览器的显示模式。传统字幕编辑器默认 `basic`（单行）；旧版 `hidden` 值会迁移为 `basic`。
- `waveformSettings`：波形区的数值与显示偏好，包括基础窗口长度、多行每行长度和高度、振幅、侧边、禁用项显示、分组徽章与拖动播放头。缺失字段保持浏览器本机偏好。
- `editorDisplay`：字幕列表和字幕编辑区的显示开关；不携带自动保存、导出、快捷键等与布局无关的全局偏好。
- `splitPercent`：标准堆叠布局的波形/字幕区比例，归一化到 35–75。
- `columnPercent`：旧版自由布局左右比例兼容字段，归一化到 30–75。
- `rows`：旧版自由布局三行比例兼容字段；读取时会规范化。
- `tree`：当前真源。二叉树叶子为 `{ "type": "module", "id": ... }`；分支为 `{ "type": "split", "direction": "row" | "column", "ratio": 20..80, "children": [leftOrTop, rightOrBottom] }`。有效树必须恰好包含四个模块各一次。
- `freeOrder`：旧的扁平兼容字段。读取旧数据时会转换成 `tree`；导出时仍保留，勿将它作为新功能的唯一依据。

`web/waveform.js:normalizeLayoutData()` 负责容错、范围限制和旧格式迁移。新增模块或修改树规则时，必须同步更新该函数、布局拖放逻辑、`JSON_SCHEMA.md`、相关 JS 测试和此文档。

### 服务器布局库行为

服务器版的 `preset_layouts` 是三个内置布局的用户覆盖版，`saved_layouts` 是名称到上述布局对象的映射（最多 20 个）；`active_layout_name` 指向当前跨工程复用的自定义布局。打开页面时，服务器先深拷贝工程数据，再以活动自定义布局覆盖页面中的 `layout`，不会写回 JSON。

- 内置布局：可编辑后“保存布局”覆盖本机的该预设，也可另存为；不能删除，但“重置布局”会删除其覆盖版并恢复内置默认值。
- 自定义布局：选择后进入编辑模式可“保存布局”、另存为或删除。
- 选中自定义布局会更新 `active_layout_name`；切换回内置布局会清空活动名称。
- 相关 HTTP 接口为 `POST /api/settings`，字段分别是 `saveLayout`、`deleteLayoutName`、`activeLayoutName`。接口只接受本机浏览器请求。

单文件 HTML 不使用服务器布局库，也不承诺不同 `file://` 页面共享浏览器存储。它显示四个基础布局（包括“自由停靠”），并提供“导出布局 / 导入布局”以 JSON 文件迁移布局。

## 开发检查

```powershell
node --check web\editor.js
node --check web\waveform.js
node --test tests\test_editor_utils.mjs tests\test_waveform_js.mjs
uv run python -m unittest discover -s tests -p "test_*.py"
git diff --check
```

交互改动还应手动启动 `uv run python server-editor\serve.py --blank`，验证拖放、播放、Seek、布局拖动及保存。所有文本保持 UTF-8 与 LF。
