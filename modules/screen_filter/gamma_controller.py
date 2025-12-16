import ctypes
from ctypes import wintypes
import math
from typing import List, Tuple, Dict
from screeninfo import get_monitors
from modules.screen_filter.models import FilterConfig
from utils.i18n import get_current_language

# Windows API Constants and Types
HDC = wintypes.HANDLE
BOOL = wintypes.BOOL
WORD = wintypes.WORD
DWORD = wintypes.DWORD

class RAMP(ctypes.Structure):
    _fields_ = [
        ("Red", WORD * 256),
        ("Green", WORD * 256),
        ("Blue", WORD * 256),
    ]

# Load GDI32 DLL
gdi32 = ctypes.windll.gdi32
user32 = ctypes.windll.user32

# Define function signatures
gdi32.SetDeviceGammaRamp.argtypes = [HDC, ctypes.POINTER(RAMP)]
gdi32.SetDeviceGammaRamp.restype = BOOL

gdi32.GetDeviceGammaRamp.argtypes = [HDC, ctypes.POINTER(RAMP)]
gdi32.GetDeviceGammaRamp.restype = BOOL

user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = HDC

user32.ReleaseDC.argtypes = [wintypes.HWND, HDC]
user32.ReleaseDC.restype = ctypes.c_int

# Monitor Enumeration Types
class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]

MonitorEnumProc = ctypes.WINFUNCTYPE(BOOL, wintypes.HMONITOR, HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

user32.EnumDisplayMonitors.argtypes = [HDC, ctypes.POINTER(wintypes.RECT), MonitorEnumProc, wintypes.LPARAM]
user32.EnumDisplayMonitors.restype = BOOL

user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEX)]
user32.GetMonitorInfoW.restype = BOOL

gdi32.CreateDCW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
gdi32.CreateDCW.restype = HDC

gdi32.DeleteDC.argtypes = [HDC]
gdi32.DeleteDC.restype = BOOL

class GammaController:
    def __init__(self):
        self.monitors = self._enumerate_monitors()

    def _enumerate_monitors(self) -> List[Dict[str, str]]:
        """Enumerate all monitors with enhanced metadata"""
        monitors = []

        # Get current language setting
        lang = get_current_language()

        # Get screeninfo data for friendly names
        # Use list instead of dict to match by index
        screeninfo_list = []
        try:
            screeninfo_monitors = get_monitors()
            screeninfo_list = list(screeninfo_monitors)
        except Exception as e:
            print(f"[GammaController] Warning: Failed to get screeninfo data: {e}")

        def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            mi = MONITORINFOEX()
            mi.cbSize = ctypes.sizeof(MONITORINFOEX)
            if user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
                device_name = mi.szDevice  # e.g., "\\.\DISPLAY1"

                # Get screeninfo data by matching index
                # Windows enumerates monitors in the same order as screeninfo
                monitor_index = len(monitors)
                screeninfo_data = screeninfo_list[monitor_index] if monitor_index < len(screeninfo_list) else None

                # Generate friendly name based on language
                if screeninfo_data:
                    if screeninfo_data.is_primary:
                        if lang == "zh_CN":
                            friendly_name = f"主显示器 ({screeninfo_data.width}x{screeninfo_data.height})"
                        else:
                            friendly_name = f"Primary Monitor ({screeninfo_data.width}x{screeninfo_data.height})"
                    else:
                        if lang == "zh_CN":
                            friendly_name = f"显示器{monitor_index + 1} ({screeninfo_data.width}x{screeninfo_data.height})"
                        else:
                            friendly_name = f"Monitor {monitor_index + 1} ({screeninfo_data.width}x{screeninfo_data.height})"
                else:
                    # Fallback if screeninfo doesn't have data
                    if lang == "zh_CN":
                        friendly_name = f"显示器 {monitor_index + 1}"
                    else:
                        friendly_name = f"Monitor {monitor_index + 1}"

                monitors.append({
                    "device_name": device_name,
                    "name": friendly_name
                })
            return True

        callback_func = MonitorEnumProc(callback)
        user32.EnumDisplayMonitors(None, None, callback_func, 0)
        return monitors

    def get_monitors(self):
        # Refresh list in case monitors changed
        self.monitors = self._enumerate_monitors()
        return self.monitors

    def apply_config(self, config: FilterConfig, device_names: List[str]):
        ramp = self._generate_ramp(config)
        
        for device_name in device_names:
            # Create DC for the specific monitor
            hdc = gdi32.CreateDCW(device_name, None, None, None)
            if hdc:
                success = gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
                if not success:
                    print(f"Failed to set gamma ramp for {device_name}")
                gdi32.DeleteDC(hdc)
            else:
                print(f"Failed to create DC for {device_name}")

    def _calculate_value(self, value: float, gamma: float, contrast: float, brightness: float) -> int:
        # 1. Contrast
        contrast_factor = 1.0 + contrast
        contrasted = ((value - 0.5) * contrast_factor + 0.5)
        contrasted = max(0.0, min(1.0, contrasted))

        # 2. Gamma
        # Avoid division by zero
        if gamma < 0.01: gamma = 0.01
        gamma_corrected = math.pow(contrasted, 1.0 / gamma)

        # 3. Brightness (Multiplicative)
        # brightness = 0.0 -> factor 1.0
        # brightness = 1.0 -> factor 2.0
        # brightness = -1.0 -> factor 0.0
        brightness_factor = 1.0 + brightness
        brightened = gamma_corrected * brightness_factor
        brightened = max(0.0, min(1.0, brightened))

        return int(brightened * 65535)

    def _generate_ramp(self, config: FilterConfig) -> RAMP:
        ramp = RAMP()
        
        for i in range(256):
            base_val = i / 255.0
            
            # Calculate for each channel
            # Note: channel_scale is applied at the end
            
            # Red
            val_r = self._calculate_value(base_val, config.gamma, config.contrast, config.brightness)
            val_r = int(val_r * config.red_scale)
            ramp.Red[i] = min(65535, max(0, val_r))

            # Green
            val_g = self._calculate_value(base_val, config.gamma, config.contrast, config.brightness)
            val_g = int(val_g * config.green_scale)
            ramp.Green[i] = min(65535, max(0, val_g))

            # Blue
            val_b = self._calculate_value(base_val, config.gamma, config.contrast, config.brightness)
            val_b = int(val_b * config.blue_scale)
            ramp.Blue[i] = min(65535, max(0, val_b))
            
        return ramp

    def reset_monitors(self, device_names: List[str]):
        # Reset to linear ramp
        default_config = FilterConfig() # Default is 0/0/1.0 which is linear
        self.apply_config(default_config, device_names)
