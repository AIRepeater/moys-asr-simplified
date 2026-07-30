// MOSE server 级能力：Settings 读写 + IPC commands。
// 等价于 MAW server-editor/serve.py 的 host 能力，但用 Tauri IPC 替代 HTTP。

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use serde::{Deserialize, Serialize};

pub const MAX_RECENT_PROJECTS: usize = 10;

// === Settings 数据结构（与 serve.py:ServerSettings 对齐） ===

#[derive(Serialize, Deserialize, Clone, Default)]
pub struct RecentProject {
    pub path: String,
    pub name: String,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct ServerSettings {
    #[serde(default = "default_true")]
    pub auto_open_last_project: bool,
    #[serde(default)]
    pub recent_projects: Vec<RecentProject>,
    #[serde(default)]
    pub saved_workspaces: serde_json::Map<String, serde_json::Value>,
    #[serde(default)]
    pub preset_workspaces: serde_json::Map<String, serde_json::Value>,
    #[serde(default)]
    pub active_workspace_name: String,
}

fn default_true() -> bool {
    true
}

impl Default for ServerSettings {
    fn default() -> Self {
        Self {
            auto_open_last_project: true,
            recent_projects: Vec::new(),
            saved_workspaces: serde_json::Map::new(),
            preset_workspaces: serde_json::Map::new(),
            active_workspace_name: String::new(),
        }
    }
}

impl ServerSettings {
    pub fn load(path: &Path) -> Self {
        match fs::read_to_string(path) {
            Ok(content) => serde_json::from_str(&content).unwrap_or_default(),
            Err(_) => Self::default(),
        }
    }

    pub fn save(&self, path: &Path) -> Result<(), String> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|e| format!("创建目录失败: {}", e))?;
        }
        let json = serde_json::to_string_pretty(self).map_err(|e| format!("序列化失败: {}", e))?;
        fs::write(path, format!("{}\n", json))
            .map_err(|e| format!("写入失败: {}", e))?;
        Ok(())
    }

    pub fn remember_project(&mut self, path: &str) {
        let path_buf = PathBuf::from(path);
        let name = path_buf
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown")
            .to_string();
        self.recent_projects.retain(|p| p.path != path);
        self.recent_projects.insert(0, RecentProject {
            path: path.to_string(),
            name,
        });
        self.recent_projects.truncate(MAX_RECENT_PROJECTS);
    }

    /// 序列化为可注入前端的 SERVER_CONFIG JSON 对象。
    /// recentProjects 每条带 exists 标记，让前端区分失效路径。
    pub fn to_server_config(&self, can_save: bool) -> serde_json::Value {
        let recent: Vec<serde_json::Value> = self
            .recent_projects
            .iter()
            .map(|p| {
                let exists = PathBuf::from(&p.path).exists();
                serde_json::json!({
                    "path": p.path,
                    "name": p.name,
                    "exists": exists,
                })
            })
            .collect();

        serde_json::json!({
            "saveUrl": "mose://save-project",
            "canSave": can_save,
            "recentProjectsUrl": "mose://recent-projects",
            "settingsUrl": "mose://settings",
            "recentProjects": recent,
            "autoOpenLastProject": self.auto_open_last_project,
            "savedWorkspaces": self.saved_workspaces,
            "presetWorkspaces": self.preset_workspaces,
            "activeWorkspaceName": self.active_workspace_name,
        })
    }
}

// === App State ===

pub struct AppState {
    pub current_project_path: Mutex<Option<PathBuf>>,
    pub settings: Mutex<ServerSettings>,
    pub settings_path: PathBuf,
}

impl AppState {
    pub fn can_save(&self) -> bool {
        self.current_project_path.lock().unwrap().is_some()
    }
}

// === settings.json 路径 ===

pub fn settings_path() -> PathBuf {
    let base = if cfg!(target_os = "windows") {
        let local = std::env::var("LOCALAPPDATA").unwrap_or_else(|_| {
            let home = std::env::var("USERPROFILE").unwrap_or_else(|_| ".".into());
            format!("{}\\AppData\\Local", home)
        });
        PathBuf::from(local)
    } else {
        let data_dir = std::env::var("XDG_DATA_HOME").unwrap_or_else(|_| {
            let home = std::env::var("HOME").unwrap_or_else(|_| ".".into());
            format!("{}/.local/share", home)
        });
        PathBuf::from(data_dir)
    };
    base.join("Moy").join("mose").join("settings.json")
}

// === IPC Commands ===

