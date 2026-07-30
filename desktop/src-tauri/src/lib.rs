// MOSE Tauri 应用入口。
//
// Week 1：启动时从 web/editor-template.html 渲染 index.html（等价 edit.py --blank）。
// Week 2 起将在此处接入 IPC commands（工程加载、保存、波形等）。

use std::fs;
use std::path::PathBuf;

/// web/ 目录（MAW 仓库根的 web/），基于 Cargo.toml 编译时位置推算。
fn web_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent() // desktop/
        .unwrap()
        .parent() // moys-asr-workflow/
        .unwrap()
        .join("web")
}

/// 读取 web/ 下某个源文件，找不到则 panic（开发期早暴露）。
fn read_web_asset(name: &str) -> String {
    let path = web_dir().join(name);
    fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("无法读取 {}: {}", path.display(), e))
}

/// 渲染 MAWE 编辑器页面（空工程），与 edit.py:build_blank_html 等价。
fn render_editor_page() -> String {
    let mut page = read_web_asset("editor-template.html");

    let blank_data = r#"{"segments":[],"media":"","language":"","model":""}"#;
    let blank_media_html = r#"<audio id="player" controls preload="metadata" style="width:100%;display:block;"></audio>"#;

    // 先读取所有 web 资源到已绑定的 String，让 trim_end 的 &str 有合法生命周期
    let editor_css = read_web_asset("editor.css");
    let waveform_css = read_web_asset("waveform.css");
    let editor_utils_js = read_web_asset("editor-utils.js");
    let editor_i18n_js = read_web_asset("editor-i18n.js");
    let waveform_js = read_web_asset("waveform.js");
    let editor_js = read_web_asset("editor.js");

    // CSS / JS inline（trim_end 与 edit.py:render_editor_page 的 rstrip 行为一致）
    let replacements: Vec<(&str, &str)> = vec![
        ("__EDITOR_CSS__", editor_css.trim_end()),
        ("__WAVEFORM_CSS__", waveform_css.trim_end()),
        ("__EDITOR_UTILS_JS__", editor_utils_js.trim_end()),
        ("__EDITOR_I18N_JS__", editor_i18n_js.trim_end()),
        ("__WAVEFORM_JS__", waveform_js.trim_end()),
        ("__EDITOR_JS__", editor_js.trim_end()),
        // JSON 数据（空工程）
        ("__DATA_JSON__", blank_data),
        ("__SERVER_CONFIG_JSON__", "null"),
        ("__FILENAME_BASE_JSON__", r#""untitled""#),
        ("__STICKERS_JSON__", "[]"),
        ("__STICKER_ROOT_JSON__", r#""""#),
        ("__STICKER_URL_PREFIX_JSON__", r#""""#),
        ("__UI_LANGUAGE_JSON__", "null"),
        // 文本占位
        ("__TITLE__", "MOSE — Moy's Open Subtitle Editor"),
        ("__MEDIA_HTML__", blank_media_html),
        ("__GENERATED_AT__", ""),
        ("__JSON_DISPLAY__", "未加载工程"),
        ("__JSON_NAME_CLASS__", "empty"),
        ("__MEDIA_NAME_DISPLAY__", "未加载媒体"),
        ("__MEDIA_NAME_TITLE__", ""),
        ("__MEDIA_NAME_CLASS__", "empty"),
    ];

    for (token, value) in &replacements {
        page = page.replace(token, value);
    }
    page
}

/// 把渲染结果写到 desktop/src/index.html，供 Tauri webview 加载。
fn write_rendered_index() {
    let html = render_editor_page();
    let out_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent() // desktop/
        .unwrap()
        .join("src");
    fs::create_dir_all(&out_dir).ok();
    let out_path = out_dir.join("index.html");
    fs::write(&out_path, html.as_bytes())
        .unwrap_or_else(|e| panic!("写入 {} 失败: {}", out_path.display(), e));
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // 每次启动时从 web/ 重新渲染 index.html（开发期热更新）
    write_rendered_index();

    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("MOSE 启动失败");
}
