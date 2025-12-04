import { invoke } from '@tauri-apps/api/core';
import type { FilterConfig, FilterPreset, MonitorInfo } from '../types/filter';

// Tauri 命令封装

export const filterApi = {
  // 获取所有预设
  getAllPresets: async (): Promise<FilterPreset[]> => {
    return invoke('get_all_filter_presets');
  },

  // 获取单个预设
  getPreset: async (presetId: string): Promise<FilterPreset> => {
    return invoke('get_filter_preset', { presetId });
  },

  // 创建新预设
  createPreset: async (
    name: string,
    config: FilterConfig,
    hotkey?: string
  ): Promise<string> => {
    return invoke('create_filter_preset', { name, config, hotkey });
  },

  // 更新预设
  updatePreset: async (
    presetId: string,
    name?: string,
    config?: FilterConfig,
    hotkey?: string | null
  ): Promise<void> => {
    return invoke('update_filter_preset', {
      presetId,
      name,
      config,
      hotkey,
    });
  },

  // 删除预设
  deletePreset: async (presetId: string): Promise<void> => {
    return invoke('delete_filter_preset', { presetId });
  },

  // 重命名预设
  renamePreset: async (presetId: string, newName: string): Promise<void> => {
    return invoke('rename_filter_preset', { presetId, newName });
  },

  // 应用预设
  applyPreset: async (presetId: string): Promise<void> => {
    return invoke('apply_filter_preset', { presetId });
  },

  // 直接应用滤镜配置（临时预览，不保存）
  applyFilterConfig: async (config: FilterConfig): Promise<void> => {
    return invoke('apply_filter_config', { config });
  },

  // 获取当前激活的预设
  getActivePreset: async (): Promise<FilterPreset | null> => {
    return invoke('get_active_filter_preset');
  },

  // 重置滤镜
  resetFilter: async (): Promise<void> => {
    return invoke('reset_filter');
  },

  // 导出预设
  exportPresets: async (): Promise<string> => {
    return invoke('export_filter_presets');
  },

  // 导入预设
  importPresets: async (json: string): Promise<void> => {
    return invoke('import_filter_presets', { json });
  },

  // 重置为默认预设
  resetToDefaults: async (): Promise<void> => {
    return invoke('reset_filter_presets_to_defaults');
  },

  // 获取显示器列表
  getMonitors: async (): Promise<MonitorInfo[]> => {
    return invoke('get_monitors');
  },
};
