// MOSE Tauri 应用入口。
//
// Week 2：server 级能力（IPC commands + Settings + tauri bridge）。
// - 启动时加载 settings → 渲染 index.html（注入 SERVER_CONFIG + bridge 脚本）
// - 注册 4 个 IPC commands：open_project / save_project / remember_project / update_settings
// - tauri_bridge.js 把 web/editor.js 的 fetch 透明路由到 invoke

mod server;

use std::fs;
use std::path::PathBuf;
use std::sync::Mutex;

use server::{
    extract_waveform, open_project, open_project_at_path, pick_and_scan_stickers,
    remember_project, resolve_media, save_project, settings_path, update_settings,
    AppState, ServerSettings,
};

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

/// 渲染 MAWE 编辑器页面：注入 web/ 资源 + settings 到 SERVER_CONFIG + tauri bridge。
fn render_editor_page(settings: &ServerSettings) -> String {
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

    // SERVER_CONFIG JSON（从 settings 构建；启动时 canSave=false，打开工程后 bridge 会更新）
    let server_config_json = serde_json::to_string(&settings.to_server_config(false))
        .expect("序列化 SERVER_CONFIG 失败");

    let replacements: Vec<(&str, &str)> = vec![
        ("__EDITOR_CSS__", editor_css.trim_end()),
        ("__WAVEFORM_CSS__", waveform_css.trim_end()),
        ("__EDITOR_UTILS_JS__", editor_utils_js.trim_end()),
        ("__EDITOR_I18N_JS__", editor_i18n_js.trim_end()),
        ("__WAVEFORM_JS__", waveform_js.trim_end()),
        ("__EDITOR_JS__", editor_js.trim_end()),
        // JSON 数据
        ("__DATA_JSON__", blank_data),
        ("__SERVER_CONFIG_JSON__", &server_config_json),
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

    // 注入 tauri_bridge.js（在 </body> 前，editor.js 之后执行）
    let bridge = include_str!("tauri_bridge.js");
    page = page.replace("</body>", &format!("<script>\n{}\n</script>\n</body>", bridge));

    page
}

/// 把渲染结果写到 desktop/src/index.html，供 Tauri webview 加载。
fn write_rendered_index(settings: &ServerSettings) {
    let html = render_editor_page(settings);
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
    // 1. 加载 settings
    let s_path = settings_path();
    let settings = ServerSettings::load(&s_path);

    // 2. 渲染 index.html（注入 SERVER_CONFIG + bridge 脚本）
    write_rendered_index(&settings);

    // 3. 启动 Tauri（注册 commands + dialog plugin + 共享状态）
    // 检查命令行参数（双击 .mosp 文件时 OS 传入路径）
    let init_file = std::env::args().nth(1).filter(|p| {
        let ext = std::path::Path::new(p)
            .extension()
            .and_then(|e| e.to_str())
            .map(|e| e.to_lowercase())
            .unwrap_or_default();
        ext == "mosp" || ext == "json"
    });

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .manage(AppState {
            current_project_path: Mutex::new(None),
            settings: Mutex::new(settings),
            settings_path: s_path,
        })
        .invoke_handler(tauri::generate_handler![
            open_project,
            open_project_at_path,
            save_project,
            remember_project,
            update_settings,
            resolve_media,
            pick_and_scan_stickers,
            extract_waveform,
        ])
        .setup(move |app| {
            // 启动时如有命令行传入的文件路径，发给前端加载
            if let Some(path) = &init_file {
                use tauri::Emitter;
                let _ = app.emit("open-file", path.clone());
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("MOSE 启动失败");

    app.run(|_app_handle, _event| {});
}
