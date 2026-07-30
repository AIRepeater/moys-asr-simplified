# MOSE — Tauri 桌面应用开发目录

本目录是 **MOSE（Moy's Open Subtitle Editor）** 的 Tauri 桌面应用开发目录，属于 MAW 仓库的一部分。

## 架构定位

```
moys-asr-workflow/           (MAW，本仓库)
├── web/                     ← 编辑器源码（真源，被 desktop/ 引用）
├── desktop/                 ← 本目录，Tauri 项目
│   └── src-tauri/           ← Rust 后端 + Tauri 配置（待生成）
├── server-editor/serve.py   ← localhost 编辑器（保留，作为 MAW fallback）
└── edit.py                  ← 便携 HTML 生成器（待废弃）

moys-open-subtitle-editor/   (MOSE 发布仓库，独立)
└── 仅放 release 快照 + issue 跟踪
```

## 开发流程

```powershell
# 前提：Rust 工具链已装（https://rustup.rs/），且当前终端的 PATH 里有 cargo
cargo --version   # 能出版本号 = OK

# 进入 desktop/ 开发
cd D:\Codes\moys-asr-workflow\desktop
npm install       # 首次：安装 @tauri-apps/cli（package.json 里已声明）
npx tauri dev     # 启动开发模式（编译 Rust + 从 web/ 渲染 index.html + 开 webview 窗口）
npx tauri build   # 出 MSI/NSIS 安装包（Week 8 用）
```

启动后：
- Rust 侧自动从 `../web/` 渲染 `desktop/src/index.html`（等价 `edit.py --blank`）
- webview 加载该文件，显示完整 MAWE 编辑器界面
- 改 `web/` 源码后需要重启 `npx tauri dev`（暂无 watch 热重载）

### 关于 PATH

如果终端报 `cargo not found`，说明终端是在装 Rust 之前开的。**开一个新的 PowerShell 窗口**即可（不需要重启电脑）。

## 与 web/ 的关系

`desktop/` 的 Tauri 应用启动时读取 `../web/editor-template.html`，在 Rust 侧做 `__DATA_JSON__` 等 token 替换（与 `edit.py:render_editor_page` 等价），然后注入 webview。

**web/ 永远是编辑器真源。desktop/ 不复制 web/，只引用。**

## 同步到 MOSE 发布仓库

每次 MOSE release 时，将 `desktop/` + `../web/` 快照同步到 `moys-open-subtitle-editor` 仓库：

```powershell
# 同步脚本（待实现，Week 8）
.\scripts\sync-to-mose-release.ps1
```

## 状态

- [x] 目录占位
- [ ] Tauri 项目骨架（Week 1，等 Rust 工具链）
- [ ] 基础 IPC（Week 2）
- [ ] 波形 ffmpeg sidecar（Week 3）
- [ ] 完整功能（Week 4-6）
- [ ] 文件关联 + MAW 集成（Week 5-7）

License: AGPL-3.0-only（与 MAW 主仓库一致）。
