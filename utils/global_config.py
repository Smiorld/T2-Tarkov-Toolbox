"""
全局配置管理器 - 单例模式
负责应用级配置的加载、保存和变更通知
"""

import json
import os
from typing import Callable, Optional
from pathlib import Path


class GlobalConfig:
    """全局配置管理器 (单例)"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 配置文件路径
        self.config_dir = Path("config")
        self.config_file = self.config_dir / "app_config.json"

        # 配置数据
        self.screenshots_path: str = ""
        self.logs_path: str = ""
        self.language: str = "zh_CN"  # 默认中文

        # 回调函数列表
        self._callbacks: list[Callable[[str, str], None]] = []

        # 加载配置
        self._load_config()

        self._initialized = True

    def _load_config(self):
        """从文件加载配置"""
        if not self.config_file.exists():
            print("[全局配置] 配置文件不存在,使用默认值")
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.screenshots_path = data.get('screenshots_path', '')
            self.logs_path = data.get('logs_path', '')
            self.language = data.get('language', 'zh_CN')

            print(f"[全局配置] 已加载配置: screenshots={self.screenshots_path}, language={self.language}")
        except Exception as e:
            print(f"[全局配置] 加载配置失败: {e}")

    def _save_config(self):
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            self.config_dir.mkdir(exist_ok=True)

            data = {
                'screenshots_path': self.screenshots_path,
                'logs_path': self.logs_path,
                'language': self.language
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"[全局配置] 配置已保存")
        except Exception as e:
            print(f"[全局配置] 保存配置失败: {e}")

    # ========== 截图路径管理 ==========

    def get_screenshots_path(self) -> str:
        """获取截图路径"""
        return self.screenshots_path

    def set_screenshots_path(self, path: str, save: bool = True):
        """
        设置截图路径

        Args:
            path: 新的截图路径
            save: 是否立即保存到文件
        """
        if self.screenshots_path != path:
            old_path = self.screenshots_path
            self.screenshots_path = path

            if save:
                self._save_config()

            # 通知所有监听者
            self._notify_change('screenshots_path', path)
            print(f"[全局配置] 截图路径已更新: {old_path} -> {path}")

    # ========== 日志路径管理 ==========

    def get_logs_path(self) -> str:
        """获取日志路径"""
        return self.logs_path

    def set_logs_path(self, path: str, save: bool = True):
        """
        设置日志路径

        Args:
            path: 新的日志路径
            save: 是否立即保存到文件
        """
        if self.logs_path != path:
            old_path = self.logs_path
            self.logs_path = path

            if save:
                self._save_config()

            # 通知所有监听者
            self._notify_change('logs_path', path)
            print(f"[全局配置] 日志路径已更新: {old_path} -> {path}")

    # ========== 语言管理 ==========

    def get_language(self) -> str:
        """获取当前语言"""
        return self.language

    def set_language(self, language: str, save: bool = True):
        """
        设置语言

        Args:
            language: 语言代码 (zh_CN / en_US)
            save: 是否立即保存到文件
        """
        if self.language != language:
            old_lang = self.language
            self.language = language

            if save:
                self._save_config()

            # 通知所有监听者
            self._notify_change('language', language)
            print(f"[全局配置] 语言已更新: {old_lang} -> {language}")

    # ========== 通用配置存储 ==========

    def get(self, key: str, default=None):
        """
        获取配置值

        Args:
            key: 配置键名
            default: 如果键不存在时返回的默认值

        Returns:
            配置值或默认值
        """
        # 从文件读取以获取所有键（包括额外的键）
        if not self.config_file.exists():
            return default

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(key, default)
        except Exception as e:
            print(f"[全局配置] 读取配置键失败 {key}: {e}")
            return default

    def set(self, key: str, value, save: bool = True):
        """
        设置配置值

        Args:
            key: 配置键名
            value: 要设置的值
            save: 是否立即保存到文件
        """
        if not save:
            # 仅更新内存（用于批量更新）
            return

        try:
            # 确保配置目录存在
            self.config_dir.mkdir(exist_ok=True)

            # 加载现有配置
            data = {}
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            # 更新键值
            data[key] = value

            # 同步当前实例变量
            data['screenshots_path'] = self.screenshots_path
            data['logs_path'] = self.logs_path
            data['language'] = self.language

            # 保存回文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"[全局配置] 已保存配置键: {key} = {value}")
        except Exception as e:
            print(f"[全局配置] 保存配置键失败 {key}: {e}")

    # ========== 回调机制 ==========

    def on_config_change(self, callback: Callable[[str, str], None]):
        """
        注册配置变更回调

        Args:
            callback: 回调函数 callback(key, value)
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def _notify_change(self, key: str, value: str):
        """通知所有监听者配置已变更"""
        for callback in self._callbacks:
            try:
                callback(key, value)
            except Exception as e:
                print(f"[全局配置] 回调执行失败: {e}")


# 全局单例实例
_global_config = GlobalConfig()


def get_global_config() -> GlobalConfig:
    """获取全局配置实例"""
    return _global_config
