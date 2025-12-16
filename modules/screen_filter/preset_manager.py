import json
from typing import List, Optional
from modules.screen_filter.models import FilterPreset, FilterConfig
from utils.i18n import t

class PresetManager:
    def __init__(self, config_file: str = "filter_presets.json"):
        self.config_file = config_file
        self.presets: List[FilterPreset] = []
        self.load_presets()

    def load_presets(self):
        """Load presets from JSON file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.presets = [FilterPreset.from_dict(p) for p in data.get('presets', [])]
        except FileNotFoundError:
            # Create default presets if file doesn't exist
            self.presets = self._create_default_presets()
            self.save_presets()
        except Exception as e:
            print(f"Error loading presets: {e}")
            self.presets = self._create_default_presets()

    def save_presets(self):
        """Save presets to JSON file"""
        try:
            data = {
                'presets': [p.to_dict() for p in self.presets]
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving presets: {e}")

    def get_all_presets(self) -> List[FilterPreset]:
        """Get all presets"""
        return self.presets

    def get_preset_by_id(self, preset_id: str) -> Optional[FilterPreset]:
        """Get preset by ID"""
        for preset in self.presets:
            if preset.id == preset_id:
                return preset
        return None

    def add_preset(self, preset: FilterPreset):
        """Add a new preset"""
        self.presets.append(preset)
        self.save_presets()

    def update_preset(self, preset: FilterPreset):
        """Update an existing preset"""
        for i, p in enumerate(self.presets):
            if p.id == preset.id:
                self.presets[i] = preset
                self.save_presets()
                return

    def delete_preset(self, preset_id: str):
        """Delete a preset by ID"""
        self.presets = [p for p in self.presets if p.id != preset_id]
        self.save_presets()

    def _create_default_presets(self) -> List[FilterPreset]:
        """Create default presets with user-calibrated algorithm values"""
        return [
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
                    blue_scale=1.0
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
                    blue_scale=1.0
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
                    blue_scale=1.0
                ),
                is_default=True
            )
        ]
