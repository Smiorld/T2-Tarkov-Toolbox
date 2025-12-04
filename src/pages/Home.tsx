export default function Home() {
  return (
    <div className="container mx-auto p-8 max-w-7xl">
      {/* 欢迎横幅 */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-3">欢迎使用 T2 塔科夫工具箱！</h1>
        <p className="text-gray-400 text-lg">
          纯本地运行，保护隐私，提升游戏体验
        </p>
      </div>

      {/* 功能卡片 - 2x2 网格 */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        <div className="bg-gray-800 p-6 rounded-lg hover:bg-gray-750 transition cursor-pointer border border-gray-700">
          <h2 className="text-2xl font-bold mb-3">🎨 屏幕滤镜</h2>
          <p className="text-gray-400">
            自定义屏幕颜色、亮度、对比度，优化游戏视觉体验
          </p>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg hover:bg-gray-750 transition cursor-pointer border border-gray-700">
          <h2 className="text-2xl font-bold mb-3">🗺️ 战术地图</h2>
          <p className="text-gray-400">
            实时显示游戏地图，自动识别位置（通过截图），标记关键点位
          </p>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg hover:bg-gray-750 transition cursor-pointer border border-gray-700">
          <h2 className="text-2xl font-bold mb-3">📋 任务追踪</h2>
          <p className="text-gray-400">
            同步 TarkovTracker 任务进度，按商人分组树状图显示
          </p>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg hover:bg-gray-750 transition cursor-pointer border border-gray-700">
          <h2 className="text-2xl font-bold mb-3">⚙️ 全局设置</h2>
          <p className="text-gray-400">
            配置应用参数、截图文件夹路径、快捷键、导入导出配置
          </p>
        </div>
      </div>

      {/* 快速开始指南 */}
      <div className="bg-gradient-to-r from-blue-900 to-blue-800 p-6 rounded-lg mb-6 border border-blue-700">
        <h3 className="text-xl font-bold mb-4">🚀 快速开始</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="flex items-start">
              <span className="bg-blue-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3 flex-shrink-0">1</span>
              <span className="text-gray-200">前往 <strong>设置</strong> 配置截图文件夹路径</span>
            </div>
            <div className="flex items-start">
              <span className="bg-blue-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3 flex-shrink-0">2</span>
              <span className="text-gray-200">配置 <strong>TarkovTracker</strong> Token 同步任务</span>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex items-start">
              <span className="bg-blue-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3 flex-shrink-0">3</span>
              <span className="text-gray-200">游戏中截图，<strong>战术地图</strong> 自动显示位置</span>
            </div>
            <div className="flex items-start">
              <span className="bg-blue-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3 flex-shrink-0">4</span>
              <span className="text-gray-200">使用 <strong>屏幕滤镜</strong> 和 <strong>任务追踪</strong> 优化体验</span>
            </div>
          </div>
        </div>
      </div>

      {/* 底部信息 */}
      <div className="text-center text-gray-500 text-sm">
        <p>当前版本: v0.1.0 (开发中) | 本项目开源于 GitHub | 欢迎贡献代码和反馈问题</p>
      </div>
    </div>
  );
}
