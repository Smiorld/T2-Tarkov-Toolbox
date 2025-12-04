# 截图位置识别技术指南

## 🎯 核心原理

塔科夫游戏在保存截图时会在图片的 **EXIF 元数据** 中嵌入玩家的位置信息，包括：
- X 坐标
- Y 坐标
- Z 坐标（高度）
- 旋转角度
- 地图名称

我们可以读取这些元数据，无需 OCR 或图像识别即可获取准确位置。

## 📂 截图位置

### Windows 默认路径
```
C:\Users\<用户名>\Documents\Escape from Tarkov\Screenshots\
```

### 文件命名格式
```
photo_2024-12-03_15-30-45.png
```

## 🦀 Rust 实现

### 依赖配置

```toml
# Cargo.toml
[dependencies]
exif = "0.5"
notify = "6.1"
serde = { version = "1.0", features = ["derive"] }
```

### 数据结构定义

```rust
// src-tauri/src/models/player_position.rs

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlayerPosition {
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub rotation: f64,
    pub map_name: String,
    pub timestamp: String,
}

impl PlayerPosition {
    pub fn new(x: f64, y: f64, z: f64, rotation: f64, map_name: String) -> Self {
        Self {
            x,
            y,
            z,
            rotation,
            map_name,
            timestamp: chrono::Utc::now().to_rfc3339(),
        }
    }
}
```

### EXIF 解析实现

```rust
// src-tauri/src/utils/screenshot_parser.rs

use exif::{In, Reader, Tag};
use std::fs::File;
use std::path::Path;

use crate::models::player_position::PlayerPosition;

pub fn parse_screenshot(path: &Path) -> Result<PlayerPosition, String> {
    // 打开文件
    let file = File::open(path)
        .map_err(|e| format!("无法打开文件: {}", e))?;

    // 读取 EXIF 数据
    let mut bufreader = std::io::BufReader::new(&file);
    let exif_reader = Reader::new();
    let exif = exif_reader
        .read_from_container(&mut bufreader)
        .map_err(|e| format!("无法读取 EXIF 数据: {}", e))?;

    // 提取位置信息
    // 注意: 这些字段名可能需要根据实际情况调整
    let x = extract_float(&exif, Tag::GPSLongitude, In::PRIMARY)?;
    let y = extract_float(&exif, Tag::GPSLatitude, In::PRIMARY)?;
    let z = extract_float(&exif, Tag::GPSAltitude, In::PRIMARY).unwrap_or(0.0);
    let rotation = extract_float(&exif, Tag::GPSImgDirection, In::PRIMARY).unwrap_or(0.0);
    
    // 提取地图名称（可能存储在 UserComment 或其他字段）
    let map_name = extract_string(&exif, Tag::UserComment, In::PRIMARY)
        .unwrap_or_else(|_| "Unknown".to_string());

    Ok(PlayerPosition::new(x, y, z, rotation, map_name))
}

fn extract_float(exif: &exif::Exif, tag: Tag, ifd: In) -> Result<f64, String> {
    let field = exif
        .get_field(tag, ifd)
        .ok_or_else(|| format!("未找到字段: {:?}", tag))?;

    match field.value {
        exif::Value::Rational(ref vec) if !vec.is_empty() => {
            Ok(vec[0].num as f64 / vec[0].denom as f64)
        }
        exif::Value::SRational(ref vec) if !vec.is_empty() => {
            Ok(vec[0].num as f64 / vec[0].denom as f64)
        }
        _ => Err(format!("无法解析字段值: {:?}", tag)),
    }
}

fn extract_string(exif: &exif::Exif, tag: Tag, ifd: In) -> Result<String, String> {
    let field = exif
        .get_field(tag, ifd)
        .ok_or_else(|| format!("未找到字段: {:?}", tag))?;

    Ok(field.display_value().to_string())
}
```

### 文件监控实现

```rust
// src-tauri/src/utils/screenshot_watcher.rs

use notify::{Config, Event, RecommendedWatcher, RecursiveMode, Watcher};
use std::path::PathBuf;
use std::sync::mpsc::channel;
use tauri::{AppHandle, Manager};

pub fn start_watching_screenshots(
    app_handle: AppHandle,
    screenshot_path: PathBuf,
) -> Result<(), String> {
    // 创建通道
    let (tx, rx) = channel();

    // 创建文件监控器
    let mut watcher = RecommendedWatcher::new(
        move |res: Result<Event, notify::Error>| {
            if let Ok(event) = res {
                tx.send(event).unwrap();
            }
        },
        Config::default(),
    )
    .map_err(|e| format!("创建监控器失败: {}", e))?;

    // 开始监控目录
    watcher
        .watch(&screenshot_path, RecursiveMode::NonRecursive)
        .map_err(|e| format!("监控目录失败: {}", e))?;

    // 在后台线程处理文件变化事件
    std::thread::spawn(move || {
        for event in rx {
            if let notify::EventKind::Create(_) = event.kind {
                for path in event.paths {
                    // 检查是否是 PNG 文件
                    if path.extension().and_then(|s| s.to_str()) == Some("png") {
                        // 解析截图
                        match parse_screenshot(&path) {
                            Ok(position) => {
                                // 发送位置信息到前端
                                app_handle
                                    .emit_all("new-screenshot", position)
                                    .ok();
                            }
                            Err(e) => {
                                eprintln!("解析截图失败: {}", e);
                            }
                        }
                    }
                }
            }
        }
    });

    // 保持 watcher 存活
    std::mem::forget(watcher);

    Ok(())
}
```

### Tauri Command

