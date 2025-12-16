# 本地地图模块 - 技术设计文档

## 1. 概述

本地地图模块基于TarkovMonitor的实现思路，提供以下核心功能：
- 实时监控截图和日志文件
- 多层地图支持（多楼层建筑）
- 自定义地图导入和校准
- 浮动小地图窗口
- 服务器IP地理位置显示

## 2. 核心技术原理

### 2.1 截图解析

**塔科夫截图文件名格式：**
```
2024-12-05[14-32]_123.45, 67.89, -10.23_0.1234, 0.5678, 0.9012, 0.3456 (0).png
```

**包含信息：**
- 日期时间：`YYYY-MM-DD[HH-MM]`
- 游戏世界坐标：`X, Y, Z`（Y轴为高度）
- 旋转四元数：`RX, RY, RZ, RW`
- 序号：同一秒内多张截图的索引

**实现：** [modules/local_map/screenshot_parser.py](../modules/local_map/screenshot_parser.py)

### 2.2 日志文件解析

**日志文件位置：**
```
注册表路径（BSG启动器）：HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\EscapeFromTarkov
默认路径：[InstallLocation]\Logs

Steam路径：HKCU\Software\Valve\Steam
默认路径：[SteamPath]\steamapps\common\Escape from Tarkov\build\Logs
```

**关键日志事件：**
1. **地图加载：** `scene preset path:maps/{map_bundle}.bundle`
2. **匹配完成：** `MatchingCompleted` → 获取队列时间
3. **战局创建：** `TRACE-NetworkGameCreate` → 获取战局ID、地图、模式
4. **战局开始：** `GameStarted`
5. **战局结束：** `UserMatchOver`
6. **服务器IP：** 从日志中提取IP地址

**实现：** [modules/local_map/log_parser.py](../modules/local_map/log_parser.py)

