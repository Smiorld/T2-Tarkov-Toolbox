# T2 塔科夫工具箱 - 配置管理架构

## 📋 设计目标

1. **全局配置文件** - 所有用户配置集中存储
2. **导入/导出功能** - 用户可以备份和迁移配置
3. **分页独立配置** - 某些页面可以有独立的配置导入/导出
4. **类型安全** - TypeScript + Rust 类型定义
5. **自动保存** - 配置修改后自动持久化

## 📁 配置文件结构

### 主配置文件

**位置**: `%APPDATA%/T2-Tarkov-Toolbox/config.json` (Windows)

```json
{
  "version": "1.0.0",
  "global": {
    "language": "zh-CN",
    "theme": "dark",
    "autoStart": false,
    "minimizeToTray": true
  },
  "screenshot": {
    "watchPath": "C:\\Users\\Username\\Documents\\Escape from Tarkov\\Screenshots",
    "autoDetect": true,
    "notifyOnDetect": true
  },
  "screenFilter": {
    "enabled": false,
    "brightness": 100,
    "contrast": 100,
    "saturation": 100,
    "hue": 0,
    "redChannel": 100,
    "greenChannel": 100,
    "blueChannel": 100,
    "presets": [
      {
        "name": "夜视模式",
        "brightness": 120,
        "contrast": 110,
        "saturation": 90
      }
    ]
  },
  "map": {
    "defaultMap": "Customs",
    "showSpawnPoints": true,
    "showExtracts": true,
    "showQuestMarkers": true,
    "autoCenter": true,
    "opacity": 0.8
  },
  "quest": {
    "tarkovTrackerToken": "",
    "syncEnabled": false,
    "autoSync": true,
    "syncInterval": 600,
    "showCompletedQuests": false,
    "groupByTrader": true,
    "expandedTraders": ["Prapor", "Therapist", "Skier", "Peacekeeper", "Mechanic", "Ragman", "Jaeger", "Fence"]
  },
  "hotkeys": {
    "toggleOverlay": "Ctrl+Shift+T",
    "openMap": "Ctrl+Shift+M",
    "openPrice": "Ctrl+Shift+P"
  },
  "metadata": {
    "lastModified": "2024-12-03T12:00:00Z",
    "createdAt": "2024-12-03T10:00:00Z"
  }
}
```

### 分页独立配置

某些页面可以有独立的配置文件，方便分享：

#### 屏幕滤镜预设 (`filter-presets.json`)
```json
{
  "version": "1.0.0",
  "presets": [
    {
      "id": "night-vision",
      "name": "夜视模式",
      "description": "提高暗部可见度",
      "brightness": 120,
      "contrast": 110,
      "saturation": 90,
      "author": "用户名",
      "tags": ["夜间", "Woods"]
    }
  ]
}
```

#### 地图标记 (`map-markers.json`)
```json
{
  "version": "1.0.0",
  "mapName": "Customs",
  "customMarkers": [
    {
      "id": "marker-001",
      "name": "藏匿点",
      "x": 123.5,
      "y": 456.7,
      "type": "loot",
      "notes": "经常刷好东西"
    }
  ]
}
```

## 🏗️ 技术架构

### 1. Rust 后端（配置文件管理）

```
src-tauri/src/
├── config/
│   ├── mod.rs              # 配置模块入口
│   ├── types.rs            # 配置结构体定义
│   ├── manager.rs          # 配置管理器
│   ├── persistence.rs      # 文件读写
│   └── validation.rs       # 配置验证
└── commands/
    └── config.rs           # Tauri 命令（供前端调用）
```

**核心结构体**：

```rust
// src-tauri/src/config/types.rs

use serde::{Deserialize, Serialize};

/// 主配置结构体
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub version: String,
    pub global: GlobalConfig,
    pub screenshot: ScreenshotConfig,
    pub screen_filter: ScreenFilterConfig,
    pub map: MapConfig,
    pub price: PriceConfig,
    pub hotkeys: HotkeyConfig,
    pub metadata: ConfigMetadata,
}

/// 全局配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalConfig {
    pub language: String,
    pub theme: String,
    pub auto_start: bool,
    pub minimize_to_tray: bool,
}

/// 屏幕滤镜配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreenFilterConfig {
    pub enabled: bool,
    pub brightness: i32,
    pub contrast: i32,
    pub saturation: i32,
    pub hue: i32,
    pub red_channel: i32,
    pub green_channel: i32,
    pub blue_channel: i32,
    pub presets: Vec<FilterPreset>,
}

// ... 其他配置结构体
```