#[tauri::command]
pub async fn open_project(
    state: tauri::State<'_, AppState>,
    app: tauri::AppHandle,
) -> Result<serde_json::Value, String> {
    use tauri_plugin_dialog::DialogExt;

    let picked = app
        .dialog()
        .file()
        .add_filter("字幕工程 (*.mosp, *.json)", &["mosp", "json"])
        .blocking_pick_file();

    let Some(file_path) = picked else {
        return Ok(serde_json::json!({ "ok": false, "cancelled": true }));
    };

    let path = file_path
        .as_path()
        .ok_or_else(|| "无效的文件路径".to_string())?
        .to_path_buf();

    let content = fs::read_to_string(&path)
        .map_err(|e| format!("读取失败: {}", e))?;
    let data: serde_json::Value = serde_json::from_str(&content)
        .map_err(|e| format!("JSON 解析失败: {}", e))?;

    // 设置当前工程路径（后续 save_project 用）
    *state.current_project_path.lock().unwrap() = Some(path.clone());

    // 记录最近工程
    {
        let mut settings = state.settings.lock().unwrap();
        settings.remember_project(&path.to_string_lossy());
        let _ = settings.save(&state.settings_path);
    }

    let filename = path
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("untitled")
        .to_string();

    Ok(serde_json::json!({
        "ok": true,
        "data": data,
        "path": path.to_string_lossy(),
        "filename": filename,
    }))
}

#[tauri::command]
pub fn save_project(
    state: tauri::State<AppState>,
    project: serde_json::Value,
    _filename: Option<String>,
) -> Result<serde_json::Value, String> {
    let path = {
        let guard = state.current_project_path.lock().unwrap();
        guard
            .clone()
            .ok_or_else(|| "没有绑定工程文件路径，请先另存为".to_string())?
    };

    // .bak 备份
    let mut backup_name = None;
    if path.exists() {
        let bak_path = path.with_extension("json.bak");
        if fs::copy(&path, &bak_path).is_ok() {
            backup_name = bak_path
                .file_name()
                .and_then(|s| s.to_str())
                .map(String::from);
        }
    }

    // 写工程文件（保持 LF，与 edit.py 一致）
    let json = serde_json::to_string_pretty(&project)
        .map_err(|e| format!("序列化失败: {}", e))?;
    fs::write(&path, format!("{}\n", json))
        .map_err(|e| format!("写入失败: {}", e))?;

    let filename = path
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("untitled")
        .to_string();

    Ok(serde_json::json!({
        "ok": true,
        "filename": filename,
        "backup": backup_name,
    }))
}

#[tauri::command]
pub fn remember_project(
    state: tauri::State<AppState>,
    path: String,
) -> Result<serde_json::Value, String> {
    {
        let mut settings = state.settings.lock().unwrap();
        settings.remember_project(&path);
        settings.save(&state.settings_path)?;
    }
    Ok(serde_json::json!({ "ok": true }))
}

#[tauri::command]
pub fn update_settings(
    state: tauri::State<AppState>,
    payload: serde_json::Value,
) -> Result<serde_json::Value, String> {
    {
        let mut settings = state.settings.lock().unwrap();

        if let Some(auto_open) = payload.get("autoOpenLastProject").and_then(|v| v.as_bool()) {
            settings.auto_open_last_project = auto_open;
        }

        if let Some(save_ws) = payload.get("saveWorkspace") {
            if let Some(name) = save_ws.get("name").and_then(|v| v.as_str()) {
                let workspace = save_ws
                    .get("workspace")
                    .cloned()
                    .unwrap_or(serde_json::Value::Null);
                let overwrite = save_ws
                    .get("overwrite")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false);
                if settings.saved_workspaces.contains_key(name) && !overwrite {
                    return Err(format!("工作区 '{}' 已存在", name));
                }
                settings.saved_workspaces.insert(name.to_string(), workspace);
                settings.active_workspace_name = name.to_string();
            }
        }

        if let Some(save_preset) = payload.get("savePresetWorkspace") {
            if let Some(preset) = save_preset.get("preset").and_then(|v| v.as_str()) {
                let workspace = save_preset
                    .get("workspace")
                    .cloned()
                    .unwrap_or(serde_json::Value::Null);
                settings.preset_workspaces.insert(preset.to_string(), workspace);
            }
        }

        if let Some(delete_ws) = payload.get("deleteWorkspace") {
            if let Some(name) = delete_ws.get("name").and_then(|v| v.as_str()) {
                settings.saved_workspaces.remove(name);
                if settings.active_workspace_name == name {
                    settings.active_workspace_name.clear();
                }
            }
        }

        if let Some(active) = payload.get("activeWorkspaceName").and_then(|v| v.as_str()) {
            settings.active_workspace_name = active.to_string();
        }

        settings.save(&state.settings_path)?;
    }

    let settings = state.settings.lock().unwrap();
    Ok(serde_json::json!({
        "ok": true,
        "savedWorkspaces": settings.saved_workspaces,
        "presetWorkspaces": settings.preset_workspaces,
        "activeWorkspaceName": settings.active_workspace_name,
        "autoOpenLastProject": settings.auto_open_last_project,
    }))
}

