# T2 塔科夫工具箱 - 项目文件清单

## 📦 已创建的文件

### 📄 文档文件（重要！先读这些）

1. **README.md** - 项目总览和使用说明
2. **GETTING_STARTED.md** - 快速开始指南（⭐ 从这里开始！）
3. **.claude/context.md** - 完整的项目上下文和技术决策
4. **docs/API_GUIDE.md** - Tarkov.dev API 详细使用指南（含完整代码示例）
5. **docs/SCREENSHOT_GUIDE.md** - 截图位置识别技术说明

### ⚙️ 配置文件

6. **package.json** - 前端依赖和脚本
7. **tsconfig.json** - TypeScript 配置
8. **tsconfig.node.json** - Node 环境 TS 配置
9. **vite.config.ts** - Vite 构建配置
10. **tailwind.config.js** - Tailwind CSS 配置
11. **postcss.config.js** - PostCSS 配置
12. **.gitignore** - Git 忽略规则

### 🦀 Rust 后端文件

13. **src-tauri/Cargo.toml** - Rust 依赖配置
14. **src-tauri/tauri.conf.json** - Tauri 应用配置
15. **src-tauri/build.rs** - 构建脚本
16. **src-tauri/src/main.rs** - Rust 入口（带详细中文注释）
17. **src-tauri/src/commands/mod.rs** - 命令模块入口

### ⚛️ React 前端文件

18. **index.html** - HTML 入口
19. **src/main.tsx** - React 入口
20. **src/App.tsx** - 主应用组件（含路由和侧边栏）
21. **src/styles.css** - 全局样式
22. **src/pages/Home.tsx** - 首页组件

### 📁 目录结构

```
T2-Tarkov-Toolbox/
├── .claude/                    # ⭐ Claude AI 上下文
│   └── context.md             # 项目完整背景
├── docs/                       # ⭐ 技术文档（重要参考）
│   ├── API_GUIDE.md           # API 使用（含代码）
│   └── SCREENSHOT_GUIDE.md    # 截图解析技术
├── src-tauri/                 # Rust 后端
│   ├── src/
│   │   ├── main.rs           # 已注释，可直接运行
│   │   └── commands/         # 命令模块（待扩展）
│   ├── Cargo.toml
│   └── tauri.conf.json
├── src/                       # React 前端
│   ├── pages/
│   │   └── Home.tsx          # 已完成
│   ├── components/           # 空（待添加）
│   ├── hooks/                # 空（待添加）
│   ├── App.tsx               # 已完成（路由+侧边栏）
│   ├── main.tsx
│   └── styles.css
├── public/                    # 静态资源
│   └── maps/                 # 地图图片（待添加）
├── README.md                  # 项目说明
├── GETTING_STARTED.md         # ⭐ 快速开始（必读！）
├── package.json
├── vite.config.ts
└── .gitignore
```

## 🎯 当前状态

### ✅ 已完成
- [x] 项目基础结构搭建
- [x] Tauri + React 配置
- [x] 路由和导航
- [x] 测试命令（greet）
- [x] 完整的技术文档
- [x] 代码示例和模板

### 🚧 待实现（按优先级）
1. **物价查询功能** - 最简单，建议先做
   - 参考: `docs/API_GUIDE.md`
   - 需要创建: `src-tauri/src/commands/price.rs`
   - 需要创建: `src/pages/PriceChecker.tsx`
   - 需要创建: `src/hooks/useTarkovAPI.ts`

2. **截图位置识别**
   - 参考: `docs/SCREENSHOT_GUIDE.md`
   - 需要创建: `src-tauri/src/commands/screenshot.rs`
   - 需要创建: `src/pages/TarkovMap.tsx`

3. **屏幕滤镜**
   - 需要创建: `src/pages/ScreenFilter.tsx`

4. **设置页面**
   - 需要创建: `src/pages/Settings.tsx`

## 🚀 下一步操作

### 1. 解压项目到本地

```bash
# Windows
tar -xzf T2-Tarkov-Toolbox.tar.gz

# 或者直接解压 zip（如果你用 Windows 资源管理器）
```

### 2. 用 VSCode 打开

```bash
cd T2-Tarkov-Toolbox
code .
```

### 3. 阅读快速开始指南

打开 `GETTING_STARTED.md`，按照步骤操作。

### 4. 安装依赖并运行

```bash
pnpm install
pnpm tauri dev
```

### 5. 验证连接

在应用中测试 Tauri 通信是否正常。

### 6. 开始开发第一个功能

建议从 **物价查询** 开始（最简单）。

## 📚 重要提示

1. **所有代码都有详细注释** - 特别是 Rust 部分
2. **文档很全** - `docs/` 目录有完整的实现指南
3. **可以边学边做** - 遇到 Rust 语法问题直接问 Claude
4. **.claude/context.md 很重要** - 包含完整的技术决策和背景

## 💡 开发建议

- 优先实现**物价查询**（验证技术栈可行性）
- 然后做**截图识别**（需要实际截图测试）
- 最后做**屏幕滤镜**和**设置**

## 🐛 遇到问题？

1. 查看 `GETTING_STARTED.md` 的故障排除
2. 查看相关的 `docs/*.md` 文档
3. 问 Claude（把错误信息完整复制过来）

## 🎉 准备好了！

现在你有了一个完整的项目结构和详细的文档。解压到本地，打开 VSCode，开始编码吧！

**Good luck! 🚀**
