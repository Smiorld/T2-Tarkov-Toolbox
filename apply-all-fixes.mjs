import { readFileSync, writeFileSync } from 'fs';

// 读取文件
let content = readFileSync('src/pages/ScreenFilter.tsx', 'utf8');

// 1. 在handleSliderChange之前添加转换函数
const conversionFunctions = `    // UI值转换为后端值
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

`;

content = content.replace(
    '    const handleSliderChange = async (key: keyof FilterConfig, value: number) => {',
    conversionFunctions + '    const handleSliderChange = async (key: keyof FilterConfig, value: number) => {'
);

// 2. 更新handleReset函数以重新加载预设
content = content.replace(
    `    const handleReset = async () => {
        try {
            await invoke('reset_filter');
            setActivePresetId(null);

            // 重置后显示默认预设的配置
            const defaultPreset = presets.find(p => p.id === 'default');
            if (defaultPreset) {
                setEditingPreset(defaultPreset);
            }
        } catch (error) {
            console.error('Failed to reset filter:', error);
        }
    };`,
    `    const handleReset = async () => {
        try {
            await invoke('reset_filter');
            setActivePresetId(null);

            // 重新加载预设列表以获取最新的系统预设值
            await loadPresets();

            // 重置后显示默认预设的配置
            const allPresets = await invoke<FilterPreset[]>('get_all_filter_presets');
            const defaultPreset = allPresets.find(p => p.id === 'default');
            if (defaultPreset) {
                setEditingPreset(defaultPreset);
            }
        } catch (error) {
            console.error('Failed to reset filter:', error);
        }
    };`
);

// 3. 更新亮度滑块
content = content.replace(
    /label="亮度 \(Brightness\)"\s+value=\{editingPreset\.config\.brightness\}\s+onChange=\{\(v\) => handleSliderChange\('brightness', v\)\}\s+min=\{0\} max=\{2\.0\} step=\{0\.01\}/,
    `label="亮度 (Brightness)"
                                        value={backendToUI('brightness', editingPreset.config.brightness)}
                                        onChange={(v) => handleSliderChange('brightness', uiToBackend('brightness', v))}
                                        min={-100} max={100} step={1}`
);

// 4. 更新对比度滑块
content = content.replace(
    /label="对比度 \(Contrast\)"\s+value=\{editingPreset\.config\.contrast\}\s+onChange=\{\(v\) => handleSliderChange\('contrast', v\)\}\s+min=\{0\.5\} max=\{1\.5\} step=\{0\.01\}/,
    `label="对比度 (Contrast)"
                                        value={backendToUI('contrast', editingPreset.config.contrast)}
                                        onChange={(v) => handleSliderChange('contrast', uiToBackend('contrast', v))}
                                        min={-50} max={50} step={1}`
);

// 5. 更新SliderControl组件
content = content.replace(
    'const [inputValue, setInputValue] = useState(value.toFixed(2));',
    `const decimals = step < 1 ? 2 : 0;
    const [inputValue, setInputValue] = useState(value.toFixed(decimals));`
);

content = content.replace(
    /useEffect\(\(\) => \{\s+setInputValue\(value\.toFixed\(2\)\);\s+\}, \[value\]\);/,
    `useEffect(() => {
        setInputValue(value.toFixed(decimals));
    }, [value, decimals]);`
);

content = content.replace(
    'setInputValue(clampedValue.toFixed(2));',
    'setInputValue(clampedValue.toFixed(decimals));'
);

// 替换第二个toFixed(2) - 在else分支中
const lines = content.split('\n');
let foundFirst = false;
for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('setInputValue(value.toFixed(2))') && !lines[i].includes('useState')) {
        if (foundFirst) {
            lines[i] = lines[i].replace('value.toFixed(2)', 'value.toFixed(decimals)');
            break;
        }
        foundFirst = true;
    }
}
content = lines.join('\n');

// 6. 更新输入框宽度
content = content.replace(
    'className="text-sm font-mono text-gray-500 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none w-8 text-right"',
    'className="text-sm font-mono text-gray-500 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none w-16 text-right"'
);

// 保存文件
writeFileSync('src/pages/ScreenFilter.tsx', content, 'utf8');

console.log('✅ File modified successfully!');
console.log('Changes applied:');
console.log('  - Added uiToBackend and backendToUI conversion functions');
console.log('  - Fixed handleReset to reload presets from backend');
console.log('  - Updated brightness slider: -100 to 100, step 1');
console.log('  - Updated contrast slider: -50 to 50, step 1');
console.log('  - Updated SliderControl to use dynamic decimals');
console.log('  - Updated input width from w-8 to w-16');
