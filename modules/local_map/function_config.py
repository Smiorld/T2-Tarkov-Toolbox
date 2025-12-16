"""
地图功能配置管理器
管理快捷键、步进值等用户可配置的功能参数
"""
import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class FunctionConfig:
    """功能配置数据类"""
    overlay_hotkey: str = "F5"           # 显示/隐藏悬浮窗快捷键
    zoom_in_hotkey: str = "+"            # 放大快捷键（数字键盘+）
    zoom_out_hotkey: str = "-"           # 缩小快捷键（数字键盘-）
    zoom_step: float = 0.05              # 缩放步进值


class FunctionConfigManager:
    """功能配置管理器"""

    CONFIG_FILE = "map_function_config.json"

    def __init__(self):
        self.config = self._load()

    def _load(self) -> FunctionConfig:
        """加载配置文件"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return FunctionConfig(
                        overlay_hotkey=data.get("overlay_hotkey", "F5"),
                        zoom_in_hotkey=data.get("zoom_in_hotkey", "+"),
                        zoom_out_hotkey=data.get("zoom_out_hotkey", "-"),
                        zoom_step=float(data.get("zoom_step", 0.05))
                    )
        except Exception as e:
            print(f"加载功能配置失败: {e}")

        return FunctionConfig()

    def save(self):
        """保存配置到文件"""
        try:
            data = {
                "overlay_hotkey": self.config.overlay_hotkey,
                "zoom_in_hotkey": self.config.zoom_in_hotkey,
                "zoom_out_hotkey": self.config.zoom_out_hotkey,
                "zoom_step": self.config.zoom_step
            }

            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存功能配置失败: {e}")

    def update_overlay_hotkey(self, hotkey: str):
        """更新悬浮窗快捷键"""
        self.config.overlay_hotkey = hotkey
        self.save()

    def update_zoom_hotkeys(self, zoom_in: str, zoom_out: str):
        """更新缩放快捷键"""
        self.config.zoom_in_hotkey = zoom_in
        self.config.zoom_out_hotkey = zoom_out
        self.save()

    def update_zoom_step(self, step: float):
        """更新缩放步进值"""
        self.config.zoom_step = max(0.01, min(1.0, step))  # 限制范围 0.01-1.0
        self.save()
