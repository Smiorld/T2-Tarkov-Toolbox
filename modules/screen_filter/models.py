from dataclasses import dataclass, field, asdict
from typing import Optional, Dict

@dataclass
class FilterConfig:
    brightness: float = 0.0  # -1.0 to 1.0 (0.0 = unchanged)
    gamma: float = 1.0       # 0.5 to 3.5 (1.0 = linear)
    contrast: float = 0.0    # -0.5 to 0.5 (0.0 = unchanged)
    red_scale: float = 1.0   # 0.0 to 1.0 (1.0 = max)
    green_scale: float = 1.0
    blue_scale: float = 1.0

    # 悬浮窗对冲设置（防止过曝）
    overlay_brightness_offset: float = 0.0  # 悬浮窗额外亮度偏移
    overlay_gamma_offset: float = 0.0       # 悬浮窗额外伽马偏移
    overlay_contrast_offset: float = 0.0    # 悬浮窗额外对比度偏移

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data: dict):
        return FilterConfig(
            brightness=data.get("brightness", 0.0),
            gamma=data.get("gamma", 1.0),
            contrast=data.get("contrast", 0.0),
            red_scale=data.get("red_scale", 1.0),
            green_scale=data.get("green_scale", 1.0),
            blue_scale=data.get("blue_scale", 1.0),
            overlay_brightness_offset=data.get("overlay_brightness_offset", 0.0),
            overlay_gamma_offset=data.get("overlay_gamma_offset", 0.0),
            overlay_contrast_offset=data.get("overlay_contrast_offset", 0.0),
        )

@dataclass
class FilterPreset:
    id: str
    name: str
    config: FilterConfig
    hotkey: Optional[str] = None
    is_default: bool = False

    def to_dict(self):
        data = asdict(self)
        data['config'] = self.config.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict):
        return FilterPreset(
            id=data.get("id", ""),
            name=data.get("name", "Unnamed"),
            config=FilterConfig.from_dict(data.get("config", {})),
            hotkey=data.get("hotkey"),
            is_default=data.get("is_default", False),
        )
