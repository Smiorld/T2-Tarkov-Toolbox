# T2 Tarkov Toolbox - Screen Filter

一个纯本地运行的Windows屏幕滤镜工具，提供自定义屏幕颜色、亮度、对比度和伽马调整。

## ✨ 功能特性

- 🎨 **实时屏幕滤镜** - 自定义亮度、伽马、对比度和RGB通道
- 🎯 **预设管理** - 内置默认、白天、夜间三个预设，支持自定义预设
- ⌨️ **全局快捷键** - F2/F3/F4快速切换预设
- 🖥️ **多显示器支持** - 可选择应用到特定显示器或全部显示器
- 💾 **配置持久化** - 预设自动保存到JSON文件

## 🛠️ 技术栈

- **Python 3.11+**
- **CustomTkinter** - 现代化的Tkinter GUI框架
- **pywin32** - Windows API调用（SetDeviceGammaRamp）
- **keyboard** - 全局快捷键监听

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

## 📖 使用说明

### 参数调整

**亮度（Brightness）**: -100 到 100
- 正值增加亮度，负值降低亮度
- 默认值：0

**伽马（Gamma）**: 0.5 到 3.5
- <1.0 提亮暗部，>1.0 压暗亮部
- 默认值：1.0

**对比度（Contrast）**: -50 到 50
- 正值增强对比度，负值降低对比度
- 默认值：0

**RGB通道**: 0.5 到 2.0
- 独立调整红、绿、蓝通道的强度
- 默认值：1.0

### 预设管理

1. **默认预设**（F2）: 标准显示设置
2. **白天预设**（F3）: 轻微增强对比度
3. **夜间预设**（F4）: 高亮度和伽马，适合暗环境

### 快捷键

- `F2` - 应用默认预设
- `F3` - 应用白天预设
- `F4` - 应用夜间预设

## 🏗️ 项目结构

```
T2-Tarkov-Toolbox/
├── main.py              # 主程序入口（CustomTkinter GUI）
├── gamma_controller.py  # Windows Gamma Ramp控制器
├── models.py            # 数据模型定义
├── preset_manager.py    # 预设管理器
├── probe_limits.py      # 参数限制探测工具
├── requirements.txt     # Python依赖
└── filter_presets.json  # 预设配置文件（自动生成）
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

UI显示的参数会自动映射到算法使用的真实值：

| 参数 | UI范围 | 算法范围 | 映射公式 |
|------|--------|---------|---------|
| 亮度 | -100到100 | -1.0到1.0 | `brightness / 100` |
| 伽马 | 0.5到3.5 | 0.5到3.5 | 直接使用 |
| 对比度 | -50到50 | -0.5到0.5 | `contrast / 100` |

## ⚠️ 注意事项

1. **管理员权限**: 某些显卡驱动可能需要管理员权限才能设置Gamma Ramp
2. **驱动兼容性**: 部分显卡驱动可能不支持或限制Gamma Ramp的调整范围
3. **参数限制**: 过高的参数组合可能导致曲线饱和，建议使用预设值

## 🐛 故障排查

### "无法为显示器设置 Gamma Ramp" 错误

**原因**：参数组合导致Gamma曲线在中间值就达到最大值（平顶曲线），被驱动拒绝。

**解决方案**：
- 降低亮度值
- 使用内置预设
- 运行 `probe_limits.py` 探测你的显卡支持的最大参数值

## 📝 开发计划

- [ ] 添加曲线预览图表
- [ ] 支持导入/导出预设
- [ ] 添加定时任务（自动切换预设）
- [ ] 支持每个显示器独立配置

## 📄 许可证

MIT License

## 🙏 致谢

- Windows GDI API文档
- CustomTkinter框架
