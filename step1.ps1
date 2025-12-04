# 读取文件
$content = Get-Content "src\pages\ScreenFilter.tsx" -Raw

# 在第226行之前插入转换函数
$lines = $content -split "`r`n"
$insertIndex = 225  # 0-based index for line 226

$newLines = @(
    "    // UI值转换为后端值",
    "    const uiToBackend = (key: keyof FilterConfig, uiValue: number): number => {",
    "        switch (key) {",
    "            case 'brightness':",
    "                return uiValue / 100; // -100~100 -> -1.0~1.0",
    "            case 'contrast':",
    "                return uiValue / 100; // -50~50 -> -0.5~0.5",
    "            default:",
    "                return uiValue;",
    "        }",
    "    };",
    "",
    "    // 后端值转换为UI值",
    "    const backendToUI = (key: keyof FilterConfig, backendValue: number): number => {",
    "        switch (key) {",
    "            case 'brightness':",
    "                return backendValue * 100; // -1.0~1.0 -> -100~100",
    "            case 'contrast':",
    "                return backendValue * 100; // -0.5~0.5 -> -50~50",
    "            default:",
    "                return backendValue;",
    "        }",
    "    };",
    ""
)

$lines = $lines[0..($insertIndex - 1)] + $newLines + $lines[$insertIndex..($lines.Length - 1)]

# 保存
$lines -join "`r`n" | Set-Content "src\pages\ScreenFilter.tsx" -NoNewline

Write-Host "Step 1: Added conversion functions"
