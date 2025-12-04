import json
from typing import List, Optional
from modules.screen_filter.models import FilterPreset, FilterConfig

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
        """Create default presets"""
        return [
            FilterPreset(
                id="default",
                name="默认",
                hotkey="F2",
                config=FilterConfig(
                    brightness=0.0,
                    gamma=1.0,
                    contrast=0.0,
                    red_scale=1.0,
                    green_scale=1.0,
                    blue_scale=1.0
                ),
                is_default=True
            ),
            FilterPreset(
                id="daytime",
                name="白天",
                hotkey="F3",
                config=FilterConfig(
                    brightness=0.03,
                    gamma=1.5,
                    contrast=0.05,
                    red_scale=1.0,
                    green_scale=1.0,
                    blue_scale=1.0
                ),
                is_default=True
            ),
            FilterPreset(
                id="nighttime",
                name="夜间",
                hotkey="F4",
                config=FilterConfig(
                    brightness=0.55,
                    gamma=1.95,
                    contrast=0.22,
                    red_scale=1.0,
                    green_scale=1.0,
                    blue_scale=1.0
                ),
                is_default=True
            )
        ]
