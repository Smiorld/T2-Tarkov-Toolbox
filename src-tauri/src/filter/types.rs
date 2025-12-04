use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// 滤镜配置参数
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilterConfig {
    /// 亮度偏移 (-1.0 到 1.0, 默认 0.0)
    /// 正值增加亮度，负值降低亮度
    pub brightness: f64,

    /// 伽马值 (0.5 - 3.5, 默认 1.0)
    /// <1.0 提亮暗部，>1.0 压暗亮部
    pub gamma: f64,

    /// 对比度调整 (-0.5 到 0.5, 默认 0.0)
    /// 正值增强对比度，负值降低对比度
    pub contrast: f64,

    /// 红色通道缩放 (0.5 - 2.0, 默认 1.0)
    pub red_scale: f64,

    /// 绿色通道缩放 (0.5 - 2.0, 默认 1.0)
    pub green_scale: f64,

    /// 蓝色通道缩放 (0.5 - 2.0, 默认 1.0)
    pub blue_scale: f64,
}

impl Default for FilterConfig {
    fn default() -> Self {
        Self {
            brightness: 0.0,  // 亮度偏移默认为0
            gamma: 1.0,       // 伽马默认为1.0
            contrast: 0.0,    // 对比度偏移默认为0
            red_scale: 1.0,
            green_scale: 1.0,
            blue_scale: 1.0,
        }
    }
}

impl FilterConfig {
    /// 验证配置参数是否在有效范围内
    pub fn validate(&self) -> Result<(), String> {
        // 验证亮度偏移
        if self.brightness < -1.0 || self.brightness > 1.0 {
            return Err(format!("brightness 必须在 -1.0 到 1.0 之间，当前值: {}", self.brightness));
        }

        // 验证伽马值
        if self.gamma < 0.5 || self.gamma > 3.5 {
            return Err(format!("gamma 必须在 0.5 到 3.5 之间，当前值: {}", self.gamma));
        }

        // 验证对比度调整
        if self.contrast < -0.5 || self.contrast > 0.5 {
            return Err(format!("contrast 必须在 -0.5 到 0.5 之间，当前值: {}", self.contrast));
        }

        // 验证通道缩放
        let channels = [
            ("red_scale", self.red_scale),
            ("green_scale", self.green_scale),
            ("blue_scale", self.blue_scale),
        ];

        for (name, value) in channels.iter() {
            if *value < 0.5 || *value > 2.0 {
                return Err(format!("{} 必须在 0.5 到 2.0 之间，当前值: {}", name, value));
            }
        }

        Ok(())
    }

    /// 计算颜色值（应用亮度、伽马、对比度）
    ///
    /// 参数映射（符合行业标准）：
    /// - gamma: 0.5-3.5 (伽马指数，1.0为线性)
    /// - brightness: -1.0到1.0 (亮度偏移，0.0为不变)
    /// - contrast: -0.5到0.5 (对比度调整，0.0为不变)
    ///
    /// 处理顺序：对比度 -> 伽马 -> 亮度 -> 通道缩放
    pub fn calculate_color_value(&self, channel_scale: f64, index: usize) -> u16 {
        // 基础值 (0-255 映射到 0-1)
        let base = index as f64 / 255.0;

        // 1. 应用对比度调整 (调整斜率)
        // contrast为0时，斜率为1.0（不变）
        // contrast为正时，增强对比度（斜率>1）
        // contrast为负时，降低对比度（斜率<1）
        let contrast_factor = 1.0 + self.contrast;
        let contrasted = ((base - 0.5) * contrast_factor + 0.5).max(0.0).min(1.0);

        // 2. 应用伽马校正
        let gamma_corrected = contrasted.powf(1.0 / self.gamma);

        // 3. 应用亮度偏移 (加法，确保不会超出范围)
        let brightened = (gamma_corrected + self.brightness).max(0.0).min(1.0);

        // 4. 应用通道缩放
        let final_value = (brightened * channel_scale).max(0.0).min(1.0);

        // 转换为 u16 (0-65535)
        (final_value * 65535.0) as u16
    }
}

/// 滤镜预设
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilterPreset {
    /// 预设 ID（唯一标识符）
    pub id: String,

    /// 预设名称
    pub name: String,

    /// 快捷键（可选，例如 "F2"）
    pub hotkey: Option<String>,

    /// 滤镜配置
    pub config: FilterConfig,

    /// 是否为默认预设（默认预设不可删除）
    pub is_default: bool,
}

impl FilterPreset {
    /// 创建新的自定义预设
    pub fn new(id: String, name: String, config: FilterConfig) -> Self {
        Self {
            id,
            name,
            hotkey: None,
            config,
            is_default: false,
        }
    }

    /// 创建默认预设
    pub fn new_default(id: String, name: String, hotkey: Option<String>, config: FilterConfig) -> Self {
        Self {
            id,
            name,
            hotkey,
            config,
            is_default: true,
        }
    }
}

