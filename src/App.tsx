import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { useState } from 'react';

// 模拟 Tauri invoke（用于浏览器预览）
const invoke = async (cmd: string, args: any) => {
  if (cmd === 'greet') {
    return `你好, ${args.name}! (浏览器预览模式 - Tauri 未连接)`;
  }
  return null;
};

// 页面组件（稍后创建完整版本）
import Home from './pages/Home';
import ScreenFilter from './pages/ScreenFilter';
// import TacticalMap from './pages/TacticalMap';
// import QuestTracker from './pages/QuestTracker';
// import Settings from './pages/Settings';

// 导航链接组件（带活动状态高亮）
function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  const location = useLocation();
  const isActive = location.pathname === to;

  return (
    <Link
      to={to}
      className={`px-4 py-2 rounded transition ${isActive
        ? 'bg-blue-600 text-white'
        : 'hover:bg-gray-700'
        }`}
    >
      {children}
    </Link>
  );
}

function AppContent() {
  const [greetMsg, setGreetMsg] = useState('');
  const [name, setName] = useState('');

  async function greet() {
    // 测试 Tauri 命令
    const result = await invoke('greet', { name });
    setGreetMsg(result || '');
  }

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      {/* 顶部导航栏 */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="flex items-center justify-between px-6 py-3">
          {/* Logo 和标题 */}
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-bold">T2 塔科夫工具箱</h1>
            <span className="text-xs text-gray-500">v0.1.0</span>
          </div>

          {/* 导航菜单 */}
          <nav className="flex space-x-1">
            <NavLink to="/">🏠 首页</NavLink>
            <NavLink to="/filter">🎨 屏幕滤镜</NavLink>
            <NavLink to="/map">🗺️ 战术地图</NavLink>
            <NavLink to="/quests">📋 任务追踪</NavLink>
            <NavLink to="/settings">⚙️ 设置</NavLink>
          </nav>

          {/* Tauri 连接测试（右侧小组件） */}
          <div className="flex items-center space-x-2">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="测试连接..."
              className="px-3 py-1 bg-gray-700 rounded text-sm w-32"
            />
            <button
              onClick={greet}
              className="px-3 py-1 bg-blue-600 rounded text-sm hover:bg-blue-700"
            >
              测试
            </button>
            {greetMsg && (
              <span className="text-xs text-green-400">{greetMsg}</span>
            )}
          </div>
        </div>
      </header>

      {/* 主内容区域 */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/filter" element={<ScreenFilter />} />
          {/* <Route path="/map" element={<TacticalMap />} /> */}
          {/* <Route path="/quests" element={<QuestTracker />} /> */}
          {/* <Route path="/settings" element={<Settings />} /> */}
          <Route path="*" element={<ComingSoon />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

// 临时占位组件
function ComingSoon() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h2 className="text-3xl font-bold mb-4">功能开发中...</h2>
        <p className="text-gray-400">Coming Soon!</p>
      </div>
    </div>
  );
}

export default App;