### 2. 前端（Zustand 状态管理）

```
src/
├── stores/
│   ├── useConfigStore.ts       # 全局配置 Store
│   ├── useFilterStore.ts       # 屏幕滤镜 Store
│   ├── useMapStore.ts          # 地图配置 Store
│   └── usePriceStore.ts        # 物价配置 Store
├── types/
│   └── config.ts               # TypeScript 类型定义
└── utils/
    ├── configManager.ts        # 配置管理工具
    └── configValidator.ts      # 配置验证
```

**Zustand Store 示例**：

```typescript
// src/stores/useConfigStore.ts

import { create } from 'zustand';
import { invoke } from '@tauri-apps/api/tauri';
import type { AppConfig } from '../types/config';

interface ConfigStore {
  config: AppConfig | null;
  loading: boolean;

  // 加载配置
  loadConfig: () => Promise<void>;

  // 保存配置
  saveConfig: (config: AppConfig) => Promise<void>;

  // 更新部分配置
  updateConfig: <K extends keyof AppConfig>(
    key: K,
    value: AppConfig[K]
  ) => Promise<void>;

  // 导出配置
  exportConfig: (path: string) => Promise<void>;

  // 导入配置
  importConfig: (path: string) => Promise<void>;

  // 重置为默认配置
  resetConfig: () => Promise<void>;
}

export const useConfigStore = create<ConfigStore>((set, get) => ({
  config: null,
  loading: false,

  loadConfig: async () => {
    set({ loading: true });
    try {
      const config = await invoke<AppConfig>('load_config');
      set({ config, loading: false });
    } catch (error) {
      console.error('加载配置失败:', error);
      set({ loading: false });
    }
  },

  saveConfig: async (config) => {
    await invoke('save_config', { config });
    set({ config });
  },

  updateConfig: async (key, value) => {
    const { config } = get();
    if (!config) return;

    const newConfig = { ...config, [key]: value };
    await invoke('save_config', { config: newConfig });
    set({ config: newConfig });
  },

  exportConfig: async (path) => {
    await invoke('export_config', { path });
  },

  importConfig: async (path) => {
    const config = await invoke<AppConfig>('import_config', { path });
    set({ config });
  },

  resetConfig: async () => {
    const config = await invoke<AppConfig>('reset_config');
    set({ config });
  },
}));
```

## 🔧 Tauri 命令接口

```rust
// src-tauri/src/commands/config.rs

use crate::config::{AppConfig, ConfigManager};
use tauri::State;

/// 加载配置
#[tauri::command]
pub fn load_config(
    config_manager: State<ConfigManager>,
) -> Result<AppConfig, String> {
    config_manager
        .load()
        .map_err(|e| format!("加载配置失败: {}", e))
}

/// 保存配置
#[tauri::command]
pub fn save_config(
    config: AppConfig,
    config_manager: State<ConfigManager>,
) -> Result<(), String> {
    config_manager
        .save(&config)
        .map_err(|e| format!("保存配置失败: {}", e))
}

/// 导出配置到指定路径
#[tauri::command]
pub fn export_config(
    path: String,
    config_manager: State<ConfigManager>,
) -> Result<(), String> {
    config_manager
        .export(&path)
        .map_err(|e| format!("导出配置失败: {}", e))
}

/// 从指定路径导入配置
#[tauri::command]
pub fn import_config(
    path: String,
    config_manager: State<ConfigManager>,
) -> Result<AppConfig, String> {
    config_manager
        .import(&path)
        .map_err(|e| format!("导入配置失败: {}", e))
}

/// 重置为默认配置
#[tauri::command]
pub fn reset_config(
    config_manager: State<ConfigManager>,
) -> Result<AppConfig, String> {
    config_manager
        .reset()
        .map_err(|e| format!("重置配置失败: {}", e))
}

/// 验证配置文件
#[tauri::command]
pub fn validate_config_file(path: String) -> Result<bool, String> {
    crate::config::validation::validate_file(&path)
        .map_err(|e| format!("验证配置失败: {}", e))
}
```

## 📤 导入/导出 UI 设计

