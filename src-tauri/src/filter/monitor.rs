use serde::{Deserialize, Serialize};

/// 显示器信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonitorInfo {
    pub index: usize,
    pub name: String,
    pub device_name: String,
    pub is_primary: bool,
}

#[cfg(target_os = "windows")]
pub fn enumerate_monitors() -> Result<Vec<MonitorInfo>, String> {
    use windows::Win32::Graphics::Gdi::{
        EnumDisplayDevicesW, DISPLAY_DEVICEW, DISPLAY_DEVICE_ACTIVE,
        DISPLAY_DEVICE_ATTACHED_TO_DESKTOP, DISPLAY_DEVICE_PRIMARY_DEVICE,
    };
    use windows::core::PCWSTR;

    let mut monitors = Vec::new();
    let mut adapter_index = 0u32;

    // 第一层：枚举显卡适配器
    loop {
        let mut adapter_device: DISPLAY_DEVICEW = unsafe { std::mem::zeroed() };
        adapter_device.cb = std::mem::size_of::<DISPLAY_DEVICEW>() as u32;

        let success = unsafe {
            EnumDisplayDevicesW(
                PCWSTR::null(),
                adapter_index,
                &mut adapter_device,
                0,
            )
        };

        if !success.as_bool() {
            break;
        }

        let adapter_name = unsafe {
            let len = adapter_device.DeviceName.iter()
                .position(|&c| c == 0)
                .unwrap_or(adapter_device.DeviceName.len());
            String::from_utf16_lossy(&adapter_device.DeviceName[..len])
        };

        // 第二层：枚举该适配器下连接的显示器
        let mut monitor_index = 0u32;
        loop {
            let mut monitor_device: DISPLAY_DEVICEW = unsafe { std::mem::zeroed() };
            monitor_device.cb = std::mem::size_of::<DISPLAY_DEVICEW>() as u32;

            let adapter_name_wide: Vec<u16> = adapter_name.encode_utf16().chain(std::iter::once(0)).collect();
            
            let success = unsafe {
                EnumDisplayDevicesW(
                    PCWSTR(adapter_name_wide.as_ptr()),
                    monitor_index,
                    &mut monitor_device,
                    0,
                )
            };

            if !success.as_bool() {
                break;
            }

            // 只处理连接到桌面的激活显示器
            if (monitor_device.StateFlags & DISPLAY_DEVICE_ATTACHED_TO_DESKTOP != 0) &&
               (monitor_device.StateFlags & DISPLAY_DEVICE_ACTIVE != 0) {
                
                let monitor_string = unsafe {
                    let len = monitor_device.DeviceString.iter()
                        .position(|&c| c == 0)
                        .unwrap_or(monitor_device.DeviceString.len());
                    String::from_utf16_lossy(&monitor_device.DeviceString[..len])
                };

                let is_primary = adapter_device.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE != 0 
                    && monitor_index == 0;

                let display_name = if monitor_string.is_empty() {
                    if is_primary {
                        format!("显示器 {} (主)", monitors.len() + 1)
                    } else {
                        format!("显示器 {}", monitors.len() + 1)
                    }
                } else {
                    if is_primary {
                        format!("{} (主)", monitor_string)
                    } else {
                        monitor_string
                    }
                };

                monitors.push(MonitorInfo {
                    index: monitors.len(),
                    name: display_name,
                    device_name: adapter_name.clone(),
                    is_primary,
                });
            }

            monitor_index += 1;
            if monitor_index > 8 {
                break;
            }
        }

        adapter_index += 1;
        if adapter_index > 8 {
            break;
        }
    }

    if monitors.is_empty() {
        // 如果没有找到显示器，返回默认的主显示器
        monitors.push(MonitorInfo {
            index: 0,
            name: "主显示器".to_string(),
            device_name: "\\\\.\\DISPLAY1".to_string(),
            is_primary: true,
        });
    }

    Ok(monitors)
}

#[cfg(not(target_os = "windows"))]
pub fn enumerate_monitors() -> Result<Vec<MonitorInfo>, String> {
    Err("显示器枚举仅支持 Windows 平台".to_string())
}

/// 获取指定显示器的设备名称
#[cfg(target_os = "windows")]
pub fn get_monitor_device_name(monitor_index: usize) -> Result<String, String> {
    use windows::Win32::Graphics::Gdi::{
        EnumDisplayDevicesW, DISPLAY_DEVICEW, DISPLAY_DEVICE_ACTIVE,
    };
    use windows::core::PCWSTR;

    let mut current_index = 0usize;
    let mut api_index = 0u32;

    loop {
        let mut display_device: DISPLAY_DEVICEW = unsafe { std::mem::zeroed() };
        display_device.cb = std::mem::size_of::<DISPLAY_DEVICEW>() as u32;

        let success = unsafe {
            EnumDisplayDevicesW(
                PCWSTR::null(),
                api_index,
                &mut display_device,
                0,
            )
        };

        if !success.as_bool() {
            break;
        }

        // 只处理激活的显示器
        if display_device.StateFlags & DISPLAY_DEVICE_ACTIVE != 0 {
            if current_index == monitor_index {
                let device_name = unsafe {
                    let len = display_device.DeviceName.iter()
                        .position(|&c| c == 0)
                        .unwrap_or(display_device.DeviceName.len());
                    String::from_utf16_lossy(&display_device.DeviceName[..len])
                };
                return Ok(device_name);
            }
            current_index += 1;
        }

        api_index += 1;

        if api_index > 16 {
            break;
        }
    }

    Err(format!("显示器索引 {} 不存在", monitor_index))
}

#[cfg(not(target_os = "windows"))]
pub fn get_monitor_device_name(_monitor_index: usize) -> Result<String, String> {
    Err("显示器枚举仅支持 Windows 平台".to_string())
}