/// 预设集合（管理所有预设）
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PresetCollection {
    /// 所有预设（key: preset_id, value: FilterPreset）
    pub presets: HashMap<String, FilterPreset>,

    /// 当前激活的预设 ID
    pub active_preset_id: Option<String>,
}

impl Default for PresetCollection {
    fn default() -> Self {
        let mut presets = HashMap::new();

        // 默认预设 1: 标准
        presets.insert(
            "default".to_string(),
            FilterPreset::new_default(
                "default".to_string(),
                "默认".to_string(),
                Some("F2".to_string()),
                FilterConfig::default(),
            ),
        );

        // 默认预设 2: 白天
        presets.insert(
            "daytime".to_string(),
            FilterPreset::new_default(
                "daytime".to_string(),
                "白天".to_string(),
                Some("F3".to_string()),
                FilterConfig {
                    brightness: 0.05,   // 微增亮度
                    gamma: 1.2,         // 轻微提亮暗部
                    contrast: 0.05,     // 微增对比度
                    ..FilterConfig::default()
                },
            ),
        );

        // 默认预设 3: 夜间
        presets.insert(
            "nighttime".to_string(),
            FilterPreset::new_default(
                "nighttime".to_string(),
                "夜间".to_string(),
                Some("F4".to_string()),
                FilterConfig {
                    brightness: 0.3,    // 明显增加亮度
                    gamma: 0.7,         // 提亮暗部（<1.0）
                    contrast: 0.15,     // 增强对比度
                    ..FilterConfig::default()
                },
            ),
        );

        Self {
            presets,
            active_preset_id: Some("default".to_string()),
        }
    }
}

impl PresetCollection {
    /// 添加或更新预设
    pub fn upsert_preset(&mut self, preset: FilterPreset) {
        self.presets.insert(preset.id.clone(), preset);
    }

    /// 删除预设（不能删除默认预设）
    pub fn delete_preset(&mut self, preset_id: &str) -> Result<(), String> {
        if let Some(preset) = self.presets.get(preset_id) {
            if preset.is_default {
                return Err("不能删除默认预设".to_string());
            }
        }

        self.presets
            .remove(preset_id)
            .ok_or_else(|| "预设不存在".to_string())?;

        // 如果删除的是当前激活的预设，切换到默认预设
        if self.active_preset_id.as_deref() == Some(preset_id) {
            self.active_preset_id = Some("default".to_string());
        }

        Ok(())
    }

    /// 获取预设
    pub fn get_preset(&self, preset_id: &str) -> Option<&FilterPreset> {
        self.presets.get(preset_id)
    }

    /// 获取当前激活的预设
    pub fn get_active_preset(&self) -> Option<&FilterPreset> {
        self.active_preset_id
            .as_ref()
            .and_then(|id| self.presets.get(id))
    }

    /// 设置激活的预设
    pub fn set_active_preset(&mut self, preset_id: &str) -> Result<(), String> {
        if !self.presets.contains_key(preset_id) {
            return Err("预设不存在".to_string());
        }
        self.active_preset_id = Some(preset_id.to_string());
        Ok(())
    }

    /// 验证快捷键是否冲突
    pub fn validate_hotkey(&self, hotkey: &str, exclude_preset_id: Option<&str>) -> Result<(), String> {
        for (id, preset) in &self.presets {
            // 跳过要排除的预设（用于更新预设时）
            if let Some(exclude_id) = exclude_preset_id {
                if id == exclude_id {
                    continue;
                }
            }

            if let Some(existing_hotkey) = &preset.hotkey {
                if existing_hotkey == hotkey {
                    return Err(format!(
                        "快捷键 {} 已被预设 '{}' 使用",
                        hotkey, preset.name
                    ));
                }
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = FilterConfig::default();
        assert_eq!(config.brightness, 1.0);
        assert_eq!(config.gamma, 1.0);
        assert_eq!(config.contrast, 1.0);
    }

    #[test]
    fn test_config_validation() {
        let mut config = FilterConfig::default();
        assert!(config.validate().is_ok());

        config.brightness = 2.5;
        assert!(config.validate().is_err());

        config.brightness = 0.3;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_preset_collection_default() {
        let collection = PresetCollection::default();
        assert_eq!(collection.presets.len(), 3);
        assert!(collection.presets.contains_key("default"));
        assert!(collection.presets.contains_key("daytime"));
        assert!(collection.presets.contains_key("nighttime"));
    }

    #[test]
    fn test_delete_default_preset() {
        let mut collection = PresetCollection::default();
        let result = collection.delete_preset("default");
        assert!(result.is_err());
    }

    #[test]
    fn test_hotkey_validation() {
        let collection = PresetCollection::default();
        // F2 被默认预设占用
        assert!(collection.validate_hotkey("F2", None).is_err());
        // F5 未被占用
        assert!(collection.validate_hotkey("F5", None).is_ok());
        // 更新预设时可以保留自己的快捷键
        assert!(collection.validate_hotkey("F2", Some("default")).is_ok());
    }
}
