# 屏幕滤镜系统设计

## 🎯 功能需求

### 核心功能
1. **三套预设滤镜**
   - 默认配置（系统原始设置）
   - 白天配置（适合明亮环境）
   - 夜间配置（提高暗部可见度）

2. **调节参数**
   - 亮度 (Brightness)
   - 伽马 (Gamma)
   - 对比度 (Contrast)
   - 色温 (RGB 通道独立调节)

3. **全局快捷键**
   - F2 → 默认配置
   - F3 → 白天配置
   - F4 → 夜间配置
   - 可自定义绑定
   - 防止重复绑定
   - 支持重置为无快捷键

4. **技术要求**
   - 使用 Windows `SetDeviceGammaRamp` API
   - 系统级调整，不违反游戏 TOS
   - 应用退出时自动恢复

---

## 🔧 技术实现

### Windows Gamma Ramp API

#### 原理
Windows 使用 **Gamma Ramp**（颜色查找表 LUT）来控制显示器颜色：
- 每个颜色通道（R/G/B）有 256 个映射值
- 输入值 0-255 → 输出值 0-65535（16位精度）

#### API 调用
```rust
// src-tauri/src/filter/gamma_ramp.rs

use windows::Win32::Graphics::Gdi::{
    GetDC, ReleaseDC, GetDeviceGammaRamp, SetDeviceGammaRamp, HDC
};
use windows::Win32::Foundation::HWND;

/// Gamma Ramp 结构体（Windows 标准格式）
#[repr(C)]
pub struct GammaRamp {
    pub red: [u16; 256],
    pub green: [u16; 256],
    pub blue: [u16; 256],
}

impl GammaRamp {
    /// 创建默认 Gamma Ramp（线性映射）
    pub fn default() -> Self {
        let mut ramp = GammaRamp {
            red: [0; 256],
            green: [0; 256],
            blue: [0; 256],
        };

        for i in 0..256 {
            let value = ((i as f64 / 255.0) * 65535.0) as u16;
            ramp.red[i] = value;
            ramp.green[i] = value;
            ramp.blue[i] = value;
        }

        ramp
    }

    /// 应用亮度调整
    pub fn apply_brightness(&mut self, brightness: f64) {
        // brightness: 0.5 - 2.0 (50% - 200%)
        for i in 0..256 {
            self.red[i] = self.clamp((self.red[i] as f64 * brightness) as u16);
            self.green[i] = self.clamp((self.green[i] as f64 * brightness) as u16);
            self.blue[i] = self.clamp((self.blue[i] as f64 * brightness) as u16);
        }
    }

    /// 应用伽马调整
    pub fn apply_gamma(&mut self, gamma: f64) {
        // gamma: 0.5 - 2.0 (越小越亮)
        for i in 0..256 {
            let normalized = i as f64 / 255.0;
            let corrected = normalized.powf(1.0 / gamma);
            let value = (corrected * 65535.0) as u16;

            self.red[i] = value;
            self.green[i] = value;
            self.blue[i] = value;
        }
    }

    /// 应用对比度调整
    pub fn apply_contrast(&mut self, contrast: f64) {
        // contrast: 0.5 - 2.0 (50% - 200%)
        let factor = (259.0 * (contrast * 255.0 + 255.0)) / (255.0 * (259.0 - contrast * 255.0));

        for i in 0..256 {
            self.red[i] = self.clamp_contrast(self.red[i], factor);
            self.green[i] = self.clamp_contrast(self.green[i], factor);
            self.blue[i] = self.clamp_contrast(self.blue[i], factor);
        }
    }

    /// 应用色温调整（RGB 通道独立）
    pub fn apply_rgb_channels(&mut self, r_scale: f64, g_scale: f64, b_scale: f64) {
        // r_scale, g_scale, b_scale: 0.5 - 2.0
        for i in 0..256 {
            self.red[i] = self.clamp((self.red[i] as f64 * r_scale) as u16);
            self.green[i] = self.clamp((self.green[i] as f64 * g_scale) as u16);
            self.blue[i] = self.clamp((self.blue[i] as f64 * b_scale) as u16);
        }
    }

    fn clamp(&self, value: u16) -> u16 {
        value.min(65535)
    }

    fn clamp_contrast(&self, value: u16, factor: f64) -> u16 {
        let normalized = (value as f64 / 65535.0) * 255.0;
        let adjusted = factor * (normalized - 128.0) + 128.0;
        ((adjusted / 255.0) * 65535.0).clamp(0.0, 65535.0) as u16
    }
}

/// 滤镜管理器
pub struct FilterManager {
    original_ramp: Option<GammaRamp>,
}

impl FilterManager {
    pub fn new() -> Self {
        FilterManager {
            original_ramp: None,
        }
    }

    /// 保存原始 Gamma Ramp
    pub fn save_original(&mut self) -> Result<(), String> {
        unsafe {
            let hdc = GetDC(HWND(0));
            let mut ramp = GammaRamp::default();

            let success = GetDeviceGammaRamp(hdc, &mut ramp as *mut _ as *mut _);

            ReleaseDC(HWND(0), hdc);

            if success.as_bool() {
                self.original_ramp = Some(ramp);
                Ok(())
            } else {
                Err("无法获取原始 Gamma Ramp".to_string())
            }
        }
    }

    /// 应用 Gamma Ramp
    pub fn apply_ramp(&self, ramp: &GammaRamp) -> Result<(), String> {
        unsafe {
            let hdc = GetDC(HWND(0));
            let success = SetDeviceGammaRamp(hdc, ramp as *const _ as *const _);
            ReleaseDC(HWND(0), hdc);

            if success.as_bool() {
                Ok(())
            } else {
                Err("无法应用 Gamma Ramp".to_string())
            }
        }
    }

    /// 恢复原始设置
    pub fn restore_original(&self) -> Result<(), String> {
        if let Some(ref ramp) = self.original_ramp {
            self.apply_ramp(ramp)
        } else {
            // 如果没有保存原始设置，使用默认线性 Ramp
            let ramp = GammaRamp::default();
            self.apply_ramp(&ramp)
        }
    }
}

impl Drop for FilterManager {
    fn drop(&mut self) {
        // 应用退出时自动恢复
        let _ = self.restore_original();
    }
}
```

