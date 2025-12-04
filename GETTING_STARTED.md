# 快速开始指南

## 🚀 立刻开始开发

### 1. 环境检查

确保已安装：
- Node.js 18+ (`node --version`)
- Rust 1.70+ (`rustc --version`)
- pnpm (`pnpm --version`) 或 npm

### 2. 安装依赖

```bash
cd T2-Tarkov-Toolbox

# 安装前端依赖
pnpm install

# Rust 依赖会在第一次运行时自动安装
```

### 3. 启动开发服务器

```bash
# 这会同时启动 Vite 开发服务器和 Tauri
pnpm tauri dev
```

第一次运行会较慢（Rust 编译），之后就快了。

### 4. 验证连接

1. 应用窗口打开后，在侧边栏的测试区域输入名字
2. 点击"测试"按钮
3. 如果看到绿色的问候消息，说明 Tauri 通信正常！

## 📝 下一步：实现第一个功能

### 选项 A：物价查询（推荐从这里开始）

**为什么先做这个？**
- 最简单
- 只需要 HTTP 请求
- 可以快速验证 Rust + React 通信
- 有现成的 API

**实现步骤：**

1. **创建 Rust 命令**

```bash
# 创建文件
touch src-tauri/src/commands/price.rs
```

复制 `docs/API_GUIDE.md` 中的 Rust 代码到 `price.rs`

2. **在 main.rs 中注册**

取消注释这两行：
```rust
mod commands;
commands::price::get_item_price,
```

3. **创建前端页面**

```bash
# 创建文件
touch src/pages/PriceChecker.tsx
```

复制 `docs/API_GUIDE.md` 中的 React 代码

4. **启用路由**

在 `App.tsx` 中取消注释：
```tsx
import PriceChecker from './pages/PriceChecker';
<Route path="/price" element={<PriceChecker />} />
```

5. **测试**

- 重启 `pnpm tauri dev`
- 点击侧边栏"💰 物价查询"
- 输入 "Bitcoin" 查询

### 选项 B：截图位置识别

需要先获取一张塔科夫截图样本来测试 EXIF 字段。

参考 `docs/SCREENSHOT_GUIDE.md` 实现。

### 选项 C：屏幕滤镜

最简单的视觉效果，可以快速看到成果。

## 🐛 遇到问题？

### Rust 编译错误

```bash
# 清理并重新构建
cd src-tauri
cargo clean
cargo build
```

### 前端依赖问题

```bash
# 删除 node_modules 重装
rm -rf node_modules
pnpm install
```

### Tauri 启动失败

检查 `src-tauri/tauri.conf.json` 中的端口是否被占用：
- devUrl: `http://localhost:1420`
- 可以改成其他端口

## 📖 学习资源

### Rust 速成（针对这个项目）

你需要了解：
1. 基础语法（变量、函数）
2. `Result<T, E>` 错误处理
3. `async/await` 异步
4. `#[tauri::command]` 宏

推荐：边写边学，遇到不懂的语法就问 Claude！

### 调试技巧

**前端调试：**
- 打开 Chrome DevTools
- Console 查看日志
- Network 查看请求

**Rust 调试：**
```rust
println!("Debug: {:?}", some_variable);
eprintln!("Error: {}", error);
```

**查看详细日志：**
```bash
pnpm tauri dev --verbose
```

## 🎯 开发优先级建议

**第 1 天：**
- ✅ 搭建项目（已完成）
- [ ] 实现物价查询（最简单）
- [ ] 测试 Tauri 通信

**第 2-3 天：**
- [ ] 获取塔科夫截图样本
- [ ] 实现 EXIF 解析
- [ ] 测试位置识别

**第 4-5 天：**
- [ ] 集成地图展示
- [ ] 实现屏幕滤镜
- [ ] 完善设置页面

**第 6 天：**
- [ ] 打包测试
- [ ] 编写文档
- [ ] 准备开源

## 💡 提示

- **不要追求完美**：先实现核心功能，再优化
- **一次只做一件事**：专注当前功能，不要分心
- **多用 Claude**：遇到 Rust 错误直接问，会给你详细解释
- **查看示例代码**：`docs/` 目录有完整的代码示例

## 🎉 开始编码吧！

现在你已经准备好了。打开 VSCode，运行 `pnpm tauri dev`，开始构建你的第一个 Tauri 应用！

有问题随时问 Claude！🚀
