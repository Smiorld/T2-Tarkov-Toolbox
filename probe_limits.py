import ctypes
from ctypes import wintypes
import time
import sys

# Define structures inline to avoid import issues
WORD = wintypes.WORD
class RAMP(ctypes.Structure):
    _fields_ = [("Red", WORD * 256), ("Green", WORD * 256), ("Blue", WORD * 256)]

def probe():
    print("Starting probe...", flush=True)
    
    # Get Monitor
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    
    # Enum Monitors
    monitors = []
    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        class MONITORINFOEX(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD), ("szDevice", wintypes.WCHAR * 32)]
        mi = MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(MONITORINFOEX)
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
            monitors.append(mi.szDevice)
        return True
    
    MonitorEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HANDLE, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), 0)
    
    if not monitors:
        print("No monitors found!", flush=True)
        return

    target = monitors[0]
    print(f"Probing {target}...", flush=True)

    # Probe Brightness
    for b in range(0, 101, 2): # Step 2
        brightness = b / 100.0
        
        # Generate Ramp (Multiplicative Logic)
        ramp = RAMP()
        factor = 1.0 + brightness
        for i in range(256):
            val = (i / 255.0) * factor
            val = min(1.0, max(0.0, val))
            ival = int(val * 65535)
            ramp.Red[i] = ival
            ramp.Green[i] = ival
            ramp.Blue[i] = ival
            
        # Apply
        hdc = gdi32.CreateDCW(target, None, None, None)
        if hdc:
            success = gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
            gdi32.DeleteDC(hdc)
            print(f"Brightness {brightness:.2f} (UI {b}): {'OK' if success else 'FAIL ❌'}", flush=True)
            if not success:
                break
        time.sleep(0.05)
        
    # Reset
    hdc = gdi32.CreateDCW(target, None, None, None)
    ramp = RAMP()
    for i in range(256):
        v = int((i/255.0) * 65535)
        ramp.Red[i] = v
        ramp.Green[i] = v
        ramp.Blue[i] = v
    gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
    gdi32.DeleteDC(hdc)

if __name__ == "__main__":
    probe()
