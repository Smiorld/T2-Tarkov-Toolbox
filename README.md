# T2 塔科夫工具箱

一个纯本地运行的《逃离塔科夫》辅助工具桌面应用，提供屏幕滤镜、战术地图、物价查询等功能。

## ✨ 功能特性

- 🎨 **屏幕滤镜** - 自定义屏幕颜色、亮度、对比度
- 🗺️ **战术地图** - 自动识别位置（通过截图EXIF数据），显示出生点、提取点、任务点
- 💰 **物价查询** - 实时查询物品价格、24h平均价、商人收购价
- ⚙️ **全局设置** - 配置应用参数、截图路径、快捷键

## 🛠️ 技术栈

### 前端
- React 18 + TypeScript
- Tailwind CSS
- React Router
- Zustand (状态管理)

### 后端
- Rust
- Tauri 2.0
- reqwest (HTTP 客户端)
- exif (图片元数据解析)
- notify (文件系统监控)
- rusqlite (本地数据库)

### 外部 API
- [Tarkov.dev GraphQL API](https://api.tarkov.dev/) - 物价、物品、地图数据

## 🚀 开发环境配置

### 前置要求

- Node.js 18+ 
- Rust 1.70+
- pnpm (推荐) 或 npm

### 安装依赖

```bash
# 安装前端依赖
pnpm install

# Rust 依赖会在构建时自动安装
```

### 开发模式运行

```bash
# 启动开发服务器（前端热重载 + Rust 编译）
pnpm tauri dev
```

### 构建生产版本

```bash
# 构建 Windows .exe
pnpm tauri build
```

构建产物位于 `src-tauri/target/release/bundle/`

## 📖 项目结构

```
T2-Tarkov-Toolbox/
├── .claude/                # Claude AI 上下文文档
├── docs/                   # 详细技术文档
│   ├── API_GUIDE.md       # Tarkov.dev API 使用指南
│   └── SCREENSHOT_GUIDE.md # 截图解析技术说明
├── src-tauri/             # Rust 后端
│   ├── src/
│   │   ├── main.rs        # 入口文件
│   │   └── commands/      # Tauri 命令
│   ├── Cargo.toml         # Rust 依赖
│   └── tauri.conf.json    # Tauri 配置
├── src/                   # React 前端
│   ├── pages/             # 页面组件
│   ├── components/        # 可复用组件
│   ├── hooks/             # 自定义 Hooks
│   ├── App.tsx
│   └── main.tsx
├── public/                # 静态资源
└── package.json
```

## 🎓 开发指南

### 添加新的 Tauri 命令

1. 在 `src-tauri/src/commands/` 创建新模块
2. 实现命令函数（加上 `#[tauri::command]` 宏）
3. 在 `main.rs` 中注册命令
4. 前端通过 `invoke('command_name', { args })` 调用

示例：

```rust
// src-tauri/src/commands/example.rs
#[tauri::command]
pub fn hello(name: String) -> String {
    format!("Hello, {}!", name)
}
```

```typescript
// src/pages/Example.tsx
import { invoke } from '@tauri-apps/api/tauri';

const result = await invoke<string>('hello', { name: 'World' });
```

### 调试技巧

- 前端: 打开 DevTools（开发模式自动启用）
- Rust: 使用 `println!()` 或 `eprintln!()` 输出到控制台
- 查看 Tauri 日志: `pnpm tauri dev --verbose`

## 📚 参考资源

- [Tauri 官方文档](https://tauri.app/)
- [Tarkov.dev API 文档](https://api.tarkov.dev/)
- [Rust 官方文档](https://doc.rust-lang.org/)

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License

## 🙏 致谢

- [Tarkov.dev](https://tarkov.dev/) - 提供免费的塔科夫数据 API
- [TarkovMonitor](https://github.com/the-hideout/TarkovMonitor) - 截图解析技术参考

---

**注意**: 本工具仅用于个人学习和辅助游戏体验，不涉及任何作弊行为。请遵守游戏服务条款。
