# Claude Code 基础设施

本目录包含从 [claude-code-infrastructure-showcase](https://github.com/diet103/claude-code-infrastructure-showcase) 整合的生产级 Claude Code 基础设施。

## 📁 目录结构

```
.claude/
├── README.md                      # 本文档
├── COLLABORATION_GUIDE.md         # PM-AI 协作指南
├── context.md                     # 项目上下文和技术栈
├── settings.json                  # Claude Code 配置
├── settings.local.json            # 本地配置
│
├── skills/                        # AI 技能库
│   ├── skill-developer/           # 技能开发元技能
│   │   ├── SKILL.md              # 技能主文件
│   │   └── resources/            # 技能资源文件
│   └── skill-rules.json          # 技能自动激活规则
│
├── agents/                        # 专用 AI 代理（7个）
│   ├── code-architecture-reviewer.md     # 代码架构审查
│   ├── code-refactor-master.md           # 代码重构大师
│   ├── documentation-architect.md        # 文档架构师
│   ├── plan-reviewer.md                  # 计划审查器
│   ├── refactor-planner.md               # 重构规划器
│   ├── web-research-specialist.md        # 网络调研专家
│   └── auto-error-resolver.md            # 自动错误解决器
│
├── commands/                      # 斜杠命令
│   ├── dev-docs.md               # 生成开发文档
│   └── dev-docs-update.md        # 更新开发文档
│
└── hooks/                         # 自动化钩子
    ├── skill-activation-prompt.sh    # 技能自动激活（Shell）
    ├── skill-activation-prompt.ts    # 技能自动激活（TypeScript）
    ├── post-tool-use-tracker.sh      # 工具使用后跟踪
    ├── package.json                  # Hook 依赖
    ├── tsconfig.json                 # TypeScript 配置
    └── node_modules/                 # 依赖安装目录
```

## ✅ 已集成的组件

### 🎯 核心 Hooks（自动激活系统）

| Hook | 类型 | 功能 | 状态 |
|------|------|------|------|
| **skill-activation-prompt** | UserPromptSubmit | 根据用户提示自动建议相关技能 | ✅ 已启用 |
| **post-tool-use-tracker** | PostToolUse | 跟踪文件编辑，为技能提供上下文 | ✅ 已启用 |

这两个 hooks 构成了**技能自动激活系统**的核心：
- 当你编辑特定文件时，相关技能会自动激活
- 当你的提示包含特定关键词时，Claude 会建议相关技能
- 完全通用，无需自定义配置

### 🎨 技能（Skills）

| 技能 | 适用性 | 说明 |
|------|--------|------|
| **skill-developer** | ✅ 通用 | 创建和管理 Claude Code 技能的元技能 |

**为什么只有一个技能？**

原项目中的其他技能：
- `backend-dev-guidelines` - 专为 Express/Prisma/Node.js 设计（本项目用 Rust/Tauri）
- `frontend-dev-guidelines` - 专为 React/MUI v7 设计（本项目用 React/Tailwind）
- `route-tester` - 需要 JWT cookie 认证（本项目是桌面应用）
- `error-tracking` - 需要 Sentry（本项目暂未集成）

**下一步**：根据项目需要创建自定义技能：
- `tauri-command-dev` - Tauri 命令开发指南
- `rust-backend-dev` - Rust 后端开发规范
- `react-tailwind-dev` - React + Tailwind 前端规范

### 🤖 Agents（专用代理）

所有 **7 个通用 agents** 已集成：

| Agent | 用途 | 使用方法 |
|-------|------|----------|
| **code-architecture-reviewer** | 审查代码架构 | "使用 code-architecture-reviewer 审查物价查询模块" |
| **code-refactor-master** | 执行代码重构 | "使用 code-refactor-master 重构状态管理" |
| **documentation-architect** | 生成项目文档 | "使用 documentation-architect 生成 API 文档" |
| **plan-reviewer** | 审查开发计划 | "审查我的功能实现计划" |
| **refactor-planner** | 规划重构策略 | "规划如何重构地图组件" |
| **web-research-specialist** | 技术调研 | "调研最佳的 Rust 截图库" |
| **auto-error-resolver** | 自动修复错误 | "修复所有 TypeScript 错误" |

**未集成的 agents**（需要特定技术栈）：
- `auth-route-tester` - 需要 JWT cookie 认证
- `auth-route-debugger` - 需要 JWT cookie 认证
- `frontend-error-fixer` - 针对 React/MUI 特定错误

### 💬 Slash Commands

| 命令 | 功能 | 使用场景 |
|------|------|----------|
| `/dev-docs` | 创建结构化开发文档 | 开始新功能开发前 |
| `/dev-docs-update` | 更新开发文档 | 功能完成或重大变更后 |

**未集成的命令**：
- `/route-research-for-testing` - 专为 API 路由测试设计

## 🚀 如何使用

### 1. 技能自动激活

技能会根据以下条件自动激活：

**文件触发**：
- 编辑 `.claude/skills/**/*.md` → 激活 `skill-developer`

**关键词触发**：
- 提示包含 "创建技能"、"skill development" → 激活 `skill-developer`

**配置位置**：[skills/skill-rules.json](skills/skill-rules.json)

### 2. 使用 Agents

直接在对话中请求：

```
"使用 documentation-architect agent 帮我生成完整的项目文档"
```

或者简短版：

```
"帮我审查代码架构"  ← Claude 会自动选择 code-architecture-reviewer
```

### 3. 使用斜杠命令

在对话中输入：

```
/dev-docs feature-name "实现物品收藏功能"
```

这会创建：
- `dev/active/feature-name/feature-name-plan.md`
- `dev/active/feature-name/feature-name-context.md`
- `dev/active/feature-name/feature-name-tasks.md`

## 🎓 创建自定义技能

使用 `skill-developer` 技能创建适合本项目的技能：

### 示例：创建 Tauri 命令开发技能

1. **告诉 Claude**：
   ```
   "使用 skill-developer 帮我创建一个 tauri-command-dev 技能"
   ```

2. **提供技能需求**：
   ```
   这个技能应该包括：
   - 如何定义 Tauri 命令（#[tauri::command] 宏）
   - Rust 命令函数最佳实践
   - 前端如何调用（invoke）
   - 错误处理规范
   - 类型定义（TypeScript 和 Rust 对应）
   ```

3. **Claude 会**：
   - 创建技能目录结构
   - 生成主技能文件和资源文件
   - 更新 `skill-rules.json` 添加触发规则
   - 测试技能激活

### 推荐创建的技能

基于本项目技术栈，建议创建：

1. **tauri-command-dev** - Tauri 命令开发
   - 触发：编辑 `src-tauri/src/commands/*.rs`
   - 关键词：tauri、command、invoke

2. **rust-backend-dev** - Rust 后端开发规范
   - 触发：编辑 `src-tauri/src/**/*.rs`
   - 关键词：rust、backend、tokio

3. **react-tailwind-ui** - React + Tailwind UI 开发
   - 触发：编辑 `src/**/*.tsx`
   - 关键词：component、tailwind、ui

4. **tarkov-api-integration** - Tarkov.dev API 集成
   - 触发：编辑包含 GraphQL 的文件
   - 关键词：tarkov、graphql、api

## 📝 维护和扩展

### 添加新技能

1. 编辑任何 `.claude/skills/**/*.md` 文件
2. `skill-developer` 技能自动激活
3. 按照指导创建新技能

### 修改技能触发规则

编辑 [skills/skill-rules.json](skills/skill-rules.json)：

```json
{
  "your-skill-name": {
    "description": "技能描述",
    "keywordTriggers": ["关键词1", "关键词2"],
    "fileTriggers": {
      "pathPatterns": [
        "src/**/*.tsx",
        "src-tauri/**/*.rs"
      ]
    },
    "promptPatterns": [
      "正则表达式.*匹配"
    ]
  }
}
```

### 自定义 Agent

复制现有 agent 作为模板：

```bash
cp .claude/agents/code-architecture-reviewer.md \\
   .claude/agents/your-custom-agent.md
```

然后编辑内容适配你的需求。

## 🔧 故障排查

### 技能没有自动激活？

1. **检查 hooks 是否安装**：
   ```bash
   ls -la .claude/hooks/node_modules
   ```

2. **检查 settings.json 配置**：
   ```bash
   cat .claude/settings.json
   ```

3. **检查 skill-rules.json**：
   ```bash
   cat .claude/skills/skill-rules.json
   ```

4. **手动触发技能**：
   ```
   "使用 skill-developer 技能"
   ```

### Hooks 报错？

1. **重新安装依赖**：
   ```bash
   cd .claude/hooks && npm install
   ```

2. **检查 Node.js 版本**：
   ```bash
   node --version  # 应该 >= 18
   ```

## 📚 延伸阅读

- [COLLABORATION_GUIDE.md](COLLABORATION_GUIDE.md) - PM-AI 协作指南
- [context.md](context.md) - 项目上下文和技术栈
- [原项目文档](https://github.com/diet103/claude-code-infrastructure-showcase)

## 🙏 致谢

本基础设施来自 [diet103/claude-code-infrastructure-showcase](https://github.com/diet103/claude-code-infrastructure-showcase)，感谢作者分享 6 个月生产环境的经验总结。

---

**集成日期**: 2024-12-03
**维护者**: Claude Code AI
**项目**: T2-Tarkov-Toolbox
