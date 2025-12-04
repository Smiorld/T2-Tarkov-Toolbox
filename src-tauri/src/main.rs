// 禁止在 Windows 上显示控制台窗口
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// 引入 Tauri 相关模块
use tauri::{Manager, Emitter};

// 引入各个命令模块（稍后实现）
mod commands;
mod filter;
// mod utils;
// mod models;

use commands::filter::FilterManagerState;
use filter::FilterManager;
use std::sync::Mutex;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};

// 简单的测试命令 - 验证 Tauri 通信正常
#[tauri::command]
fn greet(name: &str) -> String {
    format!("你好, {}! 欢迎使用 T2 塔科夫工具箱！", name)
}

// 获取配置目录路径
fn get_config_dir(_app_handle: &tauri::AppHandle) -> std::path::PathBuf {
    // 获取可执行文件路径
    let exe_path = std::env::current_exe().expect("无法获取可执行文件路径");
    let exe_dir = exe_path.parent().expect("无法获取可执行文件目录");
    exe_dir.join("config")
}

// 主函数入口
fn main() {
    // 构建 Tauri 应用
    tauri::Builder::default()
        // 注册所有的命令处理函数
        .invoke_handler(tauri::generate_handler![
            greet,
            // 滤镜相关命令
            commands::filter::get_all_filter_presets,
            commands::filter::get_monitors,
            commands::filter::get_filter_preset,
            commands::filter::create_filter_preset,
            commands::filter::update_filter_preset,
            commands::filter::delete_filter_preset,
            commands::filter::rename_filter_preset,
            commands::filter::apply_filter_preset,
            commands::filter::apply_filter_config,
            commands::filter::get_active_filter_preset,
            commands::filter::reset_filter,
            commands::filter::export_filter_presets,
            commands::filter::import_filter_presets,
            commands::filter::reset_filter_presets_to_defaults,
            commands::filter::refresh_hotkey_registrations,
        ])
        .plugin(
            tauri_plugin_global_shortcut::Builder::new().with_handler(move |app, shortcut, event| {
                use std::str::FromStr;

                if event.state == ShortcutState::Pressed {
                    println!("\n========== 快捷键触发 ==========");
                    println!("触发的快捷键 Debug格式: {:?}", shortcut);

                    let state = app.state::<FilterManagerState>();
                    let manager_lock = state.0.lock().unwrap();
                    if let Some(manager) = manager_lock.as_ref() {
                        // 获取所有预设，查找匹配的快捷键
                        let presets = manager.get_all_presets();
                        println!("当前预设数量: {}", presets.len());

                        // 查找匹配快捷键的预设
                        let matched_preset = presets.iter().find(|p| {
                            if let Some(ref hotkey) = p.hotkey {
                                println!("检查预设 '{}' 的快捷键: '{}'", p.name, hotkey);
                                // 解析配置文件中的快捷键字符串
                                match tauri_plugin_global_shortcut::Shortcut::from_str(hotkey) {
                                    Ok(preset_shortcut) => {
                                        // 比较两个 Shortcut 对象（使用字符串表示比较）
                                        let a = format!("{:?}", shortcut);
                                        let b = format!("{:?}", preset_shortcut);
                                        println!("  触发快捷键: {}", a);
                                        println!("  预设快捷键: {}", b);
                                        println!("  比较结果: {}", a == b);
                                        if a == b {
                                            println!("✓ 快捷键匹配成功!");
                                            return true;
                                        }
                                    }
                                    Err(e) => {
                                        println!("  解析快捷键失败: {}", e);
                                    }
                                }
                            } else {
                                println!("预设 '{}' 没有快捷键", p.name);
                            }
                            false
                        });

                        if let Some(preset) = matched_preset {
                            println!("触发快捷键，应用预设: {}", preset.name);

                            // 获取所有显示器
                            let all_monitors = match crate::filter::enumerate_monitors() {
                                Ok(monitors) => monitors.iter().map(|m| m.device_name.clone()).collect(),
                                Err(_) => {
                                    eprintln!("无法枚举显示器");
                                    vec![]
                                }
                            };

                            if all_monitors.is_empty() {
                                eprintln!("没有找到显示器");
                                return;
                            }

                            // 应用预设
                            match manager.apply_preset(&preset.id, all_monitors) {
                                Ok(_) => {
                                    println!("成功应用预设: {}", preset.name);
                                    // 通知前端更新UI
                                    let _ = app.emit("preset-applied", &preset.id);
                                }
                                Err(e) => {
                                    eprintln!("应用预设失败: {}", e);
                                }
                            }
                        } else {
                            println!("未找到匹配的预设快捷键: {:?}", shortcut);
                        }
                    }
                }
            })
            .build(),
        )
        // 应用启动时的初始化逻辑
        .setup(|app| {
            // 打印调试信息
            println!("T2 塔科夫工具箱启动成功！");

            // 获取应用句柄
            let app_handle = app.handle();

            // 初始化滤镜管理器
            let config_dir = get_config_dir(&app_handle);
            match FilterManager::new(config_dir) {
                Ok(manager) => {
                    // 从管理器获取所有预设并注册快捷键
                    let presets = manager.get_all_presets();
                    for preset in presets {
                        if let Some(ref hotkey) = preset.hotkey {
                            use std::str::FromStr;
                            if let Ok(shortcut) = tauri_plugin_global_shortcut::Shortcut::from_str(hotkey) {
                                let _ = app_handle.global_shortcut().register(shortcut);
                                println!("已注册快捷键: {} -> {}", hotkey, preset.name);
                            }
                        }
                    }

                    app.manage(FilterManagerState(Mutex::new(Some(manager))));
                    println!("滤镜管理器初始化成功");
                }
                Err(e) => {
                    eprintln!("滤镜管理器初始化失败: {}", e);
                    app.manage(FilterManagerState(Mutex::new(None)));
                }
            }

            // TODO: 初始化数据库
            // TODO: 加载用户设置
            // TODO: 启动截图监控（如果已配置）

            Ok(())
        })
        // 运行应用
        .run(tauri::generate_context!())
        .expect("启动 Tauri 应用时出错");
}
