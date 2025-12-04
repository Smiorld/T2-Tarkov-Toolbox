// 验证所有UI范围值的有效性

use std::f64;

// 模拟FilterConfig的calculate_color_value函数
fn calculate_color_value(brightness: f64, gamma: f64, contrast: f64, index: usize) -> u16 {
    let base = index as f64 / 255.0;

    // 1. 对比度
    let contrast_factor = 1.0 + contrast;
    let contrasted = ((base - 0.5) * contrast_factor + 0.5).max(0.0).min(1.0);

    // 2. 伽马
    let gamma_corrected = contrasted.powf(1.0 / gamma);

    // 3. 亮度 (乘法)
    let brightness_factor = 1.0 + brightness;
    let brightened = (gamma_corrected * brightness_factor).max(0.0).min(1.0);

    // 转换为 u16
    (brightened * 65535.0) as u16
}

fn main() {
    println!("=== 验证UI范围的所有极限值 ===\n");

    // 测试用例
    let test_cases = vec![
        ("最小值", -1.0, 0.5, -0.5),
        ("最大值", 1.0, 3.5, 0.5),
        ("全黑 (亮度-100)", -1.0, 1.0, 0.0),
        ("超亮 (亮度100)", 1.0, 1.0, 0.0),
        ("高对比度", 0.0, 1.0, 0.5),
        ("低对比度", 0.0, 1.0, -0.5),
        ("极端组合1", 1.0, 0.5, 0.5),
        ("极端组合2", -0.5, 3.5, 0.25),
        ("夜间预设", 0.55, 1.95, 0.22),
        ("白天预设", 0.03, 1.5, 0.05),
    ];

    for (name, brightness, gamma, contrast) in test_cases {
        println!("测试: {}", name);
        println!("  参数: brightness={:.2}, gamma={:.2}, contrast={:.2}", brightness, gamma, contrast);
        
        let val_0 = calculate_color_value(brightness, gamma, contrast, 0);
        let val_127 = calculate_color_value(brightness, gamma, contrast, 127);
        let val_255 = calculate_color_value(brightness, gamma, contrast, 255);
        
        println!("  Gamma Ramp:");
        println!("    index=0:   {}", val_0);
        println!("    index=127: {}", val_127);
        println!("    index=255: {}", val_255);
        
        // 检查有效性
        let is_valid = val_0 <= val_255; // 应该是递增的
        let has_range = val_255 > val_0; // 应该有动态范围
        
        if !is_valid {
            println!("  ⚠️  警告: 非单调递增!");
        }
        if !has_range && brightness > -0.99 {
            println!("  ⚠️  警告: 无动态范围!");
        }
        if is_valid && has_range {
            println!("  ✓ 有效");
        }
        println!();
    }

    // 测试边界条件
    println!("\n=== 边界条件测试 ===");
    
    // 测试brightness_factor是否会为负
    for brightness in [-1.0, -0.5, 0.0, 0.5, 1.0] {
        let factor = 1.0 + brightness;
        println!("brightness={:.1} → factor={:.1} {}", 
            brightness, 
            factor,
            if factor >= 0.0 { "✓" } else { "⚠️ 负数!" }
        );
    }

    println!("\n=== 所有整数UI值快速扫描 ===");
    let mut has_issues = false;
    
    // 亮度: -100 到 100
    for ui_brightness in -100..=100 {
        let brightness = ui_brightness as f64 / 100.0;
        
        // 对比度: -50 到 50
        for ui_contrast in -50..=50 {
            let contrast = ui_contrast as f64 / 100.0;
            
            // 伽马: 测试几个关键点
            for ui_gamma_x10 in [5, 10, 20, 30, 35] { // 0.5, 1.0, 2.0, 3.0, 3.5
                let gamma = ui_gamma_x10 as f64 / 10.0;
                
                // 计算几个关键点
                let v0 = calculate_color_value(brightness, gamma, contrast, 0);
                let v255 = calculate_color_value(brightness, gamma, contrast, 255);
                
                // 检查是否有效
                if v0 > v255 && brightness > -0.99 {
                    println!("⚠️  发现问题: brightness={}, contrast={}, gamma={} → v0={} > v255={}",
                        brightness, contrast, gamma, v0, v255);
                    has_issues = true;
                }
            }
        }
    }
    
    if !has_issues {
        println!("✓ 所有整数UI值组合均有效!");
    }
}
