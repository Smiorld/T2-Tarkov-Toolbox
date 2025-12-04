# 构建环境设置指南

## 问题诊断

当前编译失败的原因是缺少Windows C++ 构建工具。错误信息：

```
error: linking with `link.exe` failed: exit code: 1
note: link: extra operand 'D:\\tool\\projects\\...'
Try 'link --help' for more information.
```

这表明Rust编译器找到的是GNU的`link`命令而不是MSVC的链接器。

## 解决方案

### 方法1：安装 Visual Studio Build Tools（推荐）

1. 下载 **Visual Studio Build Tools**：
   - 访问：https://visualstudio.microsoft.com/downloads/
   - 滚动到底部，找到"Tools for Visual Studio"部分
   - 下载"Build Tools for Visual Studio 2022"

2. 运行安装程序，选择以下组件：
   - ✅ **Desktop development with C++** （C++桌面开发）
   - 在右侧"Installation details"中确保勾选：
     - ✅ MSVC v143 - VS 2022 C++ x64/x86 build tools
     - ✅ Windows 11 SDK (或 Windows 10 SDK)

3. 安装完成后，**重启计算机**

4. 重新运行构建：
   ```bash
   cd d:\tool\projects\T2-Tarkov-Toolbox
   npm run tauri dev
   ```

### 方法2：使用 GNU工具链（替代方案）

如果不想安装Visual Studio Build Tools，可以切换到GNU工具链：

1. 安装 MSYS2：https://www.msys2.org/
2. 在MSYS2中安装MinGW工具链
3. 切换Rust工具链：
   ```bash
   rustup default stable-x86_64-pc-windows-gnu
   ```

**注意**：推荐使用方法1（MSVC工具链），因为Tauri官方更好地支持MSVC。

## 验证安装

安装完成后，验证环境：

```bash
# 验证link.exe是否为MSVC版本
where link.exe
# 应该显示类似：C:\Program Files (x86)\Microsoft Visual Studio\...\link.exe

# 验证cl.exe（MSVC编译器）
where cl.exe
# 应该显示类似：C:\Program Files (x86)\Microsoft Visual Studio\...\cl.exe

# 验证Rust工具链
rustc --version --verbose
# 应该显示：host: x86_64-pc-windows-msvc
```

##当前项目状态

- ✅ Rust 已安装 (v1.91.1)
- ✅ Node.js 和 npm 已安装
- ✅ 项目依赖已配置
- ✅ Rust源代码编写完成
- ❌ **缺少MSVC构建工具** ← 当前需要解决

## 下一步

安装完MSVC Build Tools后，项目应该能够成功编译并启动Tauri桌面应用！