---

## 📊 滤镜配置结构

### Rust 数据结构
```rust
// src-tauri/src/filter/types.rs

use serde::{Deserialize, Serialize};

/// 滤镜配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilterConfig {
    pub brightness: f64,  // 0.5 - 2.0 (默认 1.0)
    pub gamma: f64,       // 0.5 - 2.0 (默认 1.0)
    pub contrast: f64,    // 0.5 - 2.0 (默认 1.0)
    pub red_scale: f64,   // 0.5 - 2.0 (默认 1.0)
    pub green_scale: f64, // 0.5 - 2.0 (默认 1.0)
    pub blue_scale: f64,  // 0.5 - 2.0 (默认 1.0)
}

impl FilterConfig {
    /// 创建默认配置
    pub fn default_preset() -> Self {
        FilterConfig {
            brightness: 1.0,
            gamma: 1.0,
            contrast: 1.0,
            red_scale: 1.0,
            green_scale: 1.0,
            blue_scale: 1.0,
        }
    }

    /// 白天预设
    pub fn daytime_preset() -> Self {
        FilterConfig {
            brightness: 1.1,
            gamma: 1.0,
            contrast: 1.05,
            red_scale: 1.0,
            green_scale: 1.0,
            blue_scale: 0.95,
        }
    }

    /// 夜间预设（提高暗部可见度）
    pub fn nighttime_preset() -> Self {
        FilterConfig {
            brightness: 1.3,
            gamma: 0.8,  // 降低 gamma 使暗部更亮
            contrast: 1.15,
            red_scale: 1.05,
            green_scale: 1.1,
            blue_scale: 1.15,
        }
    }

    /// 转换为 Gamma Ramp
    pub fn to_gamma_ramp(&self) -> GammaRamp {
        let mut ramp = GammaRamp::default();

        // 应用伽马
        ramp.apply_gamma(self.gamma);

        // 应用对比度
        ramp.apply_contrast(self.contrast);

        // 应用亮度
        ramp.apply_brightness(self.brightness);

        // 应用 RGB 通道
        ramp.apply_rgb_channels(self.red_scale, self.green_scale, self.blue_scale);

        ramp
    }
}

/// 滤镜预设
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilterPreset {
    pub id: String,
    pub name: String,
    pub config: FilterConfig,
    pub hotkey: Option<String>, // 如 "F2", "F3", "F4"
}

impl FilterPreset {
    pub fn new(id: &str, name: &str, config: FilterConfig, hotkey: Option<&str>) -> Self {
        FilterPreset {
            id: id.to_string(),
            name: name.to_string(),
            config,
            hotkey: hotkey.map(|s| s.to_string()),
        }
    }
}
```