/// 打开指定路径的工程（用于"最近工程"切换，不弹 dialog）。
#[tauri::command]
pub fn open_project_at_path(
    state: tauri::State<AppState>,
    path: String,
) -> Result<serde_json::Value, String> {
    let path_buf = PathBuf::from(&path);

    if !path_buf.exists() {
        // 从最近工程列表移除失效路径
        {
            let mut settings = state.settings.lock().unwrap();
            settings.recent_projects.retain(|p| p.path != path);
            let _ = settings.save(&state.settings_path);
        }
        return Ok(serde_json::json!({
            "ok": false,
            "error": format!("文件不存在：{}", path),
        }));
    }

    let content = fs::read_to_string(&path_buf)
        .map_err(|e| format!("读取失败: {}", e))?;
    let data: serde_json::Value = serde_json::from_str(&content)
        .map_err(|e| format!("JSON 解析失败: {}", e))?;

    *state.current_project_path.lock().unwrap() = Some(path_buf.clone());

    {
        let mut settings = state.settings.lock().unwrap();
        settings.remember_project(&path);
        let _ = settings.save(&state.settings_path);
    }

    let filename = path_buf
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("untitled")
        .to_string();

    Ok(serde_json::json!({
        "ok": true,
        "data": data,
        "path": path,
        "filename": filename,
    }))
}

/// 解析媒体文件路径为 webview 可访问的 URL（当前用 file:// 协议）。
#[tauri::command]
pub fn resolve_media(path: String) -> Result<serde_json::Value, String> {
    let path_buf = PathBuf::from(&path);
    if !path_buf.exists() {
        return Ok(serde_json::json!({
            "ok": false,
            "error": format!("媒体文件不存在：{}", path),
        }));
    }
    // Windows: file:///D:/path/to/file → 正斜杠
    let posix = path.replace('\\', "/");
    let trimmed = posix.trim_start_matches('/');
    let url = format!("file:///{}", trimmed);

    Ok(serde_json::json!({
        "ok": true,
        "url": url,
        "name": path_buf.file_name().and_then(|s| s.to_str()).unwrap_or("media"),
    }))
}

// === 表情包扫描 ===

const STICKER_IMAGE_EXTS: &[&str] = &["png", "jpg", "jpeg", "gif", "webp", "bmp"];

fn scan_sticker_dir(
    root: &Path,
    current: &Path,
    max_depth: usize,
    current_depth: usize,
    max_items: usize,
    items: &mut Vec<serde_json::Value>,
) {
    if current_depth > max_depth || items.len() >= max_items {
        return;
    }
    let entries = match fs::read_dir(current) {
        Ok(e) => e,
        Err(_) => return,
    };
    let mut files: Vec<_> = entries.filter_map(|e| e.ok()).collect();
    files.sort_by_key(|e| e.path());
    for entry in files {
        if items.len() >= max_items {
            break;
        }
        let path = entry.path();
        if path.is_dir() {
            scan_sticker_dir(root, &path, max_depth, current_depth + 1, max_items, items);
        } else if path.is_file() {
            let ext = path
                .extension()
                .and_then(|e| e.to_str())
                .map(|e| e.to_lowercase())
                .unwrap_or_default();
            if !STICKER_IMAGE_EXTS.contains(&ext.as_str()) {
                continue;
            }
            let rel = path.strip_prefix(root).unwrap_or(&path);
            let rel_posix = rel.to_string_lossy().replace('\\', "/");
            let name = rel
                .with_extension("")
                .to_string_lossy()
                .replace('\\', "/");
            let filename = path
                .file_name()
                .and_then(|s| s.to_str())
                .unwrap_or("")
                .to_string();
            items.push(serde_json::json!({
                "name": name,
                "filename": filename,
                "rel": rel_posix,
            }));
        }
    }
}

/// 弹出目录选择器 + 扫描表情包，返回 { root, stickers, count }。
#[tauri::command]
pub async fn pick_and_scan_stickers(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    use tauri_plugin_dialog::DialogExt;

    let picked = app.dialog().file().blocking_pick_folder();
    let Some(dir) = picked else {
        return Ok(serde_json::json!({ "ok": false, "cancelled": true }));
    };

    let root_path = dir
        .as_path()
        .ok_or_else(|| "无效目录路径".to_string())?
        .to_path_buf();
    let root_abs = root_path.canonicalize().unwrap_or(root_path);

    let mut items = Vec::new();
    scan_sticker_dir(&root_abs, &root_abs, 3, 0, 500, &mut items);

    let root_posix = root_abs.to_string_lossy().replace('\\', "/");

    Ok(serde_json::json!({
        "ok": true,
        "root": root_posix,
        "stickers": items,
        "count": items.len(),
    }))
}

