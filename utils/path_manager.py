"""
统一的资源路径管理模块

支持开发和打包exe两种模式，使用exe所在目录作为根目录

目录结构：
T2-Tarkov-Toolbox.exe (或开发目录)
├── config/              # 配置文件目录（自动创建）
│   ├── filter_config.json
│   └── map_config.json
├── assets/              # 资源目录（自动创建）
│   └── maps/           # 地图图片目录
│       ├── bigmap/     # 各地图子目录
│       └── ...
└── exports/            # 导出目录（自动创建）
"""

import os
import sys
from pathlib import Path


class PathManager:
    """统一的路径管理器（单例模式）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 获取应用根目录（exe所在目录或开发目录）
        if getattr(sys, 'frozen', False):
            # 打包成exe后，使用exe所在目录
            self.app_root = Path(sys.executable).parent
        else:
            # 开发模式，使用项目根目录
            self.app_root = Path(__file__).parent.parent

        # 定义各个子目录
        self.config_dir = self.app_root / "config"
        self.assets_dir = self.app_root / "assets"
        self.maps_dir = self.assets_dir / "maps"
        self.exports_dir = self.app_root / "exports"

        # 创建必要的目录
        self._ensure_directories()

        self._initialized = True

    def _ensure_directories(self):
        """确保必要的目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.maps_dir.mkdir(parents=True, exist_ok=True)
        # exports目录按需创建，这里不提前创建

    # === 配置文件路径 ===

    def get_filter_config_path(self) -> str:
        """获取屏幕滤镜配置文件路径"""
        return str(self.config_dir / "filter_config.json")

    def get_map_config_path(self) -> str:
        """获取地图配置文件路径"""
        return str(self.config_dir / "map_config.json")

    def get_global_config_path(self) -> str:
        """获取全局配置文件路径"""
        return str(self.config_dir / "global_config.json")

    # === 资源文件路径 ===

    def get_maps_dir(self) -> str:
        """获取地图图片根目录"""
        return str(self.maps_dir)

    def get_map_dir(self, map_id: str) -> str:
        """获取特定地图的目录"""
        map_dir = self.maps_dir / map_id
        map_dir.mkdir(parents=True, exist_ok=True)
        return str(map_dir)

    def get_map_image_path(self, map_id: str, image_filename: str) -> str:
        """
        获取地图图片的完整路径

        Args:
            map_id: 地图ID
            image_filename: 图片文件名

        Returns:
            完整的绝对路径
        """
        return str(self.maps_dir / map_id / image_filename)

    # === 导出路径 ===

    def get_exports_dir(self) -> str:
        """获取导出目录"""
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        return str(self.exports_dir)

    # === 路径转换工具 ===

    def get_relative_path(self, absolute_path: str) -> str:
        """
        将绝对路径转换为相对于应用根目录的相对路径

        Args:
            absolute_path: 绝对路径

        Returns:
            相对路径字符串，如果不在应用目录下则返回原路径
        """
        try:
            path = Path(absolute_path)
            rel_path = path.relative_to(self.app_root)
            # 使用正斜杠，保证跨平台兼容
            return str(rel_path).replace('\\', '/')
        except ValueError:
            # 如果不在应用目录下，返回原路径
            return absolute_path

    def get_absolute_path(self, relative_path: str) -> str:
        """
        将相对路径转换为绝对路径

        Args:
            relative_path: 相对于应用根目录的相对路径

        Returns:
            绝对路径字符串
        """
        # 如果已经是绝对路径，直接返回
        path = Path(relative_path)
        if path.is_absolute():
            return relative_path

        # 转换相对路径
        abs_path = self.app_root / relative_path
        return str(abs_path)

    def normalize_image_path(self, image_path: str, map_id: str) -> str:
        """
        规范化图片路径：将任意路径转换为相对路径并复制文件到正确位置

        Args:
            image_path: 原始图片路径（可能是绝对路径）
            map_id: 地图ID

        Returns:
            相对路径（相对于app_root）
        """
        source_path = Path(image_path)
        if not source_path.exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        # 目标目录
        target_dir = self.maps_dir / map_id
        target_dir.mkdir(parents=True, exist_ok=True)

        # 目标文件路径
        target_path = target_dir / source_path.name

        # 如果源文件不在目标位置，复制文件
        if source_path.resolve() != target_path.resolve():
            import shutil
            shutil.copy2(source_path, target_path)

        # 返回相对路径
        return self.get_relative_path(str(target_path))


# 全局单例实例
path_manager = PathManager()
