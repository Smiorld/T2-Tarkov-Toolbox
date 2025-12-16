# T2 Tarkov Toolbox

**其它语言版本：[English](README.md) · [中文](README_zh.md)**

> 95% 通过 Claude AI 协助完成

一个集成多个实用工具的本地桌面应用，专为《逃离塔科夫》游戏玩家设计。

## 🎯 项目概述

T2 Tarkov Toolbox 是一个纯本地运行的多功能工具箱，提供屏幕滤镜和地图辅助等实用功能。

## ✨ 功能模块

### 1. 屏幕滤镜 ✅ 已实现

- 🎨 **实时屏幕滤镜** - 自定义亮度、伽马、对比度和RGB通道
- 🎯 **预设管理** - 内置默认、白天、夜间三个预设，支持自定义预设
- ⌨️ **全局快捷键** - F2/F3/F4快速切换预设
- 🖥️ **多显示器支持** - 可选择应用到特定显示器或全部显示器
- 💾 **配置持久化** - 预设自动保存到JSON文件

#### 参数调整

**亮度（Brightness）**: -100 到 100
- 正值增加亮度，负值降低亮度
- 默认值：0

**伽马（Gamma）**: 0.5 到 3.0
- <1.0 提亮暗部，>1.0 压暗亮部
- 默认值：1.0（行业标准：2.2）

**对比度（Contrast）**: -50 到 50
- 正值增强对比度，负值降低对比度
- 默认值：0

**RGB通道**: 0 到 255
- 独立调整红、绿、蓝通道的强度
- 默认值：255

#### 预设管理

1. **默认预设**（F2）: 标准显示设置
2. **白天预设**（F3）: 轻微增强对比度
3. **夜间预设**（F4）: 高亮度和伽马，适合暗环境

### 2. 本地地图 ✅ 已实现

- 📍 **实时位置追踪** - 通过解析游戏日志实时显示玩家位置和朝向
- 🗺️ **多地图支持** - 工厂、海关、森林、海岸线等主要地图
- 🏢 **多层级支持** - 地面、地下等多个楼层
- 🎯 **校准系统** - 3-10点校准，支持多种算法（最小二乘法、加权、RANSAC）
- 🖼️ **悬浮窗小地图**：
  - 可拖拽、调整大小
  - 透明度调整
  - 锁定/解锁模式
  - 滚轮缩放支持
  - 玩家居中模式
- 📊 **坐标转换** - 游戏坐标与地图像素坐标双向转换
- 💾 **状态持久化** - 自动保存悬浮窗位置、缩放级别等设置
- 🎨 **屏幕滤镜对冲** - 防止悬浮窗在使用屏幕滤镜时过曝