### 全局设置页面

```typescript
// src/pages/Settings.tsx

import { useConfigStore } from '../stores/useConfigStore';
import { open, save } from '@tauri-apps/plugin-dialog';

export default function Settings() {
  const { config, exportConfig, importConfig, resetConfig } = useConfigStore();

  const handleExport = async () => {
    const path = await save({
      defaultPath: 'tarkov-toolbox-config.json',
      filters: [{ name: 'Config', extensions: ['json'] }],
    });

    if (path) {
      await exportConfig(path);
      alert('配置已导出！');
    }
  };

  const handleImport = async () => {
    const path = await open({
      multiple: false,
      filters: [{ name: 'Config', extensions: ['json'] }],
    });

    if (path && typeof path === 'string') {
      try {
        await importConfig(path);
        alert('配置已导入！');
      } catch (error) {
        alert('导入失败：' + error);
      }
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">全局设置</h1>

      {/* 配置管理 */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4">配置管理</h2>
        <div className="flex gap-4">
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
          >
            导出配置
          </button>
          <button
            onClick={handleImport}
            className="px-4 py-2 bg-green-600 rounded hover:bg-green-700"
          >
            导入配置
          </button>
          <button
            onClick={resetConfig}
            className="px-4 py-2 bg-red-600 rounded hover:bg-red-700"
          >
            重置为默认
          </button>
        </div>
      </section>

      {/* 其他设置项 */}
    </div>
  );
}
```

### 分页独立配置（屏幕滤镜预设）

```typescript
// src/pages/ScreenFilter.tsx

const handleExportPresets = async () => {
  const path = await save({
    defaultPath: 'filter-presets.json',
    filters: [{ name: 'Filter Presets', extensions: ['json'] }],
  });

  if (path) {
    await invoke('export_filter_presets', { path });
    alert('滤镜预设已导出！');
  }
};

const handleImportPresets = async () => {
  const path = await open({
    multiple: false,
    filters: [{ name: 'Filter Presets', extensions: ['json'] }],
  });

  if (path && typeof path === 'string') {
    try {
      const presets = await invoke('import_filter_presets', { path });
      // 合并到现有预设
      alert('滤镜预设已导入！');
    } catch (error) {
      alert('导入失败：' + error);
    }
  }
};
```

## 🔒 配置迁移和版本管理

### 版本控制

配置文件包含 `version` 字段，用于处理配置格式升级：

```rust
// src-tauri/src/config/migration.rs

pub fn migrate_config(config: serde_json::Value) -> Result<AppConfig, Error> {
    let version = config
        .get("version")
        .and_then(|v| v.as_str())
        .unwrap_or("1.0.0");

    match version {
        "1.0.0" => {
            // 直接解析
            serde_json::from_value(config).map_err(Into::into)
        }
        "1.1.0" => {
            // 从 1.1.0 迁移到最新版本
            migrate_from_1_1_0(config)
        }
        _ => Err(Error::UnsupportedVersion(version.to_string())),
    }
}
```

## 📊 配置存储位置

**配置文件存放在 .exe 同级目录下**：

```
T2-Tarkov-Toolbox.exe
config/
├── config.json              # 主配置文件
├── filter-presets.json      # 滤镜预设（可选）
├── map-markers.json         # 地图标记（可选）
└── quest-progress.json      # 任务进度缓存（可选）
```

### 优点
- ✅ 便携式 - 整个文件夹可以移动
- ✅ 易于备份 - 直接复制 config 文件夹
- ✅ 无需管理员权限
- ✅ 多用户隔离 - 每个用户有独立配置

### 配置查找逻辑（Rust）
```rust
use std::env;
use std::path::PathBuf;

pub fn get_config_dir() -> PathBuf {
    // 获取 .exe 所在目录
    let exe_path = env::current_exe()
        .expect("无法获取可执行文件路径");

    let exe_dir = exe_path
        .parent()
        .expect("无法获取可执行文件目录");

    // config 目录
    exe_dir.join("config")
}

pub fn get_config_path() -> PathBuf {
    get_config_dir().join("config.json")
}
```

## 🎯 实现优先级

### Phase 1 - 基础配置管理（第 1 周）
1. ✅ 配置结构体定义（Rust + TypeScript）
2. ✅ 配置文件读写（Rust）
3. ✅ Tauri 命令接口
4. ✅ Zustand Store 实现
5. ✅ 全局设置页面（导入/导出）

