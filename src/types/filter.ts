// 滤镜配置类型
export interface FilterConfig {
  brightness: number; // 0.5 - 2.0
  gamma: number; // 0.5 - 2.0
  contrast: number; // 0.5 - 2.0
  red_scale: number; // 0.5 - 2.0
  green_scale: number; // 0.5 - 2.0
  blue_scale: number; // 0.5 - 2.0
}

// 滤镜预设类型
export interface FilterPreset {
  id: string;
  name: string;
  hotkey: string | null;
  config: FilterConfig;
  is_default: boolean;
}

// 预设集合类型
export interface PresetCollection {
  presets: Record<string, FilterPreset>;
  active_preset_id: string | null;
}

// 显示器信息类型
export interface MonitorInfo {
  index: number;
  name: string;
  device_name: string;
  is_primary: boolean;
}

// 默认配置
export const DEFAULT_FILTER_CONFIG: FilterConfig = {
  brightness: 1.0,
  gamma: 1.0,
  contrast: 1.0,
  red_scale: 1.0,
  green_scale: 1.0,
  blue_scale: 1.0,
};

// 参数范围
export const FILTER_PARAM_RANGE = {
  min: 0.5,
  max: 2.0,
  step: 0.01,
};