**参考资料：**
- [Tarkov Server IP Detection](https://forum.escapefromtarkov.com/topic/101978-server-ips-posted/)
- [Server Connection Guide](https://redditgame.info/escape-from-tarkov/3794)

## 3. 多层地图系统

### 3.1 数据模型

**层级结构：**
```python
MapConfig (地图配置)
  ├── MapLayer (层级 0 - 地面)
  │     ├── image_path: 地图图片路径
  │     ├── height_min/max: 高度范围
  │     └── calibration_points: 校准点列表
  ├── MapLayer (层级 1 - 一楼)
  ├── MapLayer (层级 2 - 二楼)
  └── ...
```

**自动楼层匹配：**
```python
def get_layer_by_height(y: float) -> MapLayer:
    """根据玩家Y坐标自动匹配对应楼层"""
    for layer in layers:
        if layer.height_min <= y <= layer.height_max:
            return layer
```

### 3.2 坐标校准系统

**校准流程：**
1. 用户进入游戏，在地图特定位置截图
2. 软件解析截图，获取游戏世界坐标`(X, Y, Z)`
3. 用户在地图图片上点击对应位置，提供像素坐标`(map_x, map_y)`
4. 记录校准点：`CalibrationPoint(game_pos, map_x, map_y)`
5. 至少3个点后，计算仿射变换矩阵

**坐标变换：**
```python
# 从游戏坐标转换为地图坐标
(map_x, map_y) = transform.transform(game_pos)

# 仿射变换公式：
map_x = game_x * scale_x * cos(θ) - game_z * scale_x * sin(θ) + offset_x
map_y = game_x * scale_z * sin(θ) + game_z * scale_z * cos(θ) + offset_z
```

**高度自动分层：**
```python
# 在多点定位时，基于高度信息自动确定每层范围
layer.height_min = min(point.game_pos.y for point in calibration_points)
layer.height_max = max(point.game_pos.y for point in calibration_points)
```

## 4. 浮动小地图

### 4.1 窗口特性

**功能特性：**
- ✅ 独立TopLevel窗口
- ✅ 自由拖拽位置
- ✅ 调整大小（拖拽边缘）
- ✅ 透明度调节（0.0 - 1.0）
- ✅ 锁定模式（鼠标穿透）
- ✅ 始终置顶
- ✅ 滚轮缩放地图
- ✅ 玩家居中跟随

### 4.2 鼠标穿透实现

**Windows API实现：**
```python
import ctypes
from ctypes import windll

# 获取窗口句柄
hwnd = windll.user32.GetParent(window.winfo_id())

# 设置窗口样式：WS_EX_LAYERED | WS_EX_TRANSPARENT
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20

# 启用鼠标穿透
current_style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
    current_style | WS_EX_LAYERED | WS_EX_TRANSPARENT)

# 设置透明度
windll.user32.SetLayeredWindowAttributes(hwnd, 0, int(opacity * 255), 0x2)
```

### 4.3 全局快捷键

**使用keyboard库：**
```python
import keyboard

# 注册快捷键（默认F5）
keyboard.add_hotkey('f5', toggle_floating_map)
```

## 5. 服务器IP地理位置

### 5.1 IP提取

从日志文件中提取服务器IP地址（已在LogParser中实现）

### 5.2 地理位置查询

**免费IP地理位置API选项：**
1. **ip-api.com** (免费，无需API密钥，每分钟45请求)
   ```python
   import requests
   response = requests.get(f"http://ip-api.com/json/{ip}")
   data = response.json()
   location = f"{data['city']}, {data['country']}"
   ```

2. **ipapi.co** (免费，每天1000请求)
   ```python
   response = requests.get(f"https://ipapi.co/{ip}/json/")
   ```

3. **ipinfo.io** (免费，每月50000请求，需注册获取token)

**实现建议：**
- 缓存查询结果，避免重复请求
- 使用异步请求，不阻塞主线程
- 错误处理：网络失败时显示"未知位置"

## 6. 文件监控

### 6.1 截图文件夹监控

**截图路径：**
```
%USERPROFILE%\Documents\Escape From Tarkov\Screenshots\
```

**使用watchdog库：**
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ScreenshotHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('.png'):
            parse_screenshot(event.src_path)

observer = Observer()
observer.schedule(ScreenshotHandler(), screenshots_path, recursive=False)
observer.start()
```

### 6.2 日志文件监控

**实时读取新增内容：**
```python
def monitor_log_file():
    with open(log_file, 'r') as f:
        f.seek(last_position)  # 跳到上次读取位置
        new_lines = f.readlines()
        for line in new_lines:
            parse_log_line(line)
        last_position = f.tell()  # 记录当前位置
```

## 7. UI设计

### 7.1 主面板布局

```
┌─────────────────────────────────────────────┐
│  [地图选择]  [层级选择]  [校准模式] [设置]    │
├──────────────────┬──────────────────────────┤
│  地图列表        │  地图Canvas                │
│  - Customs       │                            │
│  - Interchange   │  [地图图片]                │
│  - Streets       │   └─ 玩家标记              │
│                  │   └─ 校准点                │
│  [导入地图]      │                            │
│  [清除校准]      │  Zoom: [滑块]              │
│                  │  居中: [✓]                 │
└──────────────────┴──────────────────────────┘
```

### 7.2 校准模式UI

**流程：**
1. 用户点击"进入校准模式"
2. 提示：请在游戏中截图
3. 检测到新截图→显示游戏坐标
4. 用户在地图上点击对应位置
5. 添加校准点，显示在地图上
6. 重复步骤2-5，至少3个点
7. 计算变换矩阵，保存配置

## 8. 依赖库

```txt
customtkinter  # GUI框架
Pillow         # 图像处理
watchdog       # 文件系统监控
keyboard       # 全局快捷键
requests       # HTTP请求（IP地理位置）
numpy          # 数值计算（坐标变换）
```

## 9. 配置文件格式

**map_config.json:**
```json
{
  "maps": {
    "bigmap": {
      "map_id": "bigmap",
      "display_name": "Customs",
      "default_layer_id": 0,
      "layers": [
        {
          "layer_id": 0,
          "name": "Ground Floor",
          "image_path": "assets/maps/customs_ground.png",
          "height_min": -10.0,
          "height_max": 5.0,
          "calibration_points": [
            {
              "game_pos": {"x": 123.45, "y": 0.0, "z": -10.23},
              "map_x": 512.0,
              "map_y": 768.0,
              "timestamp": "2024-12-05T14:32:00"
            }
          ]
        }
      ]
    }
  },
  "floating_map": {
    "enabled": false,
    "width": 400,
    "height": 400,
    "pos_x": 100,
    "pos_y": 100,
    "opacity": 0.8,
    "locked": false,
    "hotkey": "F5"
  }
}
```

## 10. 已完成的模块

✅ **数据模型** - [modules/local_map/models.py](../modules/local_map/models.py)
- Position3D, Rotation, CalibrationPoint
- MapLayer, MapConfig
- PlayerPosition, RaidInfo
- CoordinateTransform, FloatingMapConfig

✅ **配置管理** - [modules/local_map/config_manager.py](../modules/local_map/config_manager.py)
- 配置文件加载/保存
- 地图图片管理
- 校准点管理
- 坐标变换计算

✅ **截图解析** - [modules/local_map/screenshot_parser.py](../modules/local_map/screenshot_parser.py)
- 文件名正则解析
- 坐标提取
- 旋转四元数转换

✅ **日志解析** - [modules/local_map/log_parser.py](../modules/local_map/log_parser.py)
- 日志文件监控
- 战局事件检测
- 服务器IP提取

## 11. 待实现的模块

⏳ **多点定位校准系统**
- 最小二乘法求解仿射变换
- 校准点UI交互
- 变换矩阵可视化验证

⏳ **地图渲染器**
- Canvas绘制地图
- 玩家位置标记
- 旋转方向箭头
- 缩放和平移

⏳ **浮动小地图窗口**
- TopLevel窗口创建
- 拖拽、缩放交互
- 透明度和锁定
- Windows API鼠标穿透

⏳ **服务器IP地理位置查询**
- IP-API集成
- 异步请求
- 结果缓存

⏳ **文件监控服务**
- Watchdog集成
- 截图实时检测
- 日志实时解析

## 12. 参考资料

- [TarkovMonitor GitHub](https://github.com/the-hideout/TarkovMonitor) - C#实现参考
- [Tarkov.dev](https://tarkov.dev) - 地图资源和API
- [Escape from Tarkov Forum - Server IPs](https://forum.escapefromtarkov.com/topic/101978-server-ips-posted/)
