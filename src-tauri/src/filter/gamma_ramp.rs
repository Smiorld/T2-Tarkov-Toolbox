use crate::filter::types::FilterConfig;
use std::collections::HashMap;

#[cfg(target_os = "windows")]
use windows::Win32::{
    Foundation::BOOL,
    Graphics::Gdi::{HDC, CreateDCW, DeleteDC},
};
#[cfg(target_os = "windows")]
use windows::core::PCWSTR;

#[cfg(target_os = "windows")]
#[link(name = "gdi32")]
extern "system" {
    fn SetDeviceGammaRamp(hdc: HDC, lpRamp: *const std::ffi::c_void) -> BOOL;
    fn GetDeviceGammaRamp(hdc: HDC, lpRamp: *mut std::ffi::c_void) -> BOOL;
}

/// Gamma Ramp 结构体（Windows API 要求的格式）
#[repr(C)]
#[derive(Debug, Clone)]
pub struct GammaRamp {
    pub red: [u16; 256],
    pub green: [u16; 256],
    pub blue: [u16; 256],
}

impl Default for GammaRamp {
    fn default() -> Self {
        let mut ramp = Self {
            red: [0; 256],
            green: [0; 256],
            blue: [0; 256],
        };

        // 默认线性映射（使用与 from_config 相同的计算方式）
        for i in 0..256 {
            let value = ((i as f64 / 255.0) * 65535.0) as u16;
            ramp.red[i] = value;
            ramp.green[i] = value;
            ramp.blue[i] = value;
        }

        ramp
    }
}

impl GammaRamp {
    /// 从滤镜配置生成 Gamma Ramp
    pub fn from_config(config: &FilterConfig) -> Self {
        let mut ramp = Self {
            red: [0; 256],
            green: [0; 256],
            blue: [0; 256],
        };

        for i in 0..256 {
            ramp.red[i] = config.calculate_color_value(config.red_scale, i);
            ramp.green[i] = config.calculate_color_value(config.green_scale, i);
            ramp.blue[i] = config.calculate_color_value(config.blue_scale, i);
        }

        ramp
    }
}

/// Gamma Ramp 控制器
pub struct GammaRampController {
    #[cfg(target_os = "windows")]
    original_ramps: HashMap<String, GammaRamp>,
}

impl GammaRampController {
    pub fn new() -> Self {
        Self {
            #[cfg(target_os = "windows")]
            original_ramps: HashMap::new(),
        }
    }

    /// 应用滤镜配置
    #[cfg(target_os = "windows")]
    pub fn apply_filter(&mut self, config: &FilterConfig) -> Result<(), String> {
        // 验证配置
        config.validate()?;

        // 获取所有显示器
        let monitors = crate::filter::monitor::enumerate_monitors()?;
        
        if monitors.is_empty() {
             return Err("未找到任何显示器".to_string());
        }

        let mut errors = Vec::new();

        for monitor in monitors {
            // 保存原始 Gamma Ramp（仅第一次）
            if !self.original_ramps.contains_key(&monitor.device_name) {
                match self.get_ramp_for_monitor(&monitor.device_name) {
                    Ok(ramp) => {
                        self.original_ramps.insert(monitor.device_name.clone(), ramp);
                    }
                    Err(e) => {
                        eprintln!("警告：无法保存显示器 {} 的原始 Gamma Ramp: {}", monitor.name, e);
                        // 继续尝试应用，但可能无法恢复
                    }
                }
            }

            // 生成新的 Gamma Ramp
            let ramp = GammaRamp::from_config(config);

            // 应用到显示器
            if let Err(e) = self.set_ramp_for_monitor(&ramp, &monitor.device_name) {
                let err_msg = format!("显示器 {}: {}", monitor.name, e);
                eprintln!("{}", err_msg);
                errors.push(err_msg);
            }
        }

        if !errors.is_empty() {
            // 如果所有显示器都失败，则返回错误
            // 这里我们只要有一个成功就算成功，或者返回部分失败的警告？
            // 为了简单起见，如果报错，返回第一个错误
            return Err(format!("应用滤镜失败: {}", errors.join("; ")));
        }

        Ok(())
    }

    /// 重置到原始状态
    #[cfg(target_os = "windows")]
    pub fn reset(&mut self) -> Result<(), String> {
        let mut errors = Vec::new();
        
        // 遍历保存的原始 ramp 并恢复
        // 注意：这里我们需要 clone keys 来避免借用检查问题，或者使用迭代器
        let devices: Vec<String> = self.original_ramps.keys().cloned().collect();

        for device_name in devices {
            if let Some(original) = self.original_ramps.get(&device_name) {
                if let Err(e) = self.set_ramp_for_monitor(original, &device_name) {
                    errors.push(format!("无法重置显示器 {}: {}", device_name, e));
                }
            }
        }
        
        // 清空保存的记录？或者保留以便下次使用？
        // 通常 reset 意味着恢复到系统状态，所以清空是合理的，
        // 但如果用户再次应用滤镜，我们需要重新获取。
        self.original_ramps.clear();

        if !errors.is_empty() {
            return Err(errors.join("; "));
        }
        
        Ok(())
    }