```rust
// src-tauri/src/commands/screenshot.rs

use tauri::State;
use std::sync::Mutex;
use std::path::PathBuf;

use crate::utils::screenshot_watcher::start_watching_screenshots;
use crate::utils::screenshot_parser::parse_screenshot;
use crate::models::player_position::PlayerPosition;

pub struct ScreenshotWatcherState {
    pub screenshot_path: Mutex<Option<PathBuf>>,
}

#[tauri::command]
pub fn set_screenshot_path(
    app_handle: tauri::AppHandle,
    state: State<ScreenshotWatcherState>,
    path: String,
) -> Result<(), String> {
    let screenshot_path = PathBuf::from(path);

    // 验证路径是否存在
    if !screenshot_path.exists() {
        return Err("截图文件夹不存在".to_string());
    }

    // 保存路径
    *state.screenshot_path.lock().unwrap() = Some(screenshot_path.clone());

    // 开始监控
    start_watching_screenshots(app_handle, screenshot_path)?;

    Ok(())
}

#[tauri::command]
pub fn parse_screenshot_file(path: String) -> Result<PlayerPosition, String> {
    let file_path = PathBuf::from(path);
    parse_screenshot(&file_path)
}

#[tauri::command]
pub fn get_default_screenshot_path() -> Result<String, String> {
    // Windows 默认路径
    let username = std::env::var("USERNAME")
        .map_err(|_| "无法获取用户名".to_string())?;
    
    let path = format!(
        "C:\\Users\\{}\\Documents\\Escape from Tarkov\\Screenshots",
        username
    );

    Ok(path)
}
```

## ⚛️ React/TypeScript 前端集成

### 监听截图事件

```typescript
// src/hooks/useScreenshotMonitor.ts

import { useEffect, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/tauri';

export interface PlayerPosition {
  x: number;
  y: number;
  z: number;
  rotation: number;
  mapName: string;
  timestamp: string;
}

export function useScreenshotMonitor() {
  const [currentPosition, setCurrentPosition] = useState<PlayerPosition | null>(null);
  const [screenshotPath, setScreenshotPath] = useState<string>('');

  // 初始化默认路径
  useEffect(() => {
    invoke<string>('get_default_screenshot_path')
      .then(path => {
        setScreenshotPath(path);
        return invoke('set_screenshot_path', { path });
      })
      .catch(err => console.error('设置截图路径失败:', err));
  }, []);

  // 监听新截图事件
  useEffect(() => {
    const unlisten = listen<PlayerPosition>('new-screenshot', (event) => {
      console.log('检测到新截图:', event.payload);
      setCurrentPosition(event.payload);
    });

    return () => {
      unlisten.then(fn => fn());
    };
  }, []);

  const updateScreenshotPath = async (newPath: string) => {
    try {
      await invoke('set_screenshot_path', { path: newPath });
      setScreenshotPath(newPath);
    } catch (error) {
      console.error('更新截图路径失败:', error);
      throw error;
    }
  };

  return {
    currentPosition,
    screenshotPath,
    updateScreenshotPath,
  };
}
```

### 地图组件使用

```tsx
// src/pages/TarkovMap.tsx

import { useScreenshotMonitor } from '../hooks/useScreenshotMonitor';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';

export default function TarkovMap() {
  const { currentPosition } = useScreenshotMonitor();

  return (
    <div className="h-screen w-full">
      <h1 className="text-2xl font-bold p-4">战术地图</h1>
      
      {currentPosition && (
        <div className="p-4 bg-blue-100">
          <p>当前位置: ({currentPosition.x.toFixed(2)}, {currentPosition.y.toFixed(2)})</p>
          <p>地图: {currentPosition.mapName}</p>
          <p>朝向: {currentPosition.rotation.toFixed(0)}°</p>
        </div>
      )}

      <MapContainer
        center={[0, 0]}
        zoom={2}
        className="h-full"
      >
        <TileLayer url="/maps/{z}/{x}/{y}.png" />
        
        {currentPosition && (
          <Marker position={[currentPosition.y, currentPosition.x]}>
            <Popup>
              你在这里！<br />
              朝向: {currentPosition.rotation.toFixed(0)}°
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}
```

## 🔧 调试技巧

### 1. 测试 EXIF 读取

```rust
#[tauri::command]
pub fn debug_exif(path: String) -> Result<String, String> {
    let file = File::open(&path)
        .map_err(|e| format!("打开文件失败: {}", e))?;

    let mut bufreader = std::io::BufReader::new(&file);
    let exif_reader = Reader::new();
    let exif = exif_reader
        .read_from_container(&mut bufreader)
        .map_err(|e| format!("读取 EXIF 失败: {}", e))?;

    let mut output = String::new();
    for field in exif.fields() {
        output.push_str(&format!(
            "{:?}: {}\n",
            field.tag,
            field.display_value()
        ));
    }

    Ok(output)
}
```

### 2. 手动触发解析

```tsx
// 添加调试按钮
<button onClick={async () => {
  const result = await invoke('debug_exif', {
    path: 'C:\\Users\\...\\photo_2024-12-03_15-30-45.png'
  });
  console.log(result);
}}>
  调试 EXIF
</button>
```

## ⚠️ 注意事项

1. **EXIF 字段名称**: 塔科夫可能使用自定义的 EXIF 字段，需要实际测试确认
2. **坐标系统**: 游戏坐标系可能需要转换才能在地图上正确显示
3. **文件权限**: 确保应用有权限读取截图文件夹
4. **性能**: 监控大量文件时注意性能优化

## 🎓 参考项目

- TarkovMonitor (C#): https://github.com/the-hideout/TarkovMonitor
- TarkovMapTracker (Python): https://github.com/M4elstr0m/TarkovMapTracker
- TarkovQuestie (Web): https://tarkovquestie.com/

---

**下一步**: 需要实际获取塔科夫截图样本来确认 EXIF 字段的具体名称和格式。
