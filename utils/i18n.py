"""
i18n 翻译管理器 - 单例模式
提供简单的字典查询翻译功能
"""

import json
from pathlib import Path
from typing import Optional


class I18nManager:
    """翻译管理器（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.locales_dir = Path(__file__).parent.parent / "locales"
        self.current_language = "zh_CN"  # 默认中文
        self.translations = {}

        # 立即加载默认语言的翻译
        self._load_translations()

        self._initialized = True

    def set_language(self, language: str):
        """设置当前语言并加载翻译文件"""
        self.current_language = language
        self._load_translations()

    def _load_translations(self):
        """从JSON文件加载翻译"""
        locale_file = self.locales_dir / f"{self.current_language}.json"

        if not locale_file.exists():
            print(f"[i18n] 警告：翻译文件不存在 {locale_file}")
            self.translations = {}
            return

        try:
            with open(locale_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            print(f"[i18n] 已加载语言: {self.current_language}")
        except Exception as e:
            print(f"[i18n] 加载翻译失败: {e}")
            self.translations = {}

    def t(self, key: str, **kwargs) -> str:
        """
        翻译文本（支持变量替换）

        Args:
            key: 翻译键（使用点分隔，如 "screen_filter.title"）
            **kwargs: 用于格式化的变量

        Returns:
            翻译后的文本，如果找不到则返回 [key]
        """
        # 支持嵌套键
        keys = key.split('.')
        value = self.translations

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break

        if value is None:
            print(f"[i18n] 缺失翻译键: {key}")
            return f"[{key}]"

        # 支持变量替换
        if kwargs:
            try:
                return value.format(**kwargs)
            except KeyError as e:
                print(f"[i18n] 格式化变量缺失: {e}")
                # raise(e)
                return value

        return value


# 全局单例实例
_i18n_manager = I18nManager()


def get_i18n() -> I18nManager:
    """获取翻译管理器实例"""
    return _i18n_manager


def t(key: str, **kwargs) -> str:
    """全局翻译函数（快捷方式）"""
    return _i18n_manager.t(key, **kwargs)


def get_current_language() -> str:
    """获取当前语言设置"""
    return _i18n_manager.current_language