---

## 🎮 Tauri 命令接口

```rust
// src-tauri/src/commands/filter.rs

use crate::filter::{FilterManager, FilterConfig, FilterPreset};
use tauri::State;
use std::sync::Mutex;

#[tauri::command]
pub fn apply_filter(
    config: FilterConfig,
    manager: State<Mutex<FilterManager>>,
) -> Result<(), String> {
    let manager = manager.lock().unwrap();
    let ramp = config.to_gamma_ramp();
    manager.apply_ramp(&ramp)
}

#[tauri::command]
pub fn restore_filter(
    manager: State<Mutex<FilterManager>>,
) -> Result<(), String> {
    let manager = manager.lock().unwrap();
    manager.restore_original()
}

#[tauri::command]
pub fn get_default_presets() -> Vec<FilterPreset> {
    vec![
        FilterPreset::new(
            "default",
            "默认",
            FilterConfig::default_preset(),
            Some("F2"),
        ),
        FilterPreset::new(
            "daytime",
            "白天",
            FilterConfig::daytime_preset(),
            Some("F3"),
        ),
        FilterPreset::new(
            "nighttime",
            "夜间",
            FilterConfig::nighttime_preset(),
            Some("F4"),
        ),
    ]
}
```

---

## 🔥 全局快捷键系统

### Tauri 插件：tauri-plugin-global-shortcut

```rust
// src-tauri/src/main.rs

use tauri_plugin_global_shortcut::GlobalShortcutExt;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .setup(|app| {
            // 注册默认快捷键
            app.global_shortcut().on_shortcut("F2", |app, _shortcut, _event| {
                // 应用默认滤镜
                app.emit("apply_preset", "default").unwrap();
            })?;

            app.global_shortcut().on_shortcut("F3", |app, _shortcut, _event| {
                // 应用白天滤镜
                app.emit("apply_preset", "daytime").unwrap();
            })?;

            app.global_shortcut().on_shortcut("F4", |app, _shortcut, _event| {
                // 应用夜间滤镜
                app.emit("apply_preset", "nighttime").unwrap();
            })?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            apply_filter,
            restore_filter,
            get_default_presets,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### 快捷键管理
```rust
// src-tauri/src/filter/hotkey.rs

use std::collections::HashMap;

pub struct HotkeyManager {
    bindings: HashMap<String, String>, // hotkey -> preset_id
}

impl HotkeyManager {
    pub fn new() -> Self {
        let mut bindings = HashMap::new();
        bindings.insert("F2".to_string(), "default".to_string());
        bindings.insert("F3".to_string(), "daytime".to_string());
        bindings.insert("F4".to_string(), "nighttime".to_string());

        HotkeyManager { bindings }
    }

    /// 检查快捷键是否已被占用
    pub fn is_hotkey_taken(&self, hotkey: &str) -> bool {
        self.bindings.contains_key(hotkey)
    }

    /// 绑定快捷键到预设
    pub fn bind_hotkey(&mut self, preset_id: String, hotkey: String) -> Result<(), String> {
        if self.is_hotkey_taken(&hotkey) {
            return Err(format!("快捷键 {} 已被占用", hotkey));
        }

        self.bindings.insert(hotkey, preset_id);
        Ok(())
    }

    /// 解绑快捷键
    pub fn unbind_hotkey(&mut self, hotkey: &str) {
        self.bindings.remove(hotkey);
    }

