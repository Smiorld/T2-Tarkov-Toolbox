# T2 Tarkov Toolbox

**其它语言版本：[English](README.md) · [中文](README_zh.md)**

> 95% 由 Claude AI 协助完成

一个为《逃离塔科夫》玩家打造的本地桌面工具箱，提供高级屏幕滤镜和战术地图覆盖功能。

## ✨ 功能特性

### 1. 屏幕滤镜
- 实时屏幕调整（亮度、伽马、对比度、RGB 通道）
- 预设管理，支持全局快捷键（F2/F3/F4）
- 多显示器支持
- 配置持久化

### 2. 本地战术地图
- 通过游戏日志解析实现实时位置追踪
- 多地图和多楼层支持
- 高级校准系统（3-10 点，多种算法）
- 可拖拽的悬浮窗，支持透明度控制
- 缩放和玩家居中模式
- 屏幕滤镜补偿功能

## 🚀 安装

### 系统要求
- Python 3.11+
- Windows 操作系统（需要 GDI API 支持）

### 安装步骤
1. 克隆仓库
```bash
git clone https://github.com/Smiorld/T2-Tarkov-Toolbox.git
cd T2-Tarkov-Toolbox
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 复制示例配置文件
```bash
copy config\app_config.example.json config\app_config.json
copy config\filter_config.example.json config\filter_config.json
```

4. 运行应用
```bash
python main.py
```

## ⚙️ 配置

首次运行时，在**全局设置**标签页中配置路径：
- **截图路径**：塔科夫截图文件夹路径
- **日志路径**：塔科夫日志文件夹路径

应用会尝试自动检测，也可以手动设置。

## 🛠️ 技术栈

- **Python 3.11+** & **CustomTkinter** - 现代化 GUI 框架
- **pywin32** - Windows GDI API，用于 gamma ramp 控制
- **Pillow** & **NumPy** - 图像处理和操作
- **watchdog** - 游戏日志文件监控
- **keyboard** - 全局快捷键支持
- **screeninfo** - 多显示器检测

## 📦 打包可执行文件

```bash
pyinstaller main.spec
```

可执行文件将生成在 `dist/` 文件夹中。

## 📄 许可证

本项目采用 GNU General Public License v3.0 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

**作者：T2薯条 (Smiorld)**
- [GitHub](https://github.com/Smiorld)
- [Bilibili](https://space.bilibili.com/2148654)
- [Douyin](https://v.douyin.com/01DEXWMY_nU/)

**灵感来源：**
- [每次一看见你](https://space.bilibili.com/5940215) - 屏幕滤镜概念
- [TarkovMonitor](https://github.com/CplJKUHN/TarkovMonitor) - 地图追踪方法