参考项目：[TarkovMonitor](https://github.com/CplJKUHN/TarkovMonitor)

### 3. 全局设置 ✅ 已实现

- ⚙️ **应用配置** - 路径设置、语言切换
- 💾 **配置管理** - 设置持久化存储

## 🛠️ 技术栈

### 核心框架
- **Python 3.11+**
- **CustomTkinter** - 现代化GUI框架

### Windows API
- **pywin32** - Windows GDI API（Gamma Ramp）

### 数据处理
- **Pillow** - 图像处理和缩放
- **NumPy** - 数值计算和图像处理

### 文件监控
- **watchdog** - 游戏日志文件监控

### 其他
- **keyboard** - 全局快捷键
- **screeninfo** - 多显示器信息获取

## 🚀 安装和运行

### 前置要求

- Python 3.11+
- Windows 操作系统（需要GDI API支持）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 首次配置

1. 复制示例配置文件:
```bash
copy config\app_config.example.json config\app_config.json
copy config\filter_config.example.json config\filter_config.json
```

2. 运行程序:
```bash
python main.py
```

3. 在"全局设置"标签页配置路径:
   - **截图路径**: 塔科夫截图文件夹路径
   - **日志路径**: 塔科夫日志文件夹路径

程序会尝试自动检测，也可以手动设置。

## 🏗️ 项目结构

```
T2-Tarkov-Toolbox/
├── modules/                # 功能模块
│   ├── screen_filter/      # 屏幕滤镜模块 ✅
│   │   ├── gamma_controller.py  # GDI gamma ramp控制
│   │   ├── models.py            # 数据模型
│   │   ├── state_manager.py     # 配置管理
│   │   ├── value_mapper.py      # 参数映射
│   │   └── ui.py                # UI界面
│   ├── local_map/          # 本地地图模块 ✅
│   │   ├── coordinate_transform.py  # 坐标转换算法
│   │   ├── log_parser.py            # 游戏日志解析
│   │   ├── map_canvas.py            # 地图渲染画布
│   │   ├── overlay_window.py        # 悬浮窗
│   │   ├── models.py                # 数据模型
│   │   ├── config_manager.py        # 配置管理
│   │   └── ui.py                    # UI界面
│   └── global_settings/    # 全局设置模块 ✅
│       └── ui.py
├── ui/                     # UI组件
│   └── main_window.py      # 主窗口（TabView）
├── utils/                  # 工具函数
├── locales/                # 国际化语言文件
├── config/                 # 配置文件目录
│   ├── app_config.example.json      # 应用配置示例
│   └── filter_config.example.json   # 滤镜配置示例
├── assets/                 # 资源文件
│   └── maps/              # 地图图片
├── docs/                   # 文档
├── main.py                # 程序入口
├── main.spec              # PyInstaller 打包配置
├── requirements.txt       # Python依赖
└── README.md             # 项目说明
```

## 🔧 技术原理

### Windows Gamma Ramp

程序通过Windows GDI API的`SetDeviceGammaRamp`函数控制显示器的颜色查找表（LUT）。

**关键算法**：
1. 对比度调整：调整斜率 `(base - 0.5) * (1 + contrast) + 0.5`
2. 伽马校正：幂函数 `value^(1/gamma)`
3. 亮度调整：乘法缩放 `value * (1 + brightness)`
4. 通道缩放：独立调整RGB `value * channel_scale`

每一步都确保值在 `[0, 1]` 范围内，防止产生平顶曲线（会被驱动拒绝）。

### 参数映射

UI显示的参数会自动映射到算法使用的真实值，确保所有UI值组合都安全可用：

| 参数 | UI范围 | 算法范围 | 说明 |
|------|--------|---------|------|
| 亮度 | -100到100 | -0.35到0.35 | 精细调节范围，步进1产生细微变化 |
| 伽马 | 0.5到3.0 | 0.5到3.0 | 直接映射，覆盖常用范围 |
| 对比度 | -50到50 | -0.3到0.3 | 精细调节范围，步进1产生细微变化 |
| RGB | 0到255 | 0.0到1.0 | 标准归一化 |

**实测校准说明**：
- 通过与业界参照滤镜软件对比调整，确保精细度和可控性
- 本软件 UI 亮度 37 ≈ 参照软件 UI 亮度 55 的效果
- 本软件 UI 对比度 4 ≈ 参照软件 UI 对比度 22 的效果
- 采用较小的算法范围（亮度 ±35%，对比度 ±30%），确保步进调节时变化细微、可控
- 每次步进调节产生约 0.0035（亮度）和 0.006（对比度）的算法变化

**参考标准**：
- FFmpeg eq filter: brightness ±1.0, contrast ±2.0, gamma 0.1-10.0
- Gamma Panel: gamma 0.3-4.4, brightness ±1.0, contrast 0.1-3.0
- NVIDIA Freestyle: 通常使用 ±40% 调整范围
- 本实现采用更小的范围以提供精细调节体验，避免单步变化过大

**核心特性**：
- ✅ **智能值映射**：UI范围映射到行业标准的安全算法范围
- ✅ **实时验证**：自动验证参数组合安全性
- ✅ **自动保护**：内部clamping机制防止数值溢出
- ✅ **全范围可用**：UI上的所有值都可以安全使用，不会导致驱动拒绝

## ⚠️ 注意事项

1. **管理员权限**: 某些显卡驱动可能需要管理员权限才能设置Gamma Ramp
2. **驱动兼容性**: 部分显卡驱动可能不支持或限制Gamma Ramp的调整范围
3. **自动保护**: 新的值映射系统会自动防止参数组合导致的问题

## 🐛 故障排查

### "无法为显示器设置 Gamma Ramp" 错误

**新版本已解决**：新的值映射系统已经自动防止此问题。所有UI值都经过验证，确保安全。

如果仍然遇到问题：
1. 确保使用最新版本的代码
2. 检查显卡驱动是否支持Gamma Ramp
3. 尝试以管理员权限运行程序
4. 使用内置预设（默认/白天/夜间）

## 📦 打包可执行文件

```bash
pyinstaller main.spec
```

生成的可执行文件在 `dist/` 文件夹中。

## 📝 开发状态

### ✅ 已实现功能

**屏幕滤镜模块**:
- [x] 多预设管理
- [x] 快捷键支持（F2/F3/F4）
- [x] 多显示器支持
- [x] 参数安全验证
- [x] 悬浮窗对冲功能

**本地地图模块**:
- [x] 实时位置追踪
- [x] 多地图/多层级支持
- [x] 校准系统（多种算法）
- [x] 悬浮窗小地图
- [x] 坐标转换系统

**全局设置模块**:
- [x] 路径配置
- [x] 语言切换（中文/English）

## 🎯 设计理念

1. **本地优先**: 所有功能应能离线工作
2. **轻量高效**: 低内存占用，不影响游戏性能
3. **用户友好**: 简洁直观的UI设计
4. **模块化**: 便于维护和扩展新功能

## 📄 许可证

本项目采用 GNU General Public License v3.0 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

**创作者：T2薯条（Smiorld）**
- [GitHub](https://github.com/Smiorld)
- [Bilibili](https://space.bilibili.com/2148654)
- [Douyin](https://v.douyin.com/01DEXWMY_nU/)

**灵感来源：**
- [每次一看见你](https://space.bilibili.com/5940215) - 屏幕滤镜概念
- [TarkovMonitor](https://github.com/CplJKUHN/TarkovMonitor) - 地图追踪方法