    /// 获取指定显示器的 Gamma Ramp
    #[cfg(target_os = "windows")]
    fn get_ramp_for_monitor(&self, monitor_device: &str) -> Result<GammaRamp, String> {
        unsafe {
            // 将设备名转换为 UTF-16
            let device_name: Vec<u16> = monitor_device.encode_utf16().chain(std::iter::once(0)).collect();

            // 创建设备上下文
            let hdc = CreateDCW(
                PCWSTR(device_name.as_ptr()),
                PCWSTR::null(),
                PCWSTR::null(),
                None,
            );

            if hdc.is_invalid() {
                return Err(format!("无法为显示器 {} 创建设备上下文", monitor_device));
            }

            let mut ramp = GammaRamp::default();
            let result = GetDeviceGammaRamp(
                hdc,
                &mut ramp as *mut GammaRamp as *mut _,
            );

            // 释放设备上下文
            let _ = DeleteDC(hdc);

            if result.as_bool() {
                Ok(ramp)
            } else {
                Err(format!("无法获取显示器 {} 的 Gamma Ramp", monitor_device))
            }
        }
    }

    /// 为指定显示器设置 Gamma Ramp
    #[cfg(target_os = "windows")]
    fn set_ramp_for_monitor(&self, ramp: &GammaRamp, monitor_device: &str) -> Result<(), String> {
        unsafe {
            // 将设备名转换为 UTF-16
            let device_name: Vec<u16> = monitor_device.encode_utf16().chain(std::iter::once(0)).collect();

            // 创建设备上下文
            let hdc = CreateDCW(
                PCWSTR(device_name.as_ptr()),
                PCWSTR::null(),
                PCWSTR::null(),
                None,
            );

            if hdc.is_invalid() {
                return Err(format!("无法为显示器 {} 创建设备上下文", monitor_device));
            }

            // 设置 Gamma Ramp
            let result = SetDeviceGammaRamp(
                hdc,
                ramp as *const GammaRamp as *const _,
            );

            // 释放设备上下文
            let _ = DeleteDC(hdc);

            if result.as_bool() {
                Ok(())
            } else {
                Err(format!("无法为显示器 {} 设置 Gamma Ramp", monitor_device))
            }
        }
    }

    /// 应用滤镜到指定显示器 (保留接口，但内部实现已统一)
    #[cfg(target_os = "windows")]
    pub fn apply_filter_to_monitor(&mut self, config: &FilterConfig, monitor_device: &str) -> Result<(), String> {
        // 验证配置
        config.validate()?;
        
        // 保存原始 ramp
        if !self.original_ramps.contains_key(monitor_device) {
             match self.get_ramp_for_monitor(monitor_device) {
                Ok(ramp) => {
                    self.original_ramps.insert(monitor_device.to_string(), ramp);
                }
                Err(e) => return Err(e),
            }
        }

        // 生成新的 Gamma Ramp
        let ramp = GammaRamp::from_config(config);

        // 打印调试信息
        println!("生成的 Gamma Ramp 值:");
        println!("  index=0: R={}, G={}, B={}", ramp.red[0], ramp.green[0], ramp.blue[0]);
        println!("  index=127: R={}, G={}, B={}", ramp.red[127], ramp.green[127], ramp.blue[127]);
        println!("  index=255: R={}, G={}, B={}", ramp.red[255], ramp.green[255], ramp.blue[255]);

        // 应用到指定显示器
        self.set_ramp_for_monitor(&ramp, monitor_device)
    }

    /// 重置指定显示器的滤镜
    #[cfg(target_os = "windows")]
    pub fn reset_monitor(&mut self, monitor_device: &str) -> Result<(), String> {
        if let Some(original) = self.original_ramps.get(monitor_device) {
            self.set_ramp_for_monitor(original, monitor_device)
        } else {
            // 如果没有原始记录，尝试设置默认线性 ramp
            let default_ramp = GammaRamp::default();
            self.set_ramp_for_monitor(&default_ramp, monitor_device)
        }
    }

    /// 非 Windows 平台的占位实现
    #[cfg(not(target_os = "windows"))]
    pub fn apply_filter(&mut self, _config: &FilterConfig) -> Result<(), String> {
        Err("屏幕滤镜仅支持 Windows 平台".to_string())
    }

    #[cfg(not(target_os = "windows"))]
    pub fn reset(&mut self) -> Result<(), String> {
        Err("屏幕滤镜仅支持 Windows 平台".to_string())
    }

    #[cfg(not(target_os = "windows"))]
    pub fn apply_filter_to_monitor(&mut self, _config: &FilterConfig, _monitor_device: &str) -> Result<(), String> {
        Err("屏幕滤镜仅支持 Windows 平台".to_string())
    }

    #[cfg(not(target_os = "windows"))]
    pub fn reset_monitor(&mut self, _monitor_device: &str) -> Result<(), String> {
        Err("屏幕滤镜仅支持 Windows 平台".to_string())
    }
}

impl Drop for GammaRampController {
    fn drop(&mut self) {
        // 程序退出时自动重置
        let _ = self.reset();
    }
}

#[cfg(all(test, target_os = "windows"))]
mod tests {
    use super::*;

    #[test]
    fn test_gamma_ramp_default() {
        let ramp = GammaRamp::default();
        // 验证线性映射
        assert_eq!(ramp.red[0], 0);
        assert_eq!(ramp.red[255], 65280);
    }

    #[test]
    fn test_gamma_ramp_from_config() {
        let config = FilterConfig::default();
        let ramp = GammaRamp::from_config(&config);
        // 默认配置应该接近线性
        assert!(ramp.red[128] > 30000 && ramp.red[128] < 35000);
    }
}
