# T2 塔科夫工具箱 - 功能模块规划

## 📋 功能模块清单

### ✅ 已确认的功能模块

1. **🎨 屏幕滤镜 (Screen Filter)**
   - 自定义屏幕颜色、亮度、对比度
   - 滤镜预设管理
   - 实时预览

2. **🗺️ 战术地图 (Tactical Map)**
   - 显示游戏地图
   - 自动识别位置（通过截图 EXIF）
   - 标记出生点、提取点、任务点
   - 自定义标记

3. **📋 任务追踪 (Quest Tracker)**
   - 同步 TarkovTracker 任务进度
   - 按商人分组的树状图显示
   - 任务详情查看
   - 任务搜索和筛选

4. **⚙️ 全局设置 (Settings)**
   - 应用配置
   - 截图文件夹路径
   - 快捷键设置
   - 配置导入/导出

### ❌ 暂时移除的功能

- ~~💰 物价查询~~ - RatScanner 已足够好用，暂不实现

### 🔮 未来可能添加

- 🔫 装配器（枪械配件）
- 📦 藏匿点地图
- 🎯 击杀统计
- 📊 数据分析

---

## 🎨 屏幕滤镜 (Screen Filter)

### 功能描述
通过透明置顶窗口实现屏幕滤镜，调整游戏视觉效果。

### 核心功能
1. **基础调整**
   - 亮度 (0-200%)
   - 对比度 (0-200%)
   - 饱和度 (0-200%)
   - 色相旋转 (-180° ~ +180°)

2. **RGB 通道**
   - 红色通道 (0-200%)
   - 绿色通道 (0-200%)
   - 蓝色通道 (0-200%)

3. **预设管理**
   - 保存当前滤镜为预设
   - 快速切换预设
   - 导入/导出预设（JSON）
   - 预设命名和分类

### 技术实现
- **Tauri 透明窗口** - 全屏置顶
- **CSS Filters** - `filter: brightness() contrast() saturate() hue-rotate()`
- **热键切换** - 快速启用/禁用

### UI 设计
```
┌──────────────────────────────────────┐
│ 屏幕滤镜                              │
├──────────────────────────────────────┤
│ [ ] 启用滤镜                          │
│                                      │
│ 亮度:    [========|====] 120%        │
│ 对比度:  [========|====] 110%        │
│ 饱和度:  [======|======] 100%        │
│ 色相:    [======|======] 0°          │
│                                      │
│ 红色通道: [========|====] 120%       │
│ 绿色通道: [========|====] 110%       │
│ 蓝色通道: [======|======] 100%       │
│                                      │
│ 预设: [夜视模式 ▼]                   │
│ [保存当前预设] [重置]                 │
│ [导出预设] [导入预设]                 │
└──────────────────────────────────────┘
```

---

## 🗺️ 战术地图 (Tactical Map)

### 功能描述
显示塔科夫地图，自动识别玩家位置，标记关键点位。

### 核心功能

1. **地图显示**
   - 支持所有主要地图（Customs, Woods, Shoreline, Interchange, Reserve, Labs, Factory, Lighthouse, Streets）
   - 缩放、平移
   - 图层切换（卫星图 / 简化图）

2. **自动位置识别**
   - 监控截图文件夹
   - 读取截图 EXIF 元数据（XPosition, YPosition, Rotation, MapName）
   - 在地图上标记玩家位置
   - 显示视角方向

3. **标记系统**
   - 出生点（Spawn Points）
   - 提取点（Extracts）
   - 任务点（Quest Markers）
   - 自定义标记（用户添加）
   - 标记过滤（显示/隐藏）

4. **地图配置**
   - 不透明度调整
   - 自动居中玩家位置
   - 标记大小和样式

### 技术实现

#### 截图 EXIF 解析（Rust）
```rust
use exif::{In, Reader, Tag};
use std::fs::File;

pub struct PlayerLocation {
    pub map_name: String,
    pub x: f64,
    pub y: f64,
    pub rotation: f64,
}

pub fn parse_screenshot(path: &str) -> Result<PlayerLocation, Error> {
    let file = File::open(path)?;
    let mut reader = std::io::BufReader::new(&file);
    let exif = Reader::new().read_from_container(&mut reader)?;

    let map_name = exif
        .get_field(Tag::ImageDescription, In::PRIMARY)
        .and_then(|f| f.display_value().to_string());

    let x_position = exif
        .get_field(Tag::XPosition, In::PRIMARY)
        .and_then(|f| f.value.get_f64(0));

    let y_position = exif
        .get_field(Tag::YPosition, In::PRIMARY)
        .and_then(|f| f.value.get_f64(0));

    // ...解析其他字段
}
```

