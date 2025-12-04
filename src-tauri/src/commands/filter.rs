use crate::filter::{FilterConfig, FilterPreset, FilterManager, MonitorInfo};
use std::sync::Mutex;
use tauri::State;

/// 全局滤镜管理器状态
pub struct FilterManagerState(pub Mutex<Option<FilterManager>>);

/// 获取所有预设
#[tauri::command]
pub fn get_all_filter_presets(
    state: State<FilterManagerState>,
) -> Result<Vec<FilterPreset>, String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    Ok(manager.get_all_presets())
}

/// 获取所有显示器
#[tauri::command]
pub fn get_monitors() -> Result<Vec<MonitorInfo>, String> {
    crate::filter::enumerate_monitors()
}

/// 获取单个预设
#[tauri::command]
pub fn get_filter_preset(
    preset_id: String,
    state: State<FilterManagerState>,
) -> Result<FilterPreset, String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.get_preset(&preset_id)
}

/// 创建新预设
#[tauri::command]
pub fn create_filter_preset(
    name: String,
    config: FilterConfig,
    hotkey: Option<String>,
    state: State<FilterManagerState>,
) -> Result<String, String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.create_preset(name, config, hotkey)
}

/// 更新预设
#[tauri::command]
pub fn update_filter_preset(
    preset_id: String,
    name: Option<String>,
    config: Option<FilterConfig>,
    hotkey: Option<Option<String>>,
    state: State<FilterManagerState>,
) -> Result<(), String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.update_preset(&preset_id, name, config, hotkey)
}

/// 删除预设
#[tauri::command]
pub fn delete_filter_preset(
    preset_id: String,
    state: State<FilterManagerState>,
) -> Result<(), String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.delete_preset(&preset_id)
}

/// 重命名预设
#[tauri::command]
pub fn rename_filter_preset(
    preset_id: String,
    new_name: String,
    state: State<FilterManagerState>,
) -> Result<(), String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.rename_preset(&preset_id, new_name)
}

/// 应用预设
#[tauri::command]
pub fn apply_filter_preset(
    preset_id: String,
    monitor_ids: Vec<String>,
    state: State<FilterManagerState>,
) -> Result<(), String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.apply_preset(&preset_id, monitor_ids)
}

/// 直接应用滤镜配置（用于实时预览，不保存）
#[tauri::command]
pub fn apply_filter_config(
    config: FilterConfig,
    monitor_ids: Vec<String>,
    state: State<FilterManagerState>,
) -> Result<(), String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.apply_config(&config, monitor_ids)
}

/// 获取当前激活的预设
#[tauri::command]
pub fn get_active_filter_preset(
    state: State<FilterManagerState>,
) -> Result<Option<FilterPreset>, String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    Ok(manager.get_active_preset())
}

/// 重置滤镜
#[tauri::command]
pub fn reset_filter(
    state: State<FilterManagerState>,
) -> Result<(), String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.reset_filter()
}

/// 导出预设
#[tauri::command]
pub fn export_filter_presets(
    state: State<FilterManagerState>,
) -> Result<String, String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.export_presets()
}

/// 导入预设
#[tauri::command]
pub fn import_filter_presets(
    json: String,
    state: State<FilterManagerState>,
) -> Result<(), String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.import_presets(&json)
}

/// 重置为默认预设
#[tauri::command]
pub fn reset_filter_presets_to_defaults(
    state: State<FilterManagerState>,
) -> Result<(), String> {
    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    manager.reset_to_defaults()
}

/// 刷新快捷键注册（在修改快捷键后调用）
#[tauri::command]
pub fn refresh_hotkey_registrations(
    app: tauri::AppHandle,
    state: State<FilterManagerState>,
) -> Result<(), String> {
    use std::str::FromStr;
    use tauri_plugin_global_shortcut::GlobalShortcutExt;

    let manager_lock = state.0.lock().unwrap();
    let manager = manager_lock
        .as_ref()
        .ok_or_else(|| "滤镜管理器未初始化".to_string())?;

    // 获取所有预设
    let presets = manager.get_all_presets();

    // 取消注册所有快捷键
    println!("取消注册所有快捷键...");
    if let Err(e) = app.global_shortcut().unregister_all() {
        eprintln!("取消注册快捷键失败: {}", e);
    }

    // 重新注册每个预设的快捷键
    println!("重新注册快捷键...");
    for preset in presets {
        if let Some(ref hotkey) = preset.hotkey {
            match tauri_plugin_global_shortcut::Shortcut::from_str(hotkey) {
                Ok(shortcut) => {
                    match app.global_shortcut().register(shortcut) {
                        Ok(_) => println!("已注册快捷键: {} -> {}", hotkey, preset.name),
                        Err(e) => eprintln!("注册快捷键失败 {} ({}): {}", hotkey, preset.name, e),
                    }
                }
                Err(e) => eprintln!("解析快捷键失败 {} ({}): {}", hotkey, preset.name, e),
            }
        }
    }

    Ok(())
}
