# 快速启动指南

## 问题总结

当前无法编译的根本原因是：**Windows PATH环境中有多个`link.exe`冲突**

- Git自带的GNU `link`（`D:\tool\Git\usr\bin\link.exe`）
- MSVC的链接器`link.exe`（需要安装，Rust需要这个）

## 最简单的解决方案

### 选项A：安装 Visual Studio Build Tools（推荐，但需要~6GB空间）

1. 下载：https://visualstudio.microsoft.com/downloads/
2. 安装"Build Tools for Visual Studio 2022"
3. 选择"Desktop development with C++"
4. 安装后重启
5. 运行：`npm run tauri dev`

### 选项B：使用PowerShell运行（临时方案）

在PowerShell（非bash）中执行以下命令：

```powershell
cd d:\tool\projects\T2-Tarkov-Toolbox

# 临时移除Git路径
$env:PATH = $env:PATH -replace 'D:\\tool\\Git\\usr\\bin;','' -replace 'D:\\tool\\Git\\bin;',''

# 确认Rust工具链
rustc --version

# 运行开发服务器
npm run tauri dev
```

### 选项C：直接双击build.bat

1. 打开文件资源管理器
2. 进入项目目录：`d:\tool\projects\T2-Tarkov-Toolbox`
3. 双击 `build.bat` 文件
4. 等待编译完成

## 当前环境状态

✅ **已完成：**
- Rust安装成功 (v1.91.1)
- Node.js和npm正常
- 项目代码完整（Rust后端 + React前端）
- 依赖配置正确

❌ **待解决：**
- MSVC Build Tools未安装或PATH冲突

## 验证环境

在PowerShell中运行：

```powershell
# 检查MSVC链接器（应该找到MSVC的，而不是Git的）
where.exe link.exe

# 检查MSVC编译器
where.exe cl.exe

# 查看Rust工具链
rustc --version --verbose
```

## 项目已实现的功能

### Rust后端
- ✅ Windows Gamma Ramp API封装
- ✅ 滤镜配置管理（亮度、伽马、对比度、RGB三通道）
- ✅ 预设管理系统（CRUD操作）
- ✅ 三个默认预设：默认(F2)、白天(F3)、夜间(F4)
- ✅ 配置持久化（.exe/config/filter_presets.json）
- ✅ 12个Tauri命令接口

### React前端
- ✅ 屏幕滤镜页面UI
  - 预设列表（左侧）
  - 配置调节面板（右侧，6个滑块）
  - 预设操作（新建、重命名、删除、应用）
- ✅ TypeScript类型定义
- ✅ Tauri API封装

### 待实现功能
- ⏳ 全局快捷键系统
- ⏳ 导入/导出UI
- ⏳ 战术地图
- ⏳ 任务追踪器
- ⏳ 设置页面

## 预期结果

成功运行后，你将看到：
1. Tauri桌面应用窗口打开
2. 顶部导航栏：首页、屏幕滤镜、战术地图、任务追踪、设置
3. 点击"屏幕滤镜"可以看到完整的滤镜管理界面

## 需要帮助？

如果仍然无法编译，请确认：
1. 是否安装了Visual Studio Build Tools？
2. 是否在PowerShell（而非bash）中运行？
3. PATH中是否有MSVC的link.exe？

可以将错误信息截图或复制给我，我会继续帮你解决！