#### 文件监控（Rust）
```rust
use notify::{Watcher, RecursiveMode, Event};
use std::sync::mpsc::channel;

pub fn watch_screenshot_folder(path: &str) {
    let (tx, rx) = channel();
    let mut watcher = notify::recommended_watcher(tx)?;

    watcher.watch(path.as_ref(), RecursiveMode::Recursive)?;

    for event in rx {
        if let Ok(Event { kind: EventKind::Create(_), paths, .. }) = event {
            for path in paths {
                if path.extension() == Some("png") || path.extension() == Some("jpg") {
                    // 解析截图并更新位置
                    if let Ok(location) = parse_screenshot(&path) {
                        // 发送到前端
                        emit_location_update(location);
                    }
                }
            }
        }
    }
}
```

#### 地图显示（前端）
- **选项 1**: Leaflet.js（推荐）
  - 成熟的地图库
  - 支持自定义瓦片地图
  - 标记和图层系统完善

- **选项 2**: React-Konva
  - Canvas 渲染，性能更好
  - 更灵活的自定义绘制
  - 学习曲线较陡

### 地图数据来源
- **Tarkov.dev API** - 提供地图数据、出生点、提取点等
- **自定义地图图片** - 高清地图图片资源

### UI 设计
```
┌──────────────────────────────────────────────┐
│ 地图: [Customs ▼]  [ ] 出生点 [√] 提取点      │
│                    [√] 任务点 [ ] 自定义标记  │
├──────────────────────────────────────────────┤
│                                              │
│            [      地图显示区域      ]         │
│                  🧍(玩家位置)                 │
│                    ↑                         │
│            🚪 提取点    ⭐ 任务点              │
│                                              │
├──────────────────────────────────────────────┤
│ 当前位置: (123.5, 456.7) | 方向: 北           │
│ 最近提取: Old Gas Station (150m)             │
└──────────────────────────────────────────────┘
```

---

## 📋 任务追踪 (Quest Tracker)

### 功能描述
同步 TarkovTracker 的任务进度，按商人分组显示任务树。

### 核心功能

1. **TarkovTracker 集成**
   - OAuth 登录 / Token 授权
   - 同步任务进度
   - 自动刷新（可配置间隔）
   - 手动同步按钮

2. **任务显示**
   - 按商人分组（树状图）
   - 任务状态：未完成 / 进行中 / 已完成
   - 任务详情（目标、奖励、地图）
   - 任务搜索和过滤

3. **商人分组**
   - Prapor（普拉波）
   - Therapist（治疗师）
   - Skier（滑雪者）
   - Peacekeeper（和平使者）
   - Mechanic（机械师）
   - Ragman（拉格曼）
   - Jaeger（猎人）
   - Fence（掮客）

4. **任务树状图**
   ```
   📁 Prapor (5/20)
   ├─ ✅ Debut
   ├─ ✅ Checking
   ├─ 🔄 Shootout Picnic (2/3)
   │  ├─ ✅ 击杀 5 个 Scav
   │  ├─ ✅ 找到手枪
   │  └─ ⏳ 交给 Prapor
   ├─ ⏹️ Delivery from the Past
   └─ 🔒 Bad Rep Evidence (需要: Debut)
   ```

### TarkovTracker API

#### 认证
```typescript
// TarkovTracker API 使用 Token 认证
const TARKOV_TRACKER_API = 'https://tarkovtracker.io/api/v2';

async function authenticateUser(token: string) {
  const response = await fetch(`${TARKOV_TRACKER_API}/progress`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (response.ok) {
    return await response.json();
  } else {
    throw new Error('认证失败');
  }
}
```

#### 获取任务进度
```typescript
interface QuestProgress {
  id: string;
  name: string;
  trader: string;
  complete: boolean;
  objectives: {
    id: string;
    description: string;
    complete: boolean;
  }[];
}

async function getQuestProgress(token: string): Promise<QuestProgress[]> {
  const response = await fetch(`${TARKOV_TRACKER_API}/progress`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  return await response.json();
}
```

#### 更新任务进度（可选）
```typescript
async function updateQuestProgress(
  token: string,
  questId: string,
  complete: boolean
) {
  await fetch(`${TARKOV_TRACKER_API}/progress/${questId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ complete }),
  });
}
```

### Rust 后端缓存

为了减少 API 调用，在 Rust 后端缓存任务数据：

```rust
// src-tauri/src/quest/cache.rs

use serde::{Deserialize, Serialize};
use std::time::{SystemTime, Duration};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuestCache {
    pub data: Vec<QuestProgress>,
    pub last_sync: SystemTime,
    pub expires_in: Duration,
}

impl QuestCache {
    pub fn is_expired(&self) -> bool {
        SystemTime::now()
            .duration_since(self.last_sync)
            .map(|d| d > self.expires_in)
            .unwrap_or(true)
    }

