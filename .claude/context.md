# T2 塔科夫工具箱 - 项目上下文

## 📋 项目概述

**项目名称**: T2-Tarkov-Toolbox  
**类型**: 纯本地桌面应用（单 .exe 文件）  
**开源**: 计划开源到 GitHub  
**目标用户**: 塔科夫玩家

## 🎯 核心功能

1. **屏幕滤镜设置**
   - 调整屏幕颜色/亮度/对比度
   - 透明置顶窗口
   - 自定义滤镜参数

2. **塔科夫战术地图**
   - 显示游戏地图
   - 自动识别玩家位置（通过截图）
   - 标记出生点、提取点、任务点

3. **塔科夫物价查询**
   - 查询物品当前价格
   - 24小时平均价格
   - 价格趋势
   - 商人收购价

4. **全局设置页面**
   - 应用配置
   - 截图文件夹路径
   - 快捷键设置

## 🛠️ 技术栈

### 前端
- **框架**: React 18 + TypeScript
- **UI 库**: Tailwind CSS + shadcn/ui
- **地图库**: Leaflet.js 或 React-Konva
- **状态管理**: Zustand
- **构建工具**: Vite

### 后端
- **语言**: Rust
- **框架**: Tauri 2.x
- **关键库**:
  - `reqwest` - HTTP 请求
  - `serde_json` - JSON 处理
  - `rusqlite` - SQLite 数据库
  - `exif` - 解析截图元数据
  - `notify` - 文件系统监控
  - `tokio` - 异步运行时

### 桌面
- **框架**: Tauri
- **打包**: electron-builder
- **最终产物**: 单个 .exe 文件（约 5-10MB）

## 🔌 外部 API 集成

### 1. Tarkov.dev GraphQL API ⭐⭐⭐⭐⭐

**API 端点**: `https://api.tarkov.dev/graphql`  
**认证**: 无需 Token，完全免费  
**用途**: 物价查询、物品信息、地图数据

**示例查询**:
```graphql
query {
  itemsByName(name: "Bitcoin") {
    name
    shortName
    avg24hPrice
    lastLowPrice
    changeLast48hPercent
    iconLink
    sellFor {
      vendor { name }
      price
    }
  }
}
```

**提供的数据**:
- 物品价格（跳蚤市场、商人）
- 24小时/7天平均价格
- 价格变化趋势
- 物品图标链接
- 任务物品信息
- 地图数据（出生点、提取点、任务点）
- 弹药、护甲数据

### 2. 截图位置识别技术

**原理**: 塔科夫游戏截图自带坐标信息（EXIF 元数据）

**实现方法**:
1. 监控截图文件夹: `Documents/Escape from Tarkov/Screenshots`
2. 检测新截图时读取 EXIF 数据
3. 提取坐标字段:
   - XPosition
   - YPosition
   - Rotation
   - MapName
4. 在地图上标记玩家位置

**参考项目**:
- TarkovMonitor (C#)
- TarkovMapTracker (Python)
- TarkovQuestie (Web)

## 🚀 开发路线

### Phase 1 - 基础框架（第1天）
- [x] 创建 Tauri + React 项目结构
- [ ] 配置 Rust 依赖
- [ ] 实现基础路由和页面框架
- [ ] 连接 Tarkov.dev API（测试物价查询）

### Phase 2 - 核心功能（第2-3天）
- [ ] 实现物价查询页面
- [ ] 实现截图监控和位置解析
- [ ] 集成地图展示
- [ ] 测试位置标记功能

### Phase 3 - 高级功能（第4-5天）
- [ ] 实现屏幕滤镜
- [ ] 添加设置页面
- [ ] 本地数据存储（SQLite）
- [ ] 快捷键支持

### Phase 4 - 打包发布（第6天）
- [ ] 打包测试
- [ ] 编写 README
- [ ] 准备开源

## 💡 关键设计决策

### 为什么选择 Tauri？
1. **打包体积小**: 5-10MB vs Electron 的 150MB+
2. **性能好**: Rust 后端 + 系统 WebView
3. **学习机会**: 可以学习 Rust + TypeScript
4. **真正的单 exe**: 无需额外进程

### 为什么不用 Python？
1. **无法练习前端技能**: 想学 TypeScript 和现代前端
2. **打包体积大**: PyQt 打包后 50-100MB
3. **UI 现代感不足**: 不如 React 组件生态

### 为什么不用 Python Sidecar？
1. **增加复杂度**: 需要管理两个进程
2. **打包更大**: +30-50MB
3. **Rust 足够**: 项目需求不复杂，Rust 完全能胜任

## 📚 学习资源

### Rust 学习重点
- 基础语法（变量、函数、结构体）
- 错误处理（Result 类型）
- 异步编程（async/await）
- Tauri Command（暴露给前端的函数）

### Tauri 学习重点
- IPC 通信（invoke）
- 窗口 API
- 文件系统访问
- 系统托盘

### 预计学习时间
- Rust 基础: 1-2 周上手
- Tauri 开发: 边做边学

## 🔧 开发环境

### 必需工具
- Node.js 18+
- Rust 1.70+
- pnpm (推荐) 或 npm
- VSCode + Tauri 扩展

### VSCode 扩展推荐
- rust-analyzer
- Tauri
- ES7+ React/Redux/React-Native snippets
- Tailwind CSS IntelliSense

## 📝 代码规范

### Rust
- 使用 `rustfmt` 格式化
- 使用 `clippy` 检查
- 详细的错误处理（不要 `.unwrap()`）
- 中文注释

### TypeScript
- ESLint + Prettier
- 严格模式
- 中文注释
- 组件命名: PascalCase
- 函数命名: camelCase

## 🐛 已知注意事项

1. **截图路径**: Windows 默认为 `C:\Users\<用户名>\Documents\Escape from Tarkov\Screenshots`
2. **EXIF 字段**: 需要测试确认塔科夫实际使用的字段名
3. **地图坐标系**: Tarkov.dev 使用的坐标系统可能需要转换
4. **跨平台**: 优先支持 Windows，macOS/Linux 后续考虑

## 🎓 项目学习目标

### 技能扩展
- ✅ Rust 基础编程
- ✅ TypeScript 前端开发
- ✅ Tauri 桌面应用开发
- ✅ GraphQL API 使用
- ✅ 图像元数据处理

### 项目经验
- ✅ 开源项目发布
- ✅ 桌面应用打包分发
- ✅ 技术文档编写
- ✅ 社区维护

## 📞 参考链接

- Tarkov.dev API: https://api.tarkov.dev/
- Tarkov.dev GitHub: https://github.com/the-hideout/tarkov-api
- TarkovMonitor: https://github.com/the-hideout/TarkovMonitor
- Tauri 文档: https://tauri.app/
- Rust 官方文档: https://doc.rust-lang.org/

---

**最后更新**: 2024-12-03
**当前阶段**: Phase 1 - 基础框架搭建
