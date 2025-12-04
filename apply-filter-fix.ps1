# PowerShell script to modify ScreenFilter.tsx

$file = "src\pages\ScreenFilter.tsx"
$content = Get-Content $file -Raw -Encoding UTF8

# 1. Add conversion functions before handleSliderChange
$searchPattern = '    const handleSliderChange = async \(key: keyof FilterConfig, value: number\) => \{'
$replacement = @'
    // UI值转换为后端值
    const uiToBackend = (key: keyof FilterConfig, uiValue: number): number => {
        switch (key) {
            case 'brightness':
                return uiValue / 100; // -100~100 -> -1.0~1.0
            case 'contrast':
                return uiValue / 100; // -50~50 -> -0.5~0.5
            default:
                return uiValue;
        }
    };

    // 后端值转换为UI值
    const backendToUI = (key: keyof FilterConfig, backendValue: number): number => {
        switch (key) {
            case 'brightness':
                return backendValue * 100; // -1.0~1.0 -> -100~100
            case 'contrast':
                return backendValue * 100; // -0.5~0.5 -> -50~50
            default:
                return backendValue;
        }
    };

    const handleSliderChange = async (key: keyof FilterConfig, value: number) => {
'@
$content = $content -replace [regex]::Escape($searchPattern), $replacement

# 2. Update brightness slider
$content = $content -replace 'label="亮度 \(Brightness\)"[\s\S]*?value=\{editingPreset\.config\.brightness\}[\s\S]*?onChange=\{\(v\) => handleSliderChange\(''brightness'', v\)\}[\s\S]*?min=\{0\} max=\{2\.0\} step=\{0\.01\}', @'
label="亮度 (Brightness)"
                                        value={backendToUI('brightness', editingPreset.config.brightness)}
                                        onChange={(v) => handleSliderChange('brightness', uiToBackend('brightness', v))}
                                        min={-100} max={100} step={1}
'@

# 3. Update contrast slider
$content = $content -replace 'label="对比度 \(Contrast\)"[\s\S]*?value=\{editingPreset\.config\.contrast\}[\s\S]*?onChange=\{\(v\) => handleSliderChange\(''contrast'', v\)\}[\s\S]*?min=\{0\.5\} max=\{1\.5\} step=\{0\.01\}', @'
label="对比度 (Contrast)"
                                        value={backendToUI('contrast', editingPreset.config.contrast)}
                                        onChange={(v) => handleSliderChange('contrast', uiToBackend('contrast', v))}
                                        min={-50} max={50} step={1}
'@

# 4. Update SliderControl component
$content = $content -replace 'const \[inputValue, setInputValue\] = useState\(value\.toFixed\(2\)\);', @'
const decimals = step < 1 ? 2 : 0;
    const [inputValue, setInputValue] = useState(value.toFixed(decimals));
'@

$content = $content -replace 'useEffect\(\(\) => \{[\s]*setInputValue\(value\.toFixed\(2\)\);[\s]*\}, \[value\]\);', @'
useEffect(() => {
        setInputValue(value.toFixed(decimals));
    }, [value, decimals]);
'@

$content = $content -replace 'setInputValue\(clampedValue\.toFixed\(2\)\);', 'setInputValue(clampedValue.toFixed(decimals));'
$content = $content -replace 'setInputValue\(value\.toFixed\(2\)\);(?![\s]*\}[\s]*useEffect)', 'setInputValue(value.toFixed(decimals));'

# 5. Update input width
$content = $content -replace 'className="text-sm font-mono text-gray-500 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none w-8 text-right"', 'className="text-sm font-mono text-gray-500 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none w-16 text-right"'

# Save the file
$content | Set-Content $file -Encoding UTF8 -NoNewline

Write-Host "File modified successfully!"