    pub fn update(&mut self, data: Vec<QuestProgress>) {
        self.data = data;
        self.last_sync = SystemTime::now();
    }
}
```

### UI 设计

```
┌──────────────────────────────────────────────┐
│ 任务追踪                                      │
│                                              │
│ TarkovTracker Token: [**************]  [连接] │
│ 最后同步: 5分钟前  [手动同步] [自动同步: ON]   │
├──────────────────────────────────────────────┤
│ 搜索: [____________]  [ ] 显示已完成任务      │
│                                              │
│ 📁 Prapor (5/20) ▼                          │
│   ├─ ✅ Debut                                │
│   ├─ ✅ Checking                             │
│   ├─ 🔄 Shootout Picnic (2/3)               │
│   │   ├─ ✅ 击杀 5 个 Scav                   │
│   │   ├─ ✅ 找到手枪                         │
│   │   └─ ⏳ 交给 Prapor                      │
│   └─ 🔒 Bad Rep Evidence                    │
│                                              │
│ 📁 Therapist (3/15) ▶                       │
│ 📁 Skier (2/18) ▶                           │
│ ...                                          │
└──────────────────────────────────────────────┘
```

---

## ⚙️ 全局设置 (Settings)

### 配置项

#### 应用设置
- 语言（中文/英文）
- 主题（深色/浅色）
- 开机自启
- 最小化到托盘

#### 截图监控
- 截图文件夹路径
- 自动检测
- 检测到截图时通知

#### 快捷键
- 切换滤镜：Ctrl+Shift+T
- 打开地图：Ctrl+Shift+M
- 打开任务：Ctrl+Shift+Q

#### 任务同步
- TarkovTracker Token
- 自动同步间隔
- 显示已完成任务

#### 配置管理
- [导出配置] - 导出到 JSON 文件
- [导入配置] - 从 JSON 文件导入
- [重置为默认] - 恢复硬编码默认值

---

## 📊 导航和路由

### 更新后的导航栏

```typescript
<nav className="flex space-x-1">
  <NavLink to="/">🏠 首页</NavLink>
  <NavLink to="/filter">🎨 屏幕滤镜</NavLink>
  <NavLink to="/map">🗺️ 战术地图</NavLink>
  <NavLink to="/quests">📋 任务追踪</NavLink>
  <NavLink to="/settings">⚙️ 设置</NavLink>
</nav>
```

### 路由配置

```typescript
<Routes>
  <Route path="/" element={<Home />} />
  <Route path="/filter" element={<ScreenFilter />} />
  <Route path="/map" element={<TacticalMap />} />
  <Route path="/quests" element={<QuestTracker />} />
  <Route path="/settings" element={<Settings />} />
  <Route path="*" element={<NotFound />} />
</Routes>
```

---

## 🗂️ 项目结构更新

```
src/
├── pages/
│   ├── Home.tsx              # 首页
│   ├── ScreenFilter.tsx      # 屏幕滤镜
│   ├── TacticalMap.tsx       # 战术地图
│   ├── QuestTracker.tsx      # 任务追踪
│   └── Settings.tsx          # 全局设置
├── components/
│   ├── filter/               # 滤镜组件
│   │   ├── FilterControls.tsx
│   │   └── PresetManager.tsx
│   ├── map/                  # 地图组件
│   │   ├── MapViewer.tsx
│   │   ├── MarkerLayer.tsx
│   │   └── LocationIndicator.tsx
│   └── quest/                # 任务组件
│       ├── QuestTree.tsx
│       ├── QuestItem.tsx
│       └── TraderGroup.tsx
├── stores/
│   ├── useConfigStore.ts     # 配置管理
│   ├── useFilterStore.ts     # 滤镜状态
│   ├── useMapStore.ts        # 地图状态
│   └── useQuestStore.ts      # 任务状态
├── services/
│   ├── tarkovTrackerAPI.ts   # TarkovTracker API
│   └── tarkovDevAPI.ts       # Tarkov.dev API
└── types/
    ├── config.ts
    ├── quest.ts
    └── map.ts

src-tauri/src/
├── config/                   # 配置管理
├── filter/                   # 滤镜窗口
├── map/                      # 地图逻辑
│   ├── exif_parser.rs       # EXIF 解析
│   └── screenshot_watcher.rs # 文件监控
├── quest/                    # 任务同步
│   ├── api.rs               # API 调用
│   └── cache.rs             # 缓存管理
└── commands/
    ├── config.rs
    ├── filter.rs
    ├── map.rs
    └── quest.rs
```

---

## 🎯 开发优先级

### Phase 1 - 基础框架（第 1 周）
1. ✅ UI 框架和导航
2. ✅ 配置管理系统
3. ✅ 全局设置页面

### Phase 2 - 屏幕滤镜（第 2 周）
1. 滤镜控制界面
2. 实时预览
3. 预设管理
4. 导入/导出

### Phase 3 - 战术地图（第 3-4 周）
1. 地图显示（Leaflet.js）
2. EXIF 解析（Rust）
3. 文件监控（Rust）
4. 位置标记
5. 自定义标记

### Phase 4 - 任务追踪（第 5-6 周）
1. TarkovTracker API 集成
2. 任务树状图
3. 同步机制
4. 缓存管理

---

**最后更新**: 2024-12-03
**当前阶段**: Phase 1 - 基础框架搭建中
