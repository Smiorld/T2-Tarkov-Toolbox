# T2 Tarkov Toolbox

**Other Languages: [English](README.md) · [中文](README_zh.md)**

> 95% built with Claude AI assistance

A local desktop toolbox for Escape from Tarkov players, featuring advanced screen filters and tactical map overlay.

## ✨ Features

### 1. Screen Filter
- Real-time screen adjustment (brightness, gamma, contrast, RGB channels)
- Preset management with global hotkeys (F2/F3/F4)
- Multi-monitor support
- Configuration persistence

### 2. Local Tactical Map
- Real-time position tracking via game log parsing
- Multi-map and multi-floor support
- Advanced calibration system (3-10 points, multiple algorithms)
- Draggable overlay window with transparency control
- Zoom and center-on-player modes
- Screen filter compensation for overlay

## 🚀 Installation

### Requirements
- Python 3.11+
- Windows OS (requires GDI API support)

### Setup
1. Clone the repository
```bash
git clone https://github.com/Smiorld/T2-Tarkov-Toolbox.git
cd T2-Tarkov-Toolbox
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Copy example configuration files
```bash
copy config\app_config.example.json config\app_config.json
copy config\filter_config.example.json config\filter_config.json
```

4. Run the application
```bash
python main.py
```

## ⚙️ Configuration

On first run, configure paths in the **Global Settings** tab:
- **Screenshots Path**: Path to Tarkov screenshots folder
- **Logs Path**: Path to Tarkov logs folder

The app will attempt auto-detection, or you can set paths manually.

## 🛠️ Tech Stack

- **Python 3.11+** & **CustomTkinter** - Modern GUI framework
- **pywin32** - Windows GDI API for gamma ramp control
- **Pillow** & **NumPy** - Image processing and manipulation
- **watchdog** - Game log file monitoring
- **keyboard** - Global hotkey support
- **screeninfo** - Multi-monitor detection

## 📦 Building Executable

```bash
pyinstaller main.spec
```

The executable will be generated in the `dist/` folder.

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

**Created by T2薯条 (Smiorld)**
- [GitHub](https://github.com/Smiorld)
- [Bilibili](https://space.bilibili.com/2148654)
- [Douyin](https://v.douyin.com/01DEXWMY_nU/)

**Inspired by:**
- [每次一看见你](https://space.bilibili.com/5940215) - Original screen filter concept
- [TarkovMonitor](https://github.com/CplJKUHN/TarkovMonitor) - Map tracking approach
