// Tauri 2.x 入口：通过 lib::run() 启动，便于未来支持 mobile entry point。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    mose_lib::run()
}
