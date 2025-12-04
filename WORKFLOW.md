# T2 塔科夫工具箱 - 开发与发布工作流

## 📝 快速参考

### 🛠️ 开发调试（Development & Debug）

#### 方式 1: 带管理员权限开发（推荐用于测试滤镜功能）
```bash
双击运行: dev-admin.bat
```
- ✅ 自动请求管理员权限
- ✅ 热重载（修改代码自动刷新）
- ✅ 滤镜功能可正常工作
- ✅ 实时查看 console 日志

#### 方式 2: 普通权限开发（UI 开发推荐）
```bash
双击运行: dev-normal.bat
```
- ✅ 热重载
- ✅ 快速启动
- ⚠️ 滤镜功能会提示权限错误（正常）
- 💡 适合开发 UI、非滤镜功能

---

### 📦 生成发布版本（Release Build）

#### 选项 1: 便携版（绿色版，推荐分享）
```bash
双击运行: build-portable.bat
```

**输出：** `release-portable/` 文件夹
- `t2-tarkov-toolbox.exe` - 主程序
- `启动(管理员).vbs` - 双击自动请求管理员权限
- `config/` - 配置文件夹
- `使用说明.txt` - 使用说明

**特点：**
- ✅ 解压即用，无需安装
- ✅ 可直接打包成 zip 分享
- ✅ 包含自动管理员启动器
- 💾 体积小（约 5-10MB）

---

#### 选项 2: 安装包版（Windows Installer）
```bash
双击运行: build-installer.bat
```

**输出：** `src-tauri/target/release/bundle/nsis/*.exe`
- Windows 安装程序（.exe）
- 安装到 Program Files
- 自动创建开始菜单快捷方式
- 支持卸载

**特点：**
- ✅ 专业的安装体验
- ✅ 自动添加到系统
- ⚠️ 需要用户安装权限
- 💾 体积稍大（包含安装程序）

---

#### 选项 3: 快速构建（仅 exe）
```bash
双击运行: build-release.bat
```

**输出：** `src-tauri/target/release/t2-tarkov-toolbox.exe`
- 只生成单个 exe 文件
- 最快的构建方式
- 需要手动创建启动器

---

## 🎯 使用场景推荐

| 场景 | 推荐方式 | 说明 |
|------|----------|------|
| 日常开发 UI | `dev-normal.bat` | 快速启动，热重载 |
| 开发/测试滤镜功能 | `dev-admin.bat` | 管理员权限 + 热重载 |
| 给朋友分享 | `build-portable.bat` | 打包成 zip，解压即用 |
| 正式发布 | `build-installer.bat` | 专业安装包 |
| 快速测试打包 | `build-release.bat` | 最快构建 |

---

## 🔧 构建要求

### 必需环境
- ✅ Node.js (已安装)
- ✅ Rust (已安装)
- ✅ Visual Studio 2022 Build Tools (已安装)

### 第一次构建
第一次运行任何构建脚本时，会下载依赖，可能需要 5-10 分钟。
后续构建会快很多（1-2 分钟）。

---

## 📁 输出文件位置

```
项目根目录/
├── release-portable/          # 便携版输出
│   ├── t2-tarkov-toolbox.exe
│   ├── 启动(管理员).vbs
│   ├── config/
│   └── 使用说明.txt
│
├── src-tauri/target/release/
│   ├── t2-tarkov-toolbox.exe  # 独立可执行文件
│   └── bundle/nsis/           # 安装包
│       └── *.exe
```

---

## 🐛 常见问题

### Q: 构建失败 "link.exe not found"
A: 运行脚本会自动设置 MSVC 环境，如果仍然失败，重启电脑后重试。

### Q: 滤镜功能提示权限错误
A: 使用 `dev-admin.bat` 或右键"以管理员身份运行"。

### Q: 构建很慢
A: 第一次构建需要下载和编译依赖。清理缓存：
```bash
cd src-tauri
cargo clean
```

### Q: 想清理所有构建产物
A: 删除以下文件夹：
- `src-tauri/target/`
- `dist/`
- `release-portable/`

---

## 🚀 快速测试流程

1. **开发新功能**
   ```bash
   dev-admin.bat  # 启动开发服务器
   # 修改代码，保存后自动刷新
   ```

2. **测试构建**
   ```bash
   build-portable.bat  # 生成便携版
   # 测试 release-portable/启动(管理员).vbs
   ```

3. **发布分享**
   ```bash
   # 压缩 release-portable/ 文件夹
   # 分享给用户
   ```

---

## 📊 版本管理

当前版本：**0.1.0**

修改版本号位置：
- `src-tauri/Cargo.toml` - `version = "0.1.0"`
- `src-tauri/tauri.conf.json` - `"version": "0.1.0"`
- `package.json` - `"version": "0.1.0"`

---

## 💡 提示

- 开发时优先使用 `dev-admin.bat`，可以实时看到效果
- 每次重大修改后，用 `build-portable.bat` 测试完整打包
- 发布前，用 `build-installer.bat` 生成正式安装包
- 所有脚本都会自动设置编译环境，直接双击即可

---

最后更新：2025-12-03