    /// 重置快捷键
    pub fn reset_hotkey(&mut self, preset_id: &str) {
        self.bindings.retain(|_key, value| value != preset_id);
    }
}
```

---

## 🎨 前端 UI 设计

### 页面布局
```typescript
// src/pages/ScreenFilter.tsx

import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { listen } from '@tauri-apps/api/event';

interface FilterConfig {
  brightness: number;
  gamma: number;
  contrast: number;
  red_scale: number;
  green_scale: number;
  blue_scale: number;
}

interface FilterPreset {
  id: string;
  name: string;
  config: FilterConfig;
  hotkey: string | null;
}

export default function ScreenFilter() {
  const [presets, setPresets] = useState<FilterPreset[]>([]);
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [currentConfig, setCurrentConfig] = useState<FilterConfig>({
    brightness: 1.0,
    gamma: 1.0,
    contrast: 1.0,
    red_scale: 1.0,
    green_scale: 1.0,
    blue_scale: 1.0,
  });

  useEffect(() => {
    // 加载预设
    invoke<FilterPreset[]>('get_default_presets').then(setPresets);

    // 监听快捷键事件
    const unlisten = listen<string>('apply_preset', (event) => {
      applyPreset(event.payload);
    });

    return () => {
      unlisten.then(fn => fn());
    };
  }, []);

  const applyPreset = async (presetId: string) => {
    const preset = presets.find(p => p.id === presetId);
    if (!preset) return;

    try {
      await invoke('apply_filter', { config: preset.config });
      setActivePreset(presetId);
      setCurrentConfig(preset.config);
    } catch (error) {
      console.error('应用滤镜失败:', error);
    }
  };

  const applyCustomConfig = async () => {
    try {
      await invoke('apply_filter', { config: currentConfig });
      setActivePreset(null);
    } catch (error) {
      console.error('应用滤镜失败:', error);
    }
  };

  const restoreDefault = async () => {
    try {
      await invoke('restore_filter');
      setActivePreset(null);
      setCurrentConfig({
        brightness: 1.0,
        gamma: 1.0,
        contrast: 1.0,
        red_scale: 1.0,
        green_scale: 1.0,
        blue_scale: 1.0,
      });
    } catch (error) {
      console.error('恢复滤镜失败:', error);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">🎨 屏幕滤镜</h1>

      {/* 预设快速切换 */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4">快速预设</h2>
        <div className="grid grid-cols-3 gap-4">
          {presets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => applyPreset(preset.id)}
              className={`p-4 rounded-lg border-2 transition ${
                activePreset === preset.id
                  ? 'border-blue-500 bg-blue-900'
                  : 'border-gray-700 bg-gray-800 hover:border-gray-600'
              }`}
            >
              <div className="font-bold text-lg mb-2">{preset.name}</div>
              {preset.hotkey && (
                <div className="text-sm text-gray-400">
                  快捷键: {preset.hotkey}
                </div>
              )}
            </button>
          ))}
        </div>
      </section>

      {/* 自定义调节 */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4">自定义调节</h2>

        <div className="space-y-4 bg-gray-800 p-6 rounded-lg">
          {/* 亮度 */}
          <div>
            <label className="block mb-2">
              亮度: {(currentConfig.brightness * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="50"
              max="200"
              value={currentConfig.brightness * 100}
              onChange={(e) =>
                setCurrentConfig({
                  ...currentConfig,
                  brightness: parseInt(e.target.value) / 100,
                })
              }
              className="w-full"
            />
          </div>

          {/* 伽马 */}
          <div>
            <label className="block mb-2">
              伽马: {currentConfig.gamma.toFixed(2)}
            </label>
            <input
              type="range"
              min="50"
              max="200"
              value={currentConfig.gamma * 100}
              onChange={(e) =>
                setCurrentConfig({
                  ...currentConfig,
                  gamma: parseInt(e.target.value) / 100,
                })
              }
              className="w-full"
            />
            <span className="text-xs text-gray-500">
              越小越亮（推荐 0.8-1.2）
            </span>
          </div>

          {/* 对比度 */}
          <div>
            <label className="block mb-2">
              对比度: {(currentConfig.contrast * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="50"
              max="200"
              value={currentConfig.contrast * 100}
              onChange={(e) =>
                setCurrentConfig({
                  ...currentConfig,
                  contrast: parseInt(e.target.value) / 100,
                })
              }
              className="w-full"
            />
          </div>

          {/* RGB 通道 */}
          <div className="pt-4 border-t border-gray-700">
            <h3 className="font-bold mb-3">色温调节（RGB 通道）</h3>

            <div className="space-y-3">
              <div>
                <label className="block mb-2 text-red-400">
                  红色: {(currentConfig.red_scale * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="50"
                  max="200"
                  value={currentConfig.red_scale * 100}
                  onChange={(e) =>
                    setCurrentConfig({
                      ...currentConfig,
                      red_scale: parseInt(e.target.value) / 100,
                    })
                  }
                  className="w-full"
                />
              </div>

              <div>
                <label className="block mb-2 text-green-400">
                  绿色: {(currentConfig.green_scale * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="50"
                  max="200"
                  value={currentConfig.green_scale * 100}
                  onChange={(e) =>
                    setCurrentConfig({
                      ...currentConfig,
                      green_scale: parseInt(e.target.value) / 100,
                    })
                  }
                  className="w-full"
                />
              </div>

              <div>
                <label className="block mb-2 text-blue-400">
                  蓝色: {(currentConfig.blue_scale * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="50"
                  max="200"
                  value={currentConfig.blue_scale * 100}
                  onChange={(e) =>
                    setCurrentConfig({
                      ...currentConfig,
                      blue_scale: parseInt(e.target.value) / 100,
                    })
                  }
                  className="w-full"
                />
              </div>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-4 pt-4">
            <button
              onClick={applyCustomConfig}
              className="flex-1 px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
            >
              应用
            </button>
            <button
              onClick={restoreDefault}
              className="flex-1 px-4 py-2 bg-gray-700 rounded hover:bg-gray-600"
            >
              恢复默认
            </button>
          </div>
        </div>
      </section>

      {/* 提示信息 */}
      <div className="bg-yellow-900 bg-opacity-30 border border-yellow-700 p-4 rounded-lg">
        <p className="text-yellow-200 text-sm">
          💡 滤镜使用 Windows 系统级 API，完全合法，不违反游戏 TOS
        </p>
        <p className="text-yellow-200 text-sm mt-2">
          🔑 快捷键: F2 默认 | F3 白天 | F4 夜间
        </p>
      </div>
    </div>
  );
}
```

---

## 📦 Cargo 依赖

```toml
# src-tauri/Cargo.toml

[dependencies]
tauri = { version = "2.0", features = ["global-shortcut"] }
tauri-plugin-global-shortcut = "2.0"
serde = { version = "1", features = ["derive"] }
serde_json = "1"

[target.'cfg(windows)'.dependencies]
windows = { version = "0.51", features = [
    "Win32_Graphics_Gdi",
    "Win32_Foundation"
]}
```

---

## ✅ 功能清单

- ✅ 三套默认预设（默认/白天/夜间）
- ✅ 亮度、伽马、对比度调节
- ✅ RGB 三通道独立调节（色温）
- ✅ Windows `SetDeviceGammaRamp` API（系统级，不违反 TOS）
- ✅ 全局快捷键（F2/F3/F4，可自定义）
- ✅ 防止快捷键重复绑定
- ✅ 支持重置快捷键
- ✅ 应用退出自动恢复
- ✅ 实时预览调整效果

---

## 🚀 实现步骤

1. **Rust 后端**（第 1-2 天）
   - Gamma Ramp API 封装
   - 滤镜配置管理
   - Tauri 命令接口

2. **全局快捷键**（第 3 天）
   - 集成 tauri-plugin-global-shortcut
   - 快捷键管理器
   - 快捷键绑定逻辑

3. **前端 UI**（第 4-5 天）
   - 预设切换界面
   - 滑块调节组件
   - 实时应用和预览

4. **测试和优化**（第 6 天）
   - 多显示器支持
   - 错误处理
   - 性能优化

---

**下一步**: 开始实现 Rust 后端的 Gamma Ramp 系统？
