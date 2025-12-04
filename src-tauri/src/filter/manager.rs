use crate::filter::{GammaRampController, FilterConfig, FilterPreset, PresetCollection};
use std::sync::{Arc, Mutex};
use std::fs;
use std::path::PathBuf;

/// 滤镜管理器
pub struct FilterManager {
    /// Gamma Ramp 控制器
    controller: Arc<Mutex<GammaRampController>>,

    /// 预设集合
    presets: Arc<Mutex<PresetCollection>>,

    /// 配置文件路径
    config_path: PathBuf,
}

impl FilterManager {
    /// 创建新的滤镜管理器
    pub fn new(config_dir: PathBuf) -> Result<Self, String> {
        // 确保配置目录存在
        fs::create_dir_all(&config_dir)
            .map_err(|e| format!("无法创建配置目录: {}", e))?;

        let config_path = config_dir.join("filter_presets.json");

        // 加载或创建预设集合
        let presets = if config_path.exists() {
            Self::load_presets(&config_path)?
        } else {
            let default_presets = PresetCollection::default();
            Self::save_presets(&config_path, &default_presets)?;
            default_presets
        };

        Ok(Self {
            controller: Arc::new(Mutex::new(GammaRampController::new())),
            presets: Arc::new(Mutex::new(presets)),
            config_path,
        })
    }

    /// 加载预设集合
    fn load_presets(path: &PathBuf) -> Result<PresetCollection, String> {
        let content = fs::read_to_string(path)
            .map_err(|e| format!("无法读取配置文件: {}", e))?;

        serde_json::from_str(&content)
            .map_err(|e| format!("配置文件格式错误: {}", e))
    }

    /// 保存预设集合
    fn save_presets(path: &PathBuf, presets: &PresetCollection) -> Result<(), String> {
        let content = serde_json::to_string_pretty(presets)
            .map_err(|e| format!("无法序列化配置: {}", e))?;

        fs::write(path, content)
            .map_err(|e| format!("无法写入配置文件: {}", e))
    }

    /// 持久化当前预设集合
    fn persist_presets(&self) -> Result<(), String> {
        let presets = self.presets.lock().unwrap();
        Self::save_presets(&self.config_path, &presets)
    }

    /// 获取所有预设
    pub fn get_all_presets(&self) -> Vec<FilterPreset> {
        let presets = self.presets.lock().unwrap();
        presets.presets.values().cloned().collect()
    }

    /// 获取预设
    pub fn get_preset(&self, preset_id: &str) -> Result<FilterPreset, String> {
        let presets = self.presets.lock().unwrap();
        presets
            .get_preset(preset_id)
            .cloned()
            .ok_or_else(|| "预设不存在".to_string())
    }

    /// 创建新预设
    pub fn create_preset(&self, name: String, config: FilterConfig, hotkey: Option<String>) -> Result<String, String> {
        let mut presets = self.presets.lock().unwrap();

        // 验证配置
        config.validate()?;

        // 验证快捷键
        if let Some(ref key) = hotkey {
            presets.validate_hotkey(key, None)?;
        }

        // 生成唯一 ID
        let id = format!("custom_{}", uuid::Uuid::new_v4().to_string());

        // 创建预设
        let preset = FilterPreset {
            id: id.clone(),
            name,
            hotkey,
            config,
            is_default: false,
        };

        presets.upsert_preset(preset);
        drop(presets);

        self.persist_presets()?;
        Ok(id)
    }

    /// 更新预设
    pub fn update_preset(&self, preset_id: &str, name: Option<String>, config: Option<FilterConfig>, hotkey: Option<Option<String>>) -> Result<(), String> {
        let mut presets = self.presets.lock().unwrap();

        // 获取现有预设
        let mut preset = presets
            .get_preset(preset_id)
            .cloned()
            .ok_or_else(|| "预设不存在".to_string())?;

        // 更新名称
        if let Some(new_name) = name {
            preset.name = new_name;
        }

        // 更新配置
        if let Some(new_config) = config {
            new_config.validate()?;
            preset.config = new_config;
        }

        // 更新快捷键
        if let Some(new_hotkey) = hotkey {
            if let Some(ref key) = new_hotkey {
                presets.validate_hotkey(key, Some(preset_id))?;
            }
            preset.hotkey = new_hotkey;
        }

        presets.upsert_preset(preset);
        drop(presets);

        self.persist_presets()?;
        Ok(())
    }