// === 波形提取（移植自 waveform.py） ===

/// 从媒体提取波形峰值（等价 waveform.py:extract_waveform）。
/// 调 ffmpeg sidecar 输出 mono PCM s16le → 流式读 → 分桶 min/max → 量化 int8 → base64。
#[tauri::command]
pub async fn extract_waveform(
    app: tauri::AppHandle,
    media_path: String,
    peaks_per_second: Option<u32>,
) -> Result<serde_json::Value, String> {
    use tauri_plugin_shell::ShellExt;
    use tauri_plugin_shell::process::CommandEvent;

    let pps = peaks_per_second.unwrap_or(100);
    let pcm_sample_rate = pps * 10;

    let path = PathBuf::from(&media_path);
    if !path.exists() {
        return Err(format!("媒体文件不存在: {}", media_path));
    }

    // 文件签名（用于缓存失效检查，与 waveform.py:media_signature 对齐）
    let stat = fs::metadata(&path).map_err(|e| format!("读取文件信息失败: {}", e))?;
    let source = serde_json::json!({
        "name": path.file_name().and_then(|s| s.to_str()).unwrap_or(""),
        "size": stat.len(),
        "modified_ms": stat.modified()
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_millis() as u64)
            .unwrap_or(0),
    });

    // 调 ffmpeg sidecar
    let sidecar = app
        .shell()
        .sidecar("ffmpeg")
        .map_err(|e| format!("无法找到 ffmpeg sidecar: {}", e))?;

    let (mut rx, _child) = sidecar
        .args([
            "-nostdin", "-hide_banner", "-loglevel", "error",
            "-i", &media_path,
            "-map", "0:a:0", "-vn", "-ac", "1",
            "-ar", &pcm_sample_rate.to_string(),
            "-f", "s16le", "pipe:1",
        ])
        .spawn()
        .map_err(|e| format!("ffmpeg 启动失败: {}", e))?;

    // 流式收集 PCM s16le 字节
    let mut pcm_data = Vec::new();
    let mut stderr_output = String::new();
    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(bytes) => {
                pcm_data.extend_from_slice(bytes.as_slice());
            }
            CommandEvent::Stderr(bytes) => {
                if let Ok(s) = std::str::from_utf8(bytes.as_slice()) {
                    stderr_output.push_str(s);
                }
            }
            CommandEvent::Terminated(_) => break,
            _ => {}
        }
    }

    if pcm_data.is_empty() {
        return Err(if stderr_output.trim().is_empty() {
            "ffmpeg 没有输出音频数据".to_string()
        } else {
            format!("ffmpeg 错误: {}", stderr_output.trim())
        });
    }

    // PCM s16le → i16 样本
    let samples: Vec<i16> = pcm_data
        .chunks_exact(2)
        .map(|chunk| i16::from_le_bytes([chunk[0], chunk[1]]))
        .collect();

    // 分桶 min/max → 量化 int8（与 waveform.py:_append_bucket 一致）
    let bucket = (pcm_sample_rate / pps) as usize;
    let bucket = bucket.max(1);
    let mut peaks_bytes = Vec::new();

    for chunk in samples.chunks(bucket) {
        let min_val = chunk.iter().min().copied().unwrap_or(0);
        let max_val = chunk.iter().max().copied().unwrap_or(0);
        let min_q = (min_val as f32 * 127.0 / 32768.0).round().clamp(-127.0, 127.0) as i8;
        let max_q = (max_val as f32 * 127.0 / 32768.0).round().clamp(-127.0, 127.0) as i8;
        peaks_bytes.push(min_q as u8);
        peaks_bytes.push(max_q as u8);
    }

    let peak_count = peaks_bytes.len() / 2;
    let actual_pps = if !samples.is_empty() && bucket > 0 {
        pcm_sample_rate / bucket as u32
    } else {
        pps
    };
    let duration_ms = if !samples.is_empty() {
        (samples.len() as u64 * 1000) / pcm_sample_rate as u64
    } else {
        0
    };

    // base64 编码
    use base64::Engine;
    let data = base64::engine::general_purpose::STANDARD.encode(&peaks_bytes);

    Ok(serde_json::json!({
        "schema": "moy.asr.waveform.v1",
        "encoding": "i8-minmax-base64",
        "peaks_per_second": actual_pps,
        "peak_count": peak_count,
        "duration_ms": duration_ms,
        "data": data,
        "source": source,
    }))
}