### Phase 2 - 分页配置（第 2 周）
1. ✅ 屏幕滤镜预设导入/导出
2. ✅ 地图标记导入/导出
3. ✅ 物价收藏夹导入/导出

### Phase 3 - 高级功能（第 3 周）
1. ✅ 配置验证和错误提示
2. ✅ 配置迁移系统
3. ✅ 配置备份和恢复
4. ✅ 云同步（可选）

## 🛡️ 最佳实践

### 1. 配置默认值（硬编码）

**所有默认配置硬编码在代码中**，重置功能直接使用硬编码值：

```rust
// src-tauri/src/config/defaults.rs

impl Default for AppConfig {
    fn default() -> Self {
        AppConfig {
            version: "1.0.0".to_string(),
            global: GlobalConfig {
                language: "zh-CN".to_string(),
                theme: "dark".to_string(),
                auto_start: false,
                minimize_to_tray: true,
            },
            screenshot: ScreenshotConfig {
                watch_path: get_default_screenshot_path(),
                auto_detect: true,
                notify_on_detect: true,
            },
            screen_filter: ScreenFilterConfig {
                enabled: false,
                brightness: 100,
                contrast: 100,
                saturation: 100,
                hue: 0,
                red_channel: 100,
                green_channel: 100,
                blue_channel: 100,
                presets: vec![],
            },
            map: MapConfig {
                default_map: "Customs".to_string(),
                show_spawn_points: true,
                show_extracts: true,
                show_quest_markers: true,
                auto_center: true,
                opacity: 0.8,
            },
            quest: QuestConfig {
                tarkov_tracker_token: String::new(),
                sync_enabled: false,
                auto_sync: true,
                sync_interval: 600,
                show_completed_quests: false,
                group_by_trader: true,
                expanded_traders: vec![
                    "Prapor".to_string(),
                    "Therapist".to_string(),
                    "Skier".to_string(),
                    "Peacekeeper".to_string(),
                    "Mechanic".to_string(),
                    "Ragman".to_string(),
                    "Jaeger".to_string(),
                    "Fence".to_string(),
                ],
            },
            hotkeys: HotkeyConfig {
                toggle_overlay: "Ctrl+Shift+T".to_string(),
                open_map: "Ctrl+Shift+M".to_string(),
                open_quest: "Ctrl+Shift+Q".to_string(),
            },
            metadata: ConfigMetadata {
                last_modified: Utc::now(),
                created_at: Utc::now(),
            },
        }
    }
}

/// 获取默认截图路径
fn get_default_screenshot_path() -> String {
    // Windows: Documents/Escape from Tarkov/Screenshots
    let documents = dirs::document_dir()
        .expect("无法获取 Documents 目录");

    documents
        .join("Escape from Tarkov")
        .join("Screenshots")
        .to_string_lossy()
        .to_string()
}
```

### 2. 自动保存
前端修改配置后，自动调用保存命令，无需手动保存按钮（除非用户希望）。

### 3. 配置验证
导入配置前，验证 JSON 格式和必需字段：

```rust
pub fn validate_config(config: &AppConfig) -> Result<(), Vec<String>> {
    let mut errors = Vec::new();

    if config.version.is_empty() {
        errors.push("版本号不能为空".to_string());
    }

    // 验证其他字段...

    if errors.is_empty() {
        Ok(())
    } else {
        Err(errors)
    }
}
```

### 4. 错误处理
配置加载失败时，使用默认配置：

```rust
pub fn load_or_default() -> AppConfig {
    ConfigManager::load()
        .unwrap_or_else(|e| {
            eprintln!("加载配置失败，使用默认配置: {}", e);
            AppConfig::default()
        })
}
```

## 📝 总结

这个配置管理架构提供了：

- ✅ **集中管理** - 所有配置在一个文件中
- ✅ **类型安全** - Rust + TypeScript 类型定义
- ✅ **灵活导出** - 支持全局配置和分页配置导出
- ✅ **易于扩展** - 添加新配置项只需修改结构体
- ✅ **版本控制** - 支持配置格式升级和迁移
- ✅ **用户友好** - 可视化的导入/导出界面

---

**下一步**: 实现配置管理的核心代码（Rust 后端 + 前端 Store）