    /// 删除预设
    pub fn delete_preset(&self, preset_id: &str) -> Result<(), String> {
        let mut presets = self.presets.lock().unwrap();
        presets.delete_preset(preset_id)?;
        drop(presets);

        self.persist_presets()?;
        Ok(())
    }

    /// 重命名预设
    pub fn rename_preset(&self, preset_id: &str, new_name: String) -> Result<(), String> {
        self.update_preset(preset_id, Some(new_name), None, None)
    }

    /// 应用预设
    pub fn apply_preset(&self, preset_id: &str, monitor_devices: Vec<String>) -> Result<(), String> {
        let mut presets = self.presets.lock().unwrap();

        // 获取预设
        let preset = presets
            .get_preset(preset_id)
            .ok_or_else(|| "预设不存在".to_string())?;

        // 应用滤镜
        let mut controller = self.controller.lock().unwrap();
        if monitor_devices.is_empty() {
            return Err("未选择任何显示器".to_string());
        }
        
        // 应用到指定的显示器列表
        for device in monitor_devices {
            controller.apply_filter_to_monitor(&preset.config, &device)?;
        }

        // 设置为激活预设
        presets.set_active_preset(preset_id)?;
        drop(presets);

        self.persist_presets()?;
        Ok(())
    }

    /// 直接应用滤镜配置（用于实时预览，不保存为激活预设）
    pub fn apply_config(&self, config: &FilterConfig, monitor_devices: Vec<String>) -> Result<(), String> {
        // 验证配置
        config.validate()?;

        // 应用滤镜
        let mut controller = self.controller.lock().unwrap();
        if monitor_devices.is_empty() {
            return Err("未选择任何显示器".to_string());
        }
        
        for device in monitor_devices {
            controller.apply_filter_to_monitor(config, &device)?;
        }
        Ok(())
    }

    /// 获取当前激活的预设
    pub fn get_active_preset(&self) -> Option<FilterPreset> {
        let presets = self.presets.lock().unwrap();
        presets.get_active_preset().cloned()
    }

    /// 重置滤镜（恢复到系统默认）
    pub fn reset_filter(&self) -> Result<(), String> {
        let mut controller = self.controller.lock().unwrap();
        controller.reset()?;

        let mut presets = self.presets.lock().unwrap();
        presets.active_preset_id = None;
        drop(presets);

        self.persist_presets()?;
        Ok(())
    }

    /// 导出预设集合到 JSON 字符串
    pub fn export_presets(&self) -> Result<String, String> {
        let presets = self.presets.lock().unwrap();
        serde_json::to_string_pretty(&*presets)
            .map_err(|e| format!("导出失败: {}", e))
    }

    /// 从 JSON 字符串导入预设集合
    pub fn import_presets(&self, json: &str) -> Result<(), String> {
        let imported: PresetCollection = serde_json::from_str(json)
            .map_err(|e| format!("导入失败: {}", e))?;

        let mut presets = self.presets.lock().unwrap();
        *presets = imported;
        drop(presets);

        self.persist_presets()?;
        Ok(())
    }

    /// 重置为默认预设
    pub fn reset_to_defaults(&self) -> Result<(), String> {
        let default_presets = PresetCollection::default();
        let mut presets = self.presets.lock().unwrap();
        *presets = default_presets;
        drop(presets);

        self.persist_presets()?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_filter_manager_creation() {
        let temp_dir = env::temp_dir().join("t2_test_filter");
        let manager = FilterManager::new(temp_dir.clone());
        assert!(manager.is_ok());

        // 清理
        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_create_and_delete_preset() {
        let temp_dir = env::temp_dir().join("t2_test_filter_2");
        let manager = FilterManager::new(temp_dir.clone()).unwrap();

        // 创建预设
        let config = FilterConfig::default();
        let preset_id = manager.create_preset("测试预设".to_string(), config, None).unwrap();

        // 验证创建成功
        let preset = manager.get_preset(&preset_id);
        assert!(preset.is_ok());

        // 删除预设
        let result = manager.delete_preset(&preset_id);
        assert!(result.is_ok());

        // 验证删除成功
        let preset = manager.get_preset(&preset_id);
        assert!(preset.is_err());

        // 清理
        let _ = fs::remove_dir_all(temp_dir);
    }
}
