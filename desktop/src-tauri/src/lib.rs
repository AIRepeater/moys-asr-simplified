// MOSE Tauri 应用入口。
//
// Week 1：仅启动空 webview，加载 ../src/index.html 占位页。
// Week 2 起在此处接入工程加载、token 替换、IPC commands。

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|_app| {
            // Week 2 将在此：
            //   1. 读取 ../web/editor-template.html
            //   2. 做 __DATA_JSON__ 等 token 替换
            //   3. 把替换后的 HTML 注入 webview
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("MOSE 启动失败");
}
