"""
Unified configuration manager for all screen filter settings.
Manages presets, UI state (monitor selection), and hotkeys in a single JSON file.
"""
import json
from typing import List, Optional, Dict
from modules.screen_filter.models import FilterPreset, FilterConfig
from utils.i18n import t


class ConfigManager:
    """Unified configuration manager for presets and UI state"""

    def __init__(self, config_file: Optional[str] = None):
        # 使用路径管理器获取配置文件路径
        if config_file is None:
            from utils import path_manager
            config_file = path_manager.get_filter_config_path()

        self.config_file = config_file

        # Load old config to detect changes
        old_presets = None
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                old_config = json.load(f)
                old_presets = [p.get("name") for p in old_config.get("presets", [])]
        except:
            pass

        self.config = self._load_config()

        # Save if migration changed preset names
        new_presets = [p.get("name") for p in self.config.get("presets", [])]
        if old_presets and old_presets != new_presets:
            self.save_config()

    def _load_config(self) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # Migrate preset names to current language
            config = self._migrate_default_preset_names(config)
            return config
        except FileNotFoundError:
            return self._create_default_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._create_default_config()

    def _create_default_config(self) -> dict:
        """Create default configuration structure with default presets"""
        return {
            "presets": self._get_default_presets_dict(),  # List of preset configurations
            "selected_monitors": [],                       # List of selected monitor device names
            "last_preset_id": None,                        # ID of last selected preset
            "reset_on_close": True                         # Reset filters when app closes
        }

    def _get_default_presets_dict(self) -> list:
        """Get default presets as dictionary list"""
        default_presets = [
            FilterPreset(
                id="default",
                name=t("screen_filter.presets.default"),
                hotkey="F2",
                config=FilterConfig(
                    brightness=0.0,    # UI: 0 (neutral)
                    gamma=1.0,         # UI: 1.0 (linear gamma)
                    contrast=0.0,      # UI: 0 (neutral)
                    red_scale=1.0,
                    green_scale=1.0,
                    blue_scale=1.0,
                    overlay_brightness_offset=0.0,  # 无对冲
                    overlay_gamma_offset=0.0,
                    overlay_contrast_offset=0.0
                ),
                is_default=True
            ),
            FilterPreset(
                id="daytime",
                name=t("screen_filter.presets.daytime"),
                hotkey="F3",
                config=FilterConfig(
                    brightness=0.0315,  # UI: ~9 (calibrated for daytime use)
                    gamma=1.5,          # UI: 1.5 (slightly darken brights)
                    contrast=0.048,     # UI: ~8 (subtle contrast boost)
                    red_scale=1.0,
                    green_scale=1.0,
                    blue_scale=1.0,
                    overlay_brightness_offset=0.1435,   # 对冲白天滤镜的亮度影响
                    overlay_gamma_offset=0.24,          # 对冲白天滤镜的伽马影响
                    overlay_contrast_offset=-0.21       # 对冲白天滤镜的对比度影响
                ),
                is_default=True
            ),
            FilterPreset(
                id="nighttime",
                name=t("screen_filter.presets.nighttime"),
                hotkey="F4",
                config=FilterConfig(
                    brightness=0.1855,  # UI: ~53 (calibrated for night visibility)
                    gamma=1.95,         # UI: 1.95 (lighten darks significantly)
                    contrast=0.042,     # UI: ~7 (balanced contrast)
                    red_scale=1.0,
                    green_scale=1.0,
                    blue_scale=1.0,
                    overlay_brightness_offset=0.2065,   # 对冲夜间滤镜的亮度影响
                    overlay_gamma_offset=0.74,          # 对冲夜间滤镜的伽马影响
                    overlay_contrast_offset=-0.138      # 对冲夜间滤镜的对比度影响
                ),
                is_default=True
            )
        ]
        return [p.to_dict() for p in default_presets]

    def _migrate_default_preset_names(self, config: dict) -> dict:
        """Update default preset names to current language"""
        # Map hardcoded names to translation keys
        name_to_key = {
            "默认": "screen_filter.presets.default",
            "白天": "screen_filter.presets.daytime",
            "夜间": "screen_filter.presets.nighttime",
            "Default": "screen_filter.presets.default",
            "Daytime": "screen_filter.presets.daytime",
            "Nighttime": "screen_filter.presets.nighttime"
        }

        # Update default presets only
        for preset in config.get("presets", []):
            if preset.get("is_default", False):
                current_name = preset.get("name", "")
                if current_name in name_to_key:
                    preset["name"] = t(name_to_key[current_name])

        return config

    def save_config(self):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    # === Monitor Selection State ===

    def get_selected_monitors(self) -> List[str]:
        """Get list of selected monitor device names"""
        return self.config.get("selected_monitors", [])

    def set_selected_monitors(self, monitors: List[str]):
        """Set selected monitors and save"""
        self.config["selected_monitors"] = monitors

    # === Last Preset State ===

    def get_last_preset_id(self) -> Optional[str]:
        """Get ID of last selected preset"""
        return self.config.get("last_preset_id")

    def set_last_preset_id(self, preset_id: str):
        """Set last selected preset ID"""
        self.config["last_preset_id"] = preset_id

    # === Reset on Close Setting ===

    def get_reset_on_close(self) -> bool:
        """Get reset_on_close setting"""
        return self.config.get("reset_on_close", True)  # Default to True

    def set_reset_on_close(self, value: bool):
        """Set reset_on_close setting and save"""
        self.config["reset_on_close"] = value
        self.save_config()

    # === Preset Management ===

    def get_all_presets(self) -> List[FilterPreset]:
        """Get all presets"""
        return [FilterPreset.from_dict(p) for p in self.config.get("presets", [])]

    def get_preset_by_id(self, preset_id: str) -> Optional[FilterPreset]:
        """Get preset by ID"""
        for preset_dict in self.config.get("presets", []):
            if preset_dict.get("id") == preset_id:
                return FilterPreset.from_dict(preset_dict)
        return None

    def add_preset(self, preset: FilterPreset):
        """Add a new preset"""
        if "presets" not in self.config:
            self.config["presets"] = []
        self.config["presets"].append(preset.to_dict())

    def update_preset(self, preset: FilterPreset):
        """Update an existing preset"""
        presets = self.config.get("presets", [])
        for i, p in enumerate(presets):
            if p.get("id") == preset.id:
                presets[i] = preset.to_dict()
                return

    def delete_preset(self, preset_id: str):
        """Delete a preset by ID"""
        self.config["presets"] = [
            p for p in self.config.get("presets", [])
            if p.get("id") != preset_id
        ]

    def set_all_presets(self, presets: List[FilterPreset]):
        """Replace all presets"""
        self.config["presets"] = [p.to_dict() for p in presets]
