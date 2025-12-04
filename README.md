# T2 Tarkov Toolbox

一个集成多个实用工具的本地桌面应用，专为《逃离塔科夫》游戏玩家设计。

## 🎯 项目概述

T2 Tarkov Toolbox 是一个纯本地运行的多功能工具箱，提供屏幕滤镜、地图辅助和任务追踪等实用功能。

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

### 2. 本地地图 📋 计划中

- 📸 **截图监控** - 自动监控游戏截图文件夹
- 📍 **位置显示** - 读取EXIF数据在地图上显示玩家位置
- 🗺️ **地图标记** - 显示出生点、提取点、任务点、战利品点
- 🎨 **自定义标记** - 支持自定义标记和注释

参考项目：[TarkovMonitor](https://github.com/CplJKUHN/TarkovMonitor)

### 3. 任务追踪 📋 计划中

- 📋 **任务列表** - 显示所有任务（按商人分组）
- ✅ **进度追踪** - 标记任务完成状态
- ☁️ **云端同步** - 通过TarkovTracker.org API同步进度
- 💾 **本地模式** - 支持纯本地追踪（无需联网）

**API集成**：
- Tarkov.dev GraphQL API - 获取任务数据
- TarkovTracker.org API - 云端同步（可选）

## 🛠️ 技术栈

### 核心框架
- **Python 3.11+**
- **CustomTkinter** - 现代化GUI框架

### Windows API
- **pywin32** - Windows GDI API（Gamma Ramp）

### 数据处理
- **Pillow** - 图像处理和EXIF读取（计划中）
- **sqlite3** - 本地数据库（计划中）

### 网络请求
- **requests** - HTTP客户端（计划中）

### 文件监控
- **watchdog** - 文件系统事件监控（计划中）

### 其他
- **keyboard** - 全局快捷键

## 🚀 安装和运行

### 前置要求

- Python 3.11+
- Windows 操作系统（需要GDI API支持）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行程序

```bash
python main.py
```

## 🏗️ 项目结构

```
T2-Tarkov-Toolbox/
├── .claude/                # Claude Code配置
├── modules/                # 功能模块
│   ├── screen_filter/      # 屏幕滤镜模块 ✅
│   │   ├── __init__.py
│   │   ├── gamma_controller.py
│   │   ├── models.py
│   │   ├── preset_manager.py
│   │   └── ui.py
│   ├── local_map/          # 本地地图模块 📋
│   │   ├── __init__.py
│   │   └── ui.py
│   └── quest_tracker/      # 任务追踪模块 📋
│       ├── __init__.py
│       └── ui.py
├── core/                   # 核心组件
│   └── __init__.py
├── ui/                     # UI组件
│   ├── __init__.py
│   ├── main_window.py      # 主窗口（TabView）
│   └── components/         # 通用UI组件
├── assets/                 # 资源文件
│   ├── maps/              # 地图图片
│   └── icons/             # 图标
├── data/                   # 数据文件
├── main.py                # 程序入口
├── requirements.txt       # Python依赖
├── README.md             # 项目说明
└── PROJECT_ARCHITECTURE.md # 架构规划
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
| 亮度 | -100到100 | -0.5到0.5 | 基于FFmpeg标准（±1.0范围内） |
| 伽马 | 0.5到3.0 | 0.5到3.0 | 基于Gamma Panel标准 |
| 对比度 | -50到50 | -0.5到0.5 | 基于业界最佳实践 |
| RGB | 0到255 | 0.0到1.0 | 标准归一化 |

**参考标准**：
- FFmpeg eq filter: brightness ±1.0, contrast ±2.0
- Gamma Panel: gamma 0.3-4.4, brightness ±1.0
- NVIDIA Freestyle: 通常使用 ±40% 调整范围
- 本实现采用保守范围，确保兼容性和稳定性

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

**新版本已解决**：新的值映射系统（v2.0）已经自动防止此问题。所有UI值都经过验证，确保安全。

如果仍然遇到问题：
1. 确保使用最新版本的代码
2. 检查显卡驱动是否支持Gamma Ramp
3. 尝试以管理员权限运行程序
4. 使用内置预设（默认/白天/夜间）

## 📝 开发计划

### Phase 1: 架构重构 ✅ 已完成
- [x] 重构屏幕滤镜代码到模块化结构
- [x] 实现主窗口TabView框架
- [x] 迁移屏幕滤镜到第一个Tab

### Phase 2: 地图模块 📋 待实现
- [ ] 实现截图文件夹监控
- [ ] EXIF数据解析
- [ ] 地图渲染引擎
- [ ] 标记系统

### Phase 3: 任务追踪模块 📋 待实现
- [ ] Tarkov.dev API集成
- [ ] 本地数据库设计
- [ ] 任务列表UI
- [ ] TarkovTracker云端同步（可选）

### Phase 4: 优化和扩展
- [ ] 添加曲线预览图表
- [ ] 支持导入/导出预设
- [ ] 性能优化
- [ ] 用户反馈收集

## 🎯 设计理念

1. **本地优先**: 所有功能应能离线工作
2. **轻量高效**: 低内存占用，不影响游戏性能
3. **用户友好**: 简洁直观的UI设计
4. **模块化**: 便于维护和扩展新功能

## 📄 许可证

MIT License

## 🙏 致谢

- Windows GDI API文档
- CustomTkinter框架
- TarkovMonitor项目
- Tarkov.dev API
