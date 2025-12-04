import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

interface FilterConfig {
    brightness: number;
    gamma: number;
    contrast: number;
    red_scale: number;
    green_scale: number;
    blue_scale: number;
}

interface FilterPreset {
    id: string;
    name: string;
    hotkey: string | null;
    config: FilterConfig;
    is_default: boolean;
}

interface MonitorInfo {
    index: number;
    name: string;
    device_name: string;
    is_primary: boolean;
}

const MONITOR_SELECTION_KEY = 'screen_filter_monitor_selection';

export default function ScreenFilter() {
    const [presets, setPresets] = useState<FilterPreset[]>([]);
    const [activePresetId, setActivePresetId] = useState<string | null>(null);
    const [editingPreset, setEditingPreset] = useState<FilterPreset | null>(null);
    const [monitors, setMonitors] = useState<MonitorInfo[]>([]);
    const [selectedMonitorIds, setSelectedMonitorIds] = useState<string[]>([]);
    const [listeningForHotkey, setListeningForHotkey] = useState<string | null>(null);


    useEffect(() => {
        loadPresets();
        loadActivePreset();
        loadMonitors();
    }, []);

    // 监听后端快捷键触发事件
    useEffect(() => {
        const unlisten = listen<string>('preset-applied', async (event) => {
            const presetId = event.payload;
            console.log('Backend preset applied:', presetId);

            // 更新激活的预设ID
            setActivePresetId(presetId);

            // 重新从后端获取预设列表，避免闭包陷阱
            try {
                const allPresets = await invoke<FilterPreset[]>('get_all_filter_presets');
                const preset = allPresets.find(p => p.id === presetId);
                if (preset) {
                    setEditingPreset(preset);
                }
            } catch (error) {
                console.error('Failed to load preset:', error);
            }
        });

        return () => {
            unlisten.then(fn => fn());
        };
    }, []);

    // 键盘监听：捕获快捷键绑定
    useEffect(() => {
        if (!listeningForHotkey) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            e.preventDefault();
            e.stopPropagation();

            // ESC 取消
            if (e.key === 'Escape') {
                setListeningForHotkey(null);
                return;
            }

            // 构建快捷键字符串
            const modifiers: string[] = [];
            if (e.ctrlKey) modifiers.push('Ctrl');
            if (e.altKey) modifiers.push('Alt');
            if (e.shiftKey) modifiers.push('Shift');
            if (e.metaKey) modifiers.push('Meta');

            // 获取按键名称
            let keyName = e.key;
            if (keyName === ' ') keyName = 'Space';
            else if (keyName.length === 1) keyName = keyName.toUpperCase();
            else if (keyName.startsWith('Arrow')) keyName = keyName.substring(5);

            // 跳过单独的修饰键
            if (['Control', 'Alt', 'Shift', 'Meta'].includes(keyName)) return;

            // 组合快捷键字符串
            const hotkeyString = modifiers.length > 0
                ? `${modifiers.join('+')}+${keyName}`
                : keyName;

            // 更新快捷键
            updatePresetHotkey(listeningForHotkey, hotkeyString);
            setListeningForHotkey(null);
        };

        window.addEventListener('keydown', handleKeyDown, true);
        return () => window.removeEventListener('keydown', handleKeyDown, true);
    }, [listeningForHotkey]);

    const loadPresets = async () => {
        try {
            const result = await invoke<FilterPreset[]>('get_all_filter_presets');
            const sorted = result.sort((a, b) => {
                if (a.is_default && !b.is_default) return -1;
                if (!a.is_default && b.is_default) return 1;
                return a.name.localeCompare(b.name);
            });
            setPresets(sorted);
        } catch (error) {
            console.error('Failed to load presets:', error);
        }
    };

    const loadActivePreset = async () => {
        try {
            const result = await invoke<FilterPreset | null>('get_active_filter_preset');
            if (result) {
                setActivePresetId(result.id);
                if (!editingPreset) {
                    setEditingPreset(result);
                }
            }
        } catch (error) {
            console.error('Failed to load active preset:', error);
        }
    };

    const loadMonitors = async () => {
        try {
            const result = await invoke<MonitorInfo[]>('get_monitors');
            setMonitors(result);

            const saved = localStorage.getItem(MONITOR_SELECTION_KEY);
            if (saved) {
                try {
                    const { monitorCount, selection } = JSON.parse(saved);
                    if (monitorCount === result.length) {
                        setSelectedMonitorIds(selection);
                        return;
                    }
                } catch (e) {
                    console.error('Failed to parse saved monitor selection:', e);
                }
            }

            const primaryMonitor = result.find(m => m.is_primary);
            if (primaryMonitor) {
                setSelectedMonitorIds([primaryMonitor.device_name]);
            } else if (result.length > 0) {
                setSelectedMonitorIds([result[0].device_name]);
            }
        } catch (error) {
            console.error('Failed to load monitors:', error);
        }
    };

    const handleMonitorToggle = (deviceName: string) => {
        setSelectedMonitorIds(prev => {
            const newSelection = prev.includes(deviceName)
                ? prev.filter(id => id !== deviceName)
                : [...prev, deviceName];

            if (monitors.length > 0) {
                localStorage.setItem(MONITOR_SELECTION_KEY, JSON.stringify({
                    monitorCount: monitors.length,
                    selection: newSelection
                }));
            }

            return newSelection;
        });
    };

    const handleApplyPreset = async (presetId: string) => {
        if (selectedMonitorIds.length === 0) {
            alert('请至少选择一个显示器');
            return;
        }
        try {
            await invoke('apply_filter_preset', {
                presetId,
                monitorIds: selectedMonitorIds
            });
            setActivePresetId(presetId);
            const preset = presets.find(p => p.id === presetId);
            if (preset) {
                setEditingPreset(preset);
            }
        } catch (error) {
            console.error('Failed to apply preset:', error);
            alert('应用失败: ' + error);
        }
    };

    const handleReset = async () => {
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
    };

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
        if (!editingPreset) return;
        if (selectedMonitorIds.length === 0) return;

        const newConfig = { ...editingPreset.config, [key]: value };
        const updatedPreset = { ...editingPreset, config: newConfig };
        setEditingPreset(updatedPreset);

        try {
            await invoke('apply_filter_config', {
                config: newConfig,
                monitorIds: selectedMonitorIds
            });
        } catch (error) {
            console.error('Failed to preview config:', error);
        }
    };

    const handleSavePreset = async () => {
        if (!editingPreset) return;

        try {
            await invoke('update_filter_preset', {
                presetId: editingPreset.id,
                name: editingPreset.name,
                config: editingPreset.config,
                hotkey: editingPreset.hotkey
            });

            await loadPresets();
            alert('保存成功');
        } catch (error) {
            console.error('Failed to save preset:', error);
            alert('保存失败: ' + error);
        }
    };

    const handleCreatePreset = async () => {
        const name = prompt("请输入新预设名称:", "新预设");
        if (!name) return;

        try {
            const config = editingPreset ? editingPreset.config : {
                brightness: 1.0, gamma: 1.0, contrast: 1.0,
                red_scale: 1.0, green_scale: 1.0, blue_scale: 1.0
            };

            await invoke('create_filter_preset', {
                name,
                config,
                hotkey: null
            });

            await loadPresets();
        } catch (error) {
            console.error('Failed to create preset:', error);
            alert('创建失败: ' + error);
        }
    };

    const handleDeletePreset = async (id: string) => {
        if (!confirm("确定要删除此预设吗？")) return;
        try {
            await invoke('delete_filter_preset', { presetId: id });
            await loadPresets();
            if (activePresetId === id) {
                handleReset();
            }
        } catch (error) {
            console.error('Failed to delete preset:', error);
            alert('删除失败: ' + error);
        }
    };

    const handleHotkeyEdit = (presetId: string) => {
        setListeningForHotkey(presetId);
    };

    const updatePresetHotkey = async (presetId: string, hotkey: string | null) => {
        const preset = presets.find(p => p.id === presetId);
        if (!preset) return;

        try {
            await invoke('update_filter_preset', {
                presetId,
                name: preset.name,
                config: preset.config,
                hotkey
            });
            await loadPresets();

            // 刷新快捷键注册，使修改立即生效
            await invoke('refresh_hotkey_registrations');
            console.log('快捷键注册已刷新');
        } catch (error) {
            console.error('Failed to update hotkey:', error);
            alert('更新快捷键失败: ' + error);
        }
    };

    const handlePresetRename = (presetId: string) => {
        const preset = presets.find(p => p.id === presetId);
        if (!preset) return;

        const newName = prompt("请输入新的预设名称:", preset.name);
        if (!newName || newName === preset.name) return;

        updatePresetName(presetId, newName.trim());
    };

    const updatePresetName = async (presetId: string, name: string) => {
        const preset = presets.find(p => p.id === presetId);
        if (!preset) return;

        try {
            await invoke('update_filter_preset', {
                presetId,
                name,
                config: preset.config,
                hotkey: preset.hotkey
            });
            await loadPresets();
        } catch (error) {
            console.error('Failed to rename preset:', error);
            alert('重命名失败: ' + error);
        }
    };

    if (!editingPreset && presets.length > 0) {
        setEditingPreset(presets[0]);
    }

    return (
        <div className="container mx-auto p-6 max-w-6xl h-full flex flex-col">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-3xl font-bold text-gray-800 dark:text-white">屏幕滤镜控制</h1>
                <button
                    onClick={handleReset}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded shadow transition"
                >
                    重置所有滤镜
                </button>
            </div>

            {/* Monitor Selection Checkboxes */}
            {monitors.length > 0 && (
                <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                    <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                        目标显示器
                        {selectedMonitorIds.length === 0 && <span className="text-red-600 ml-2">(⚠️ 未选择 - 滤镜不会生效)</span>}
                        {selectedMonitorIds.length > 0 && <span className="text-blue-600 ml-2">({selectedMonitorIds.length} 个)</span>}
                    </h2>
                    <div className="flex flex-wrap gap-4">
                        {monitors.map(monitor => (
                            <label
                                key={monitor.device_name}
                                className="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-900 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition"
                            >
                                <input
                                    type="checkbox"
                                    checked={selectedMonitorIds.includes(monitor.device_name)}
                                    onChange={() => handleMonitorToggle(monitor.device_name)}
                                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                />
                                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                    {monitor.name}
                                </span>
                            </label>
                        ))}
                    </div>
                </div>
            )}

            <div className="grid grid-cols-12 gap-6 flex-1">
                {/* Sidebar: Preset List */}
                <div className="col-span-4 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col overflow-hidden">
                    <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-900">
                        <h2 className="font-semibold text-gray-700 dark:text-gray-200">预设列表</h2>
                        <button
                            onClick={handleCreatePreset}
                            className="text-sm px-3 py-1 bg-blue-100 text-blue-600 rounded hover:bg-blue-200 transition"
                        >
                            + 新建
                        </button>
                    </div>
                    <div className="flex-1 overflow-y-auto p-2 space-y-2">
                        {presets.map(preset => (
                            <div
                                key={preset.id}
                                onClick={() => {
                                    handleApplyPreset(preset.id);
                                }}
                                className={`p-3 rounded-lg cursor-pointer transition flex justify-between items-center group ${activePresetId === preset.id
                                    ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 border'
                                    : 'hover:bg-gray-50 dark:hover:bg-gray-700 border border-transparent'
                                    }`}
                            >
                                <div>
                                    <div className={`font-medium ${activePresetId === preset.id ? 'text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300'}`}>
                                        {preset.name}
                                    </div>
                                    {listeningForHotkey === preset.id ? (
                                        <div className="text-xs text-blue-500 mt-1 bg-blue-50 dark:bg-blue-900/30 inline-block px-1.5 py-0.5 rounded animate-pulse">
                                            按下快捷键... (ESC取消)
                                        </div>
                                    ) : preset.hotkey ? (
                                        <div
                                            className="text-xs text-gray-400 mt-1 bg-gray-100 dark:bg-gray-800 inline-block px-1.5 py-0.5 rounded cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700"
                                            onClick={(e) => { e.stopPropagation(); handleHotkeyEdit(preset.id); }}
                                            onContextMenu={(e) => {
                                                e.preventDefault();
                                                e.stopPropagation();
                                                updatePresetHotkey(preset.id, null);
                                            }}
                                            title="左键修改 | 右键清除"
                                        >
                                            {preset.hotkey}
                                        </div>
                                    ) : (
                                        <div
                                            className="text-xs text-gray-400 mt-1 bg-gray-100 dark:bg-gray-800 inline-block px-1.5 py-0.5 rounded cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700"
                                            onClick={(e) => { e.stopPropagation(); handleHotkeyEdit(preset.id); }}
                                            title="点击设置快捷键"
                                        >
                                            设置快捷键
                                        </div>
                                    )}
                                </div>

                                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    {!preset.is_default && (
                                        <>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handlePresetRename(preset.id); }}
                                                className="p-1.5 text-blue-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900 rounded"
                                                title="重命名"
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                                                </svg>
                                            </button>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleDeletePreset(preset.id); }}
                                                className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900 rounded"
                                                title="删除"
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                                                </svg>
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Main: Editor */}
                <div className="col-span-8 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 flex flex-col">
                    {editingPreset ? (
                        <>
                            <div className="flex justify-between items-start mb-8">
                                <div>
                                    <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">{editingPreset.name}</h2>
                                    <p className="text-gray-500 text-sm">
                                        {selectedMonitorIds.length === 0
                                            ? "⚠️ 警告: 未选择任何显示器"
                                            : `正在调整: ${selectedMonitorIds.length} 个显示器`
                                        }
                                    </p>
                                </div>
                                <button
                                    onClick={handleSavePreset}
                                    className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow transition font-medium"
                                >
                                    保存修改
                                </button>
                            </div>

                            <div className="space-y-8">
                                {/* Main Controls */}
                                <div className="space-y-6 p-6 bg-gray-50 dark:bg-gray-900 rounded-xl">
                                    <SliderControl
                                        label="亮度 (Brightness)"
                                        value={backendToUI('brightness', editingPreset.config.brightness)}
                                        onChange={(v) => handleSliderChange('brightness', uiToBackend('brightness', v))}
                                        min={-100} max={100} step={1}
                                    />
                                    <SliderControl
                                        label="对比度 (Contrast)"
                                        value={backendToUI('contrast', editingPreset.config.contrast)}
                                        onChange={(v) => handleSliderChange('contrast', uiToBackend('contrast', v))}
                                        min={-50} max={50} step={1}
                                    />
                                    <SliderControl
                                        label="伽马 (Gamma)"
                                        value={editingPreset.config.gamma}
                                        onChange={(v) => handleSliderChange('gamma', v)}
                                        min={0.5} max={3.5} step={0.01}
                                    />
                                </div>

                                {/* Color Channels */}
                                <div className="space-y-6 p-6 bg-gray-50 dark:bg-gray-900 rounded-xl">
                                    <h3 className="font-semibold text-gray-700 dark:text-gray-300 mb-4">色彩通道微调 (0-255)</h3>
                                    <ColorSliderControl
                                        label="红色通道 (Red)"
                                        value={Math.round(editingPreset.config.red_scale * 127.5)}
                                        onChange={(v) => handleSliderChange('red_scale', v / 127.5)}
                                        colorClass="accent-red-500"
                                    />
                                    <ColorSliderControl
                                        label="绿色通道 (Green)"
                                        value={Math.round(editingPreset.config.green_scale * 127.5)}
                                        onChange={(v) => handleSliderChange('green_scale', v / 127.5)}
                                        colorClass="accent-green-500"
                                    />
                                    <ColorSliderControl
                                        label="蓝色通道 (Blue)"
                                        value={Math.round(editingPreset.config.blue_scale * 127.5)}
                                        onChange={(v) => handleSliderChange('blue_scale', v / 127.5)}
                                        colorClass="accent-blue-500"
                                    />
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="flex items-center justify-center h-full text-gray-400">
                            请选择一个预设进行编辑
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function SliderControl({ label, value, onChange, min, max, step, colorClass = "accent-blue-600" }: {
    label: string, value: number, onChange: (v: number) => void, min: number, max: number, step: number, colorClass?: string
}) {
    const decimals = step < 1 ? 2 : 0;
    const [inputValue, setInputValue] = useState(value.toFixed(decimals));

    useEffect(() => {
        setInputValue(value.toFixed(decimals));
    }, [value, decimals]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setInputValue(e.target.value);
    };

    const handleInputBlur = () => {
        const numValue = parseFloat(inputValue);
        if (!isNaN(numValue)) {
            const clampedValue = Math.max(min, Math.min(max, numValue));
            onChange(clampedValue);
            setInputValue(clampedValue.toFixed(decimals));
        } else {
            setInputValue(value.toFixed(2));
        }
    };

    const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleInputBlur();
            e.currentTarget.blur();
        }
    };

    return (
        <div>
            <div className="flex justify-between mb-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>
                <input
                    type="text"
                    value={inputValue}
                    onChange={handleInputChange}
                    onBlur={handleInputBlur}
                    onFocus={(e) => e.target.select()}
                    onKeyDown={handleInputKeyDown}
                    className="text-sm font-mono text-gray-500 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none w-16 text-right"
                />
            </div>
            <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={value}
                onChange={(e) => onChange(parseFloat(e.target.value))}
                className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 ${colorClass}`}
            />
        </div>
    );
}

function ColorSliderControl({ label, value, onChange, colorClass = "accent-blue-600" }: {
    label: string, value: number, onChange: (v: number) => void, colorClass?: string
}) {
    const [inputValue, setInputValue] = useState(Math.round(value).toString());

    useEffect(() => {
        setInputValue(Math.round(value).toString());
    }, [value]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setInputValue(e.target.value);
    };

    const handleInputBlur = () => {
        const numValue = parseInt(inputValue);
        if (!isNaN(numValue)) {
            const clampedValue = Math.max(0, Math.min(255, numValue));
            onChange(clampedValue);
            setInputValue(clampedValue.toString());
        } else {
            setInputValue(Math.round(value).toString());
        }
    };

    const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleInputBlur();
            e.currentTarget.blur();
        }
    };

    return (
        <div>
            <div className="flex justify-between mb-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>
                <input
                    type="text"
                    value={inputValue}
                    onChange={handleInputChange}
                    onBlur={handleInputBlur}
                    onFocus={(e) => e.target.select()}
                    onKeyDown={handleInputKeyDown}
                    className="text-sm font-mono text-gray-500 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none w-8 text-right"
                />
            </div>
            <input
                type="range"
                min={0}
                max={255}
                step={1}
                value={value}
                onChange={(e) => onChange(parseInt(e.target.value))}
                className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 ${colorClass}`}
            />
        </div>
    );
}
