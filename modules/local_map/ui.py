"""
Local Map Module - Main UI

本地地图模块的主界面
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import math
import threading
import time
import keyboard
import json
from typing import Optional, Tuple
from .map_canvas import MapCanvas
from .config_manager import MapConfigManager
from .function_config import FunctionConfigManager
from .screenshot_parser import ScreenshotParser
from .log_parser import LogMonitor, LogParser
from .models import Position3D, MapLayer, CalibrationPoint
from .overlay_window import OverlayMapWindow
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from utils.i18n import t
from utils.hotkey_manager import get_hotkey_manager


class LocalMapUI(ctk.CTkFrame):
    """本地地图模块UI"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.config_manager = MapConfigManager()
        self.current_map_id: Optional[str] = None
        self.current_layer_id: int = 0
        self.calibration_mode: bool = False
        self.tracking_mode: bool = True  # 默认开启位置追踪
        self.deletion_mode: bool = False  # 删除校准点模式
        self.region_marking_mode: bool = False  # 区域标记模式
        self.region_temp_points: list = []  # 临时存储区域标记点
        self.latest_screenshot_pos: Optional[Position3D] = None
        self.latest_layer: str|None = None
        # 截图监控
        self.screenshot_observer: Optional[Observer] = None
        # 日志监控
        self.log_monitor: Optional[LogMonitor] = None

        # 悬浮小地图
        self.overlay_window: Optional[OverlayMapWindow] = None
        self.overlay_visible = False

        # 功能配置管理器
        self.func_config = FunctionConfigManager()

        # 从配置文件加载快捷键和步进值
        self.overlay_hotkey: Optional[str] = self.func_config.config.overlay_hotkey
        self.zoom_in_hotkey: Optional[str] = self.func_config.config.zoom_in_hotkey
        self.zoom_out_hotkey: Optional[str] = self.func_config.config.zoom_out_hotkey
        self.zoom_step: float = self.func_config.config.zoom_step

        # 快捷键设置状态
        self.waiting_for_hotkey = False
        self.waiting_for_zoom_in_hotkey = False
        self.waiting_for_zoom_out_hotkey = False

        # Unified hotkey manager
        self.hotkey_manager = get_hotkey_manager()
        self.running = True

        # 从全局配置读取路径
        from utils.global_config import get_global_config
        self.global_config = get_global_config()

        self.screenshots_path = self.global_config.get_screenshots_path()
        self.logs_path = self.global_config.get_logs_path()

        # 注册配置变更回调
        self.global_config.on_config_change(self._on_config_change)

        self._setup_ui()
        self._load_maps()
        self._migrate_config_if_needed()  # 执行配置迁移（仅首次运行）

        # Register hotkeys with unified manager
        self._register_hotkeys()

        # 启动截图监控 (如果路径已配置)
        if self.screenshots_path:
            self._start_screenshot_monitoring()

        # 启动日志监控 (如果路径已配置)
        if self.logs_path:
            self._start_log_monitoring()

    def _get_default_screenshots_path(self) -> str:
        """获取默认截图路径（使用Windows Shell API）"""
        try:
            import ctypes
            from ctypes import windll, wintypes

            # 使用SHGetKnownFolderPath获取"我的文档"路径
            FOLDERID_Documents = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"

            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", wintypes.BYTE * 8)
                ]

            # 解析GUID
            guid = GUID()
            guid_str = FOLDERID_Documents.strip("{}")
            parts = guid_str.split("-")
            guid.Data1 = int(parts[0], 16)
            guid.Data2 = int(parts[1], 16)
            guid.Data3 = int(parts[2], 16)
            guid.Data4[0] = int(parts[3][:2], 16)
            guid.Data4[1] = int(parts[3][2:], 16)
            for i in range(6):
                guid.Data4[i+2] = int(parts[4][i*2:(i+1)*2], 16)

            path_ptr = ctypes.c_wchar_p()
            windll.shell32.SHGetKnownFolderPath(
                ctypes.byref(guid), 0, None, ctypes.byref(path_ptr)
            )

            documents_path = path_ptr.value
            windll.ole32.CoTaskMemFree(path_ptr)

            return os.path.join(documents_path, "Escape From Tarkov", "Screenshots")
        except:
            # 回退到简单方法
            return os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "Escape From Tarkov",
                "Screenshots"
            )

    def _get_default_logs_path(self) -> str:
        """获取默认日志路径（从注册表读取游戏安装路径）"""
        try:
            import winreg
            # 尝试BSG启动器
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\EscapeFromTarkov"
            )
            install_location = winreg.QueryValueEx(key, "InstallLocation")[0]
            winreg.CloseKey(key)
            return os.path.join(install_location, "Logs")
        except:
            try:
                # 尝试Steam
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
                steam_path = winreg.QueryValueEx(key, "SteamPath")[0]
                winreg.CloseKey(key)
                return os.path.join(
                    steam_path,
                    "steamapps", "common", "Escape from Tarkov", "build", "Logs"
                )
            except:
                return ""

    def _setup_ui(self):
        """设置UI布局 - 左侧配置，右侧上下分割"""
        # === 主网格配置 ===
        # 左侧配置栏（固定宽度），右侧内容区（自适应）
        self.grid_columnconfigure(0, weight=0)  # 左侧
        self.grid_columnconfigure(1, weight=1)  # 右侧
        self.grid_rowconfigure(0, weight=1)

        # ==================== 左侧：配置栏 ====================
        self.left_panel_container = ctk.CTkFrame(self, width=280)
        self.left_panel_container.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.left_panel_container.grid_propagate(False)

        # 左侧可滚动内容
        self.left_panel = ctk.CTkScrollableFrame(
            self.left_panel_container,
            width=260,
            fg_color="transparent"
        )
        self.left_panel.pack(fill="both", expand=True, padx=5, pady=5)

        # --- 标题 ---
        ctk.CTkLabel(
            self.left_panel,
            text=t("local_map.title"),
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(5, 10))

        # --- 地图选择 ---
        ctk.CTkLabel(
            self.left_panel,
            text=t("local_map.map_selection.select_map"),
            font=ctk.CTkFont(size=11)
        ).pack(pady=(5, 2), anchor="w", padx=10)

        self.map_selector = ctk.CTkComboBox(
            self.left_panel,
            values=[],
            command=self._on_map_selected,
            width=240,
            height=28
        )
        self.map_selector.pack(pady=(0, 8))

        # --- 层级选择 ---
        ctk.CTkLabel(
            self.left_panel,
            text=t("local_map.map_selection.select_layer"),
            font=ctk.CTkFont(size=11)
        ).pack(pady=(2, 2), anchor="w", padx=10)

        self.layer_selector = ctk.CTkComboBox(
            self.left_panel,
            values=[t("local_map.status.unconfigured")],
            command=self._on_layer_selected,
            width=240,
            height=28
        )
        self.layer_selector.pack(pady=(0, 8))

        # --- 分隔线 ---
        ctk.CTkFrame(
            self.left_panel,
            height=1,
            fg_color="gray40"
        ).pack(fill="x", padx=15, pady=8)

        # --- 地图管理 ---
        ctk.CTkLabel(
            self.left_panel,
            text=t("local_map.sections.map_management"),
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(5, 5))

        self.import_map_btn = ctk.CTkButton(
            self.left_panel,
            text=t("local_map.map_management.new_layer"),
            command=self._import_map_image,
            width=240,
            height=28
        )
        self.import_map_btn.pack(pady=3)

        # 配置层级高度 和 删除层级 按钮（横向并排）
        config_delete_frame = ctk.CTkFrame(
            self.left_panel,
            fg_color="transparent"
        )
        config_delete_frame.pack(pady=3, fill="x", padx=10)

        self.layer_config_btn = ctk.CTkButton(
            config_delete_frame,
            text=t("local_map.map_management.config_layer_height"),
            command=self._config_layer_height,
            width=110,  # 约45%宽度
            height=28
        )
        self.layer_config_btn.pack(side="left", padx=(0, 5), expand=True)

        self.delete_layer_btn = ctk.CTkButton(
            config_delete_frame,
            text=t("local_map.map_management.delete_layer"),
            command=self._delete_layer,
            width=110,  # 约45%宽度
            height=28,
            fg_color="#8B0000",  # 深红色
            hover_color="#DC143C"  # 猩红色
        )
        self.delete_layer_btn.pack(side="left", expand=True)

        # 导出/导入地图配置
        map_io_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        map_io_frame.pack(pady=3, fill="x", padx=10)

        self.export_map_btn = ctk.CTkButton(
            map_io_frame,
            text=t("local_map.map_management.export_map"),
            command=self._export_map_config,
            width=110,
            height=28,
            fg_color="transparent",
            border_width=1
        )
        self.export_map_btn.pack(side="left", padx=(0, 5), expand=True)

        self.import_map_config_btn = ctk.CTkButton(
            map_io_frame,
            text=t("local_map.map_management.import_map_config"),
            command=self._import_map_config,
            width=110,
            height=28,
            fg_color="transparent",
            border_width=1
        )
        self.import_map_config_btn.pack(side="left", padx=(5, 0), expand=True)

        # --- 分隔线 ---
        ctk.CTkFrame(
            self.left_panel,
            height=1,
            fg_color="gray40"
        ).pack(fill="x", padx=15, pady=8)

        # --- 校准系统 ---
        ctk.CTkLabel(
            self.left_panel,
            text=t("local_map.sections.calibration_system"),
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(5, 5))

        self.calibration_mode_switch = ctk.CTkSwitch(
            self.left_panel,
            text=t("local_map.calibration.calibration_mode"),
            command=self._toggle_calibration_mode
        )
        self.calibration_mode_switch.pack(pady=3)

        self.calibration_info = ctk.CTkLabel(
            self.left_panel,
            text=t("local_map.calibration.calibration_info", count=0),
            font=ctk.CTkFont(size=10),
            text_color="gray60"
        )
        self.calibration_info.pack(pady=3)

        self.clear_calibration_btn = ctk.CTkButton(
            self.left_panel,
            text=t("local_map.calibration.delete_points"),
            command=self._toggle_deletion_mode,
            width=240,
            height=28,
            fg_color="darkred",
            hover_color="#8B0000"
        )
        self.clear_calibration_btn.pack(pady=3)

        # --- 分隔线 ---
        ctk.CTkFrame(
            self.left_panel,
            height=1,
            fg_color="gray40"
        ).pack(fill="x", padx=15, pady=8)

        # --- 区域标记系统 ---
        ctk.CTkLabel(
            self.left_panel,
            text=t("local_map.sections.floor_regions"),
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(5, 5))

        region_hint = ctk.CTkLabel(
            self.left_panel,
            text=t("local_map.floor_regions.hint"),
            font=ctk.CTkFont(size=10),
            text_color="gray60"
        )
        region_hint.pack(pady=(0, 5))

        self.mark_region_btn = ctk.CTkButton(
            self.left_panel,
            text=t("local_map.floor_regions.mark_region"),
            command=self._toggle_region_marking_mode,
            width=240,
            height=28,
            fg_color="#2d5a2d",
            hover_color="#4a9d4a"
        )
        self.mark_region_btn.pack(pady=3)

        # 新增：重置区域标记按钮
        self.reset_region_btn = ctk.CTkButton(
            self.left_panel,
            text=t("local_map.floor_regions.reset_region"),
            command=self._reset_region_binding,
            width=240,
            height=28,
            fg_color="#8B4513",
            hover_color="#A0522D"
        )
        self.reset_region_btn.pack(pady=3)

        self.region_info = ctk.CTkLabel(
            self.left_panel,
            text=t("local_map.floor_regions.region_info", count=0),
            font=ctk.CTkFont(size=10),
            text_color="gray60"
        )
        self.region_info.pack(pady=3)

        # --- 分隔线 ---
        ctk.CTkFrame(
            self.left_panel,
            height=1,
            fg_color="gray40"
        ).pack(fill="x", padx=15, pady=8)

        # --- 视图控制 ---
        ctk.CTkLabel(
            self.left_panel,
            text=t("local_map.sections.view_control"),
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(5, 5))

        zoom_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        zoom_frame.pack(pady=3)

        ctk.CTkLabel(
            zoom_frame,
            text=t("local_map.view_control.zoom"),
            font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=5)

        self.zoom_slider = ctk.CTkSlider(
            zoom_frame,
            from_=0.1,
            to=3.0,
            command=self._on_zoom_changed,
            width=150
        )
        self.zoom_slider.set(1.0)
        self.zoom_slider.pack(side="left", padx=5)

        self.reset_view_btn = ctk.CTkButton(
            self.left_panel,
            text=t("local_map.view_control.reset_view"),
            command=self._reset_view,
            width=240,
            height=28
        )
        self.reset_view_btn.pack(pady=3)

        # ==================== 右侧：内容区（上下分割） ====================
        self.right_container = ctk.CTkFrame(self)
        self.right_container.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        # 右侧网格配置：上面固定高度，下面自适应
        self.right_container.grid_rowconfigure(0, weight=0)  # 上：核心功能（固定高度）
        self.right_container.grid_rowconfigure(1, weight=1)  # 下：地图Canvas（自适应）
        self.right_container.grid_columnconfigure(0, weight=1)

        # --- 右上：核心功能区 ---
        self.core_control_panel = ctk.CTkFrame(
            self.right_container,
            fg_color="#1a3a1a",
            height=135  # 从150压缩到135
        )
        self.core_control_panel.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.core_control_panel.grid_propagate(False)

        # === 第一行：标题 + 开关们 ===
        row1 = ctk.CTkFrame(self.core_control_panel, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(5, 3))

        ctk.CTkLabel(
            row1,
            text=t("local_map.sections.core_functions"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#90EE90"
        ).pack(side="left", padx=(0, 10))

        self.tracking_mode_switch = ctk.CTkSwitch(
            row1,
            text=t("local_map.core_functions.enable_tracking"),
            command=self._toggle_tracking_mode,
            fg_color="#2d5a2d",
            progress_color="#4a9d4a",
            font=ctk.CTkFont(size=11)
        )
        self.tracking_mode_switch.pack(side="left", padx=5)
        self.tracking_mode_switch.select()

        self.player_centered_switch = ctk.CTkSwitch(
            row1,
            text=t("local_map.core_functions.player_centered"),
            command=self._toggle_player_centered,
            fg_color="#2d5a2d",
            progress_color="#4a9d4a",
            font=ctk.CTkFont(size=11)
        )
        self.player_centered_switch.pack(side="left", padx=5)
        self.player_centered_switch.select()

        self.log_status_label = ctk.CTkLabel(
            row1,
            text=t("local_map.core_functions.log_monitor_status_off"),
            text_color="gray",
            font=("", 10)
        )
        self.log_status_label.pack(side="right", padx=5)

        # === 第二行：按钮们 ===
        row2 = ctk.CTkFrame(self.core_control_panel, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=3)

        self.overlay_toggle_btn = ctk.CTkButton(
            row2,
            text=t("local_map.core_functions.show_overlay"),
            command=self._toggle_overlay,
            width=90,
            height=28,
            fg_color="#2d5a2d",
            hover_color="#4a9d4a",
            font=ctk.CTkFont(size=11)
        )
        self.overlay_toggle_btn.pack(side="left", padx=2)

        self.overlay_lock_btn = ctk.CTkButton(
            row2,
            text=t("local_map.core_functions.lock_overlay"),
            command=self._toggle_overlay_lock,
            width=90,
            height=28,
            state="disabled",
            fg_color="#2d5a2d",
            hover_color="#4a9d4a",
            font=ctk.CTkFont(size=11)
        )
        self.overlay_lock_btn.pack(side="left", padx=2)

        self.hotkey_btn = ctk.CTkButton(
            row2,
            text=t("local_map.core_functions.overlay_hotkey", overlay_hotkey=self.overlay_hotkey) if self.overlay_hotkey else t("local_map.core_functions.overlay_hotkey_not_set"),
            command=self._set_overlay_hotkey,
            width=85,
            height=28,
            fg_color="#2d5a2d",
            hover_color="#4a9d4a",
            font=ctk.CTkFont(size=10)
        )
        self.hotkey_btn.pack(side="left", padx=2)

        self.zoom_in_hotkey_btn = ctk.CTkButton(
            row2,
            text=t("local_map.core_functions.zoom_in_hotkey", zoom_in_hotkey=self.zoom_in_hotkey) if self.zoom_in_hotkey else t("local_map.core_functions.zoom_in_hotkey_not_set"),
            command=self._set_zoom_in_hotkey,
            width=70,
            height=28,
            fg_color="#2d5a2d",
            hover_color="#4a9d4a",
            font=ctk.CTkFont(size=10)
        )
        self.zoom_in_hotkey_btn.pack(side="left", padx=2)

        self.zoom_out_hotkey_btn = ctk.CTkButton(
            row2,
            text=t("local_map.core_functions.zoom_out_hotkey", zoom_out_hotkey=self.zoom_out_hotkey) if self.zoom_out_hotkey else t("local_map.core_functions.zoom_out_hotkey_not_set"),
            command=self._set_zoom_out_hotkey,
            width=70,
            height=28,
            fg_color="#2d5a2d",
            hover_color="#4a9d4a",
            font=ctk.CTkFont(size=10)
        )
        self.zoom_out_hotkey_btn.pack(side="left", padx=2)

        # === 第三行：尺寸配置 + 步进 + 透明度 ===
        row3 = ctk.CTkFrame(self.core_control_panel, fg_color="transparent")
        row3.pack(fill="x", padx=8, pady=(3, 5))

        ctk.CTkLabel(
            row3,
            text=t("local_map.core_functions.window_size"),
            font=ctk.CTkFont(size=10)
        ).pack(side="left", padx=(0, 2))

        self.overlay_width_entry = ctk.CTkEntry(
            row3,
            width=50,
            height=24,
            font=ctk.CTkFont(size=10),
            placeholder_text=t("local_map.core_functions.width_placeholder")
        )
        self.overlay_width_entry.insert(0, "400")
        self.overlay_width_entry.pack(side="left", padx=1)
        self.overlay_width_entry.bind("<FocusOut>", lambda e: self.focus_set())

        ctk.CTkLabel(row3, text="×", font=ctk.CTkFont(size=10)).pack(side="left", padx=1)

        self.overlay_height_entry = ctk.CTkEntry(
            row3,
            width=50,
            height=24,
            font=ctk.CTkFont(size=10),
            placeholder_text=t("local_map.core_functions.height_placeholder")
        )
        self.overlay_height_entry.insert(0, "400")
        self.overlay_height_entry.pack(side="left", padx=1)
        self.overlay_height_entry.bind("<FocusOut>", lambda e: self.focus_set())

        ctk.CTkLabel(
            row3,
            text=t("local_map.core_functions.zoom_step"),
            font=ctk.CTkFont(size=10)
        ).pack(side="left", padx=(8, 2))

        self.zoom_step_entry = ctk.CTkEntry(
            row3,
            width=45,
            height=24,
            font=ctk.CTkFont(size=10),
            placeholder_text="0.2"
        )
        self.zoom_step_entry.insert(0, str(self.zoom_step))
        self.zoom_step_entry.pack(side="left", padx=1)
        self.zoom_step_entry.bind("<FocusOut>", lambda e: self.focus_set())

        self.apply_size_btn = ctk.CTkButton(
            row3,
            text=t("local_map.core_functions.apply"),
            command=self._apply_settings,
            width=50,
            height=24,
            fg_color="#2d5a2d",
            hover_color="#4a9d4a",
            font=ctk.CTkFont(size=10)
        )
        self.apply_size_btn.pack(side="left", padx=3)

        ctk.CTkLabel(
            row3,
            text=t("local_map.core_functions.opacity"),
            font=ctk.CTkFont(size=10)
        ).pack(side="left", padx=(5, 2))

        self.opacity_slider = ctk.CTkSlider(
            row3,
            from_=0.1,
            to=1.0,
            command=self._on_opacity_changed,
            width=100
        )
        self.opacity_slider.set(0.85)
        self.opacity_slider.pack(side="left", fill="x", expand=True, padx=(0, 2))

        # --- 右下：地图预览Canvas ---
        self.map_panel = ctk.CTkFrame(self.right_container)
        self.map_panel.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.map_panel.grid_rowconfigure(0, weight=1)
        self.map_panel.grid_columnconfigure(0, weight=1)

        # 地图Canvas
        self.map_canvas = MapCanvas(self.map_panel, width=800, height=600)
        self.map_canvas.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.map_canvas.set_click_callback(self._on_canvas_click)

        # 状态栏
        self.status_label = ctk.CTkLabel(
            self.map_panel,
            text=t("local_map.status.please_select_import"),
            font=ctk.CTkFont(size=11)
        )
        self.status_label.grid(row=1, column=0, pady=(0, 5))

    def _load_maps(self):
        """加载地图列表"""
        maps = self.config_manager.get_all_maps()
        map_names = [f"{m.display_name} ({m.map_id})" for m in maps]
        self.map_selector.configure(values=map_names)
        if map_names:
            self.map_selector.set(map_names[0])
            self._on_map_selected(map_names[0])

    def _on_map_selected(self, selection: str):
        """地图选择事件"""
        # 解析选择的地图ID
        if "(" in selection and ")" in selection:
            map_id = selection.split("(")[1].split(")")[0]
            self.current_map_id = map_id

            map_config = self.config_manager.get_map_config(map_id)
            if map_config and map_config.layers:
                # 更新层级列表
                layer_names = [f"Layer {l.layer_id}: {l.name}" for l in map_config.layers]
                self.layer_selector.configure(values=layer_names)
                self.layer_selector.set(layer_names[0])
                self._on_layer_selected(layer_names[0])
            else:
                self.layer_selector.configure(values=["None"])
                self.layer_selector.set("None")
                self.status_label.configure(text=t("local_map.status.no_layer_configured"))

    def _on_layer_selected(self, selection: str):
        """层级选择事件"""
        print(f"on_layer_selected:{selection}")
        if not self.current_map_id or selection == "None":
            return

        # 解析层级ID
        try:
            layer_id = int(selection.split(":")[0].split(" ")[1])
            self.current_layer_id = layer_id

            map_config = self.config_manager.get_map_config(self.current_map_id)
            if map_config:
                layer = map_config.get_layer_by_id(layer_id)
                if layer:
                    # 将相对路径转换为绝对路径
                    from utils import path_manager
                    absolute_path = path_manager.get_absolute_path(layer.image_path)

                    if os.path.exists(absolute_path):
                        # 加载地图图片（只加载一次，悬浮窗共享资源）
                        success = self.map_canvas.load_map(absolute_path)
                        if success:
                            # 显示校准点
                            self._display_calibration_points(layer)

                            # === 改：悬浮窗共享资源，不重复加载 ===
                            if self.overlay_window and self.overlay_visible:
                                # 不重复加载，只同步路径和重绘
                                self.overlay_window.map_canvas._current_image_path = absolute_path
                                self.overlay_window.map_canvas.map_image = self.map_canvas.map_image
                                self.overlay_window.map_canvas._render()
                                # 如果有玩家位置，更新显示
                                if self.latest_screenshot_pos:
                                    self._update_overlay_position()
                            # === 改动结束 ===

                            # 如果已校准，提示可以启用位置追踪
                            if layer.is_calibrated():
                                self.status_label.configure(
                                    text=t("local_map.status.loaded_calibrated", map_name=map_config.display_name, layer_name=layer.name)
                                )
                            else:
                                self.status_label.configure(
                                    text=t("local_map.status.loaded", map_name=map_config.display_name, layer_name=layer.name)
                                )
                        else:
                            self.status_label.configure(text=t("local_map.status.map_load_failed"))
                    else:
                        self.status_label.configure(text=t("local_map.status.map_file_not_exist", path=absolute_path))
        except Exception as e:
            print(f"层级选择错误: {e}")

    def _import_map_image(self):
        """导入地图图片"""
        if not self.current_map_id:
            messagebox.showwarning(t("common.warning"), t("local_map.messages.no_map_selected"))
            return

        # 选择图片文件
        file_path = filedialog.askopenfilename(
            title=t("local_map.messages.select_map_image"),
            filetypes=[(t("common.image_file"), "*.png *.jpg *.jpeg *.bmp")]
        )

        if not file_path:
            return

        # 询问层级信息（包括导入类型）
        dialog = LayerConfigDialog(self, t("local_map.messages.new_layer"))
        if dialog.result:
            layer_id, layer_name, height_min, height_max, rotation_offset, is_base_map = dialog.result

            try:
                # 使用路径管理器规范化图片路径（复制到正确位置并转换为相对路径）
                from utils import path_manager
                relative_path = path_manager.normalize_image_path(file_path, self.current_map_id)

                # 保存配置（使用相对路径）
                self.config_manager.set_map_image(
                    self.current_map_id,
                    layer_id,
                    relative_path,
                    layer_name,
                    height_min,
                    height_max,
                    rotation_offset
                )

                # 设置是否为大地图
                map_config = self.config_manager.get_map_config(self.current_map_id)
                if map_config:
                    layer = map_config.get_layer_by_id(layer_id)
                    if layer:
                        layer.is_base_map = is_base_map
                        self.config_manager.save_config()

                # 重新加载地图列表
                self._on_map_selected(self.map_selector.get())

                layer_type = t("local_map.base_map") if is_base_map else t("local_map.floor_map")
                messagebox.showinfo(t("common.success"), t("local_map.messages.import_map_success", layer_type=layer_type, layer_name=layer_name))
            except Exception as e:
                messagebox.showerror(t("common.error"), t("local_map.messages.import_map_failed", error=str(e)))

    def _config_layer_height(self):
        """配置层级高度"""
        if not self.current_map_id:
            messagebox.showwarning(t("common.warning"), t("local_map.messages.no_map_selected"))
            return

        map_config = self.config_manager.get_map_config(self.current_map_id)
        if not map_config or not map_config.layers:
            messagebox.showwarning(t("common.warning"), t("local_map.status.no_layer_configured"))
            return

        layer = map_config.get_layer_by_id(self.current_layer_id)
        if not layer:
            return

        dialog = LayerConfigDialog(
            self,
            t("local_map.map_management.config_layer_height"),
            layer.layer_id,
            layer.name,
            layer.height_min,
            layer.height_max,
            layer.rotation_offset,
            layer.is_base_map
        )

        if dialog.result:
            layer_id, layer_name, height_min, height_max, rotation_offset, is_base_map = dialog.result
            layer.name = layer_name
            layer.height_min = height_min
            layer.height_max = height_max
            layer.rotation_offset = rotation_offset
            layer.is_base_map = is_base_map
            self.config_manager.save_config()
            messagebox.showinfo(t("common.success"), t("local_map.messages.layer_config_updated"))

    def _toggle_calibration_mode(self):
        """切换校准模式"""
        self.calibration_mode = self.calibration_mode_switch.get()

        if self.calibration_mode:
            self.status_label.configure(
                text=t("local_map.calibration.mode_active")
            )
            # 确保监控已开启
            if not self.screenshot_observer:
                self._start_screenshot_monitoring()
        else:
            self.status_label.configure(text=t("local_map.calibration.mode_exited"))
            # 如果位置追踪也没开启，停止监控
            if not self.tracking_mode:
                self._stop_screenshot_monitoring()

    def _toggle_tracking_mode(self):
        """切换位置追踪模式"""
        self.tracking_mode = self.tracking_mode_switch.get()

        if self.tracking_mode:
            # 检查当前地图是否已校准
            if self.current_map_id:
                map_config = self.config_manager.get_map_config(self.current_map_id)
                if map_config:
                    layer = map_config.get_layer_by_id(self.current_layer_id)
                    if layer and layer.is_calibrated():
                        self.status_label.configure(text=t("local_map.status.tracking_enabled_status"))
                        # 启动监控
                        if not self.screenshot_observer:
                            self._start_screenshot_monitoring()
                    else:
                        messagebox.showwarning(t("common.warning"), t("local_map.messages.layer_not_calibrated"))
                        self.tracking_mode_switch.deselect()
                        self.tracking_mode = False
                else:
                    messagebox.showwarning(t("common.warning"), t("local_map.messages.select_configure_map"))
                    self.tracking_mode_switch.deselect()
                    self.tracking_mode = False
            else:
                messagebox.showwarning(t("common.warning"), t("local_map.messages.no_map_selected"))
                self.tracking_mode_switch.deselect()
                self.tracking_mode = False
        else:
            self.status_label.configure(text=t("local_map.status.tracking_disabled_status"))
            # 清除玩家标记
            self.map_canvas.clear_player_marker()
            # 如果校准模式也没开启，停止监控
            if not self.calibration_mode:
                self._stop_screenshot_monitoring()

    def _start_screenshot_monitoring(self):
        """开始监控截图文件夹"""
        if not os.path.exists(self.screenshots_path):
            messagebox.showwarning(
                t("common.warning"),
                t("local_map.messages.screenshot_folder_not_exist", path=self.screenshots_path)
            )
            return

        class ScreenshotHandler(FileSystemEventHandler):
            def __init__(self, callback):
                self.callback = callback

            def on_created(self, event):
                if event.src_path.endswith('.png'):
                    self.callback(event.src_path)

        self.screenshot_observer = Observer()
        handler = ScreenshotHandler(self._on_new_screenshot)
        self.screenshot_observer.schedule(handler, self.screenshots_path, recursive=False)
        self.screenshot_observer.start()

        print(f"开始监控截图文件夹: {self.screenshots_path}")

    def _stop_screenshot_monitoring(self):
        """停止监控截图文件夹"""
        if self.screenshot_observer:
            self.screenshot_observer.stop()
            self.screenshot_observer.join()
            self.screenshot_observer = None

    def _start_log_monitoring(self):
        """开始监控塔科夫日志文件"""
        if not self.logs_path:
            print("[本地地图] 日志路径未配置，跳过日志监控")
            return

        from pathlib import Path

        logs_base = Path(self.logs_path)

        # Tarkov logs are in timestamped subdirectories: Logs/log_YYYY.MM.DD_H-mm-ss/
        log_dirs = list(logs_base.glob("log_*"))
        if not log_dirs:
            print(f"[本地地图] 未找到日志目录: {self.logs_path}/log_*")
            return

        # Get the most recent log directory by modification time
        latest_log_dir = max(log_dirs, key=lambda p: p.stat().st_mtime)

        # Look for application.log (main game events log)
        # Tarkov log files may have format: "YYYY.MM.DD_H-mm-ss_version application_000.log"
        log_files = list(latest_log_dir.glob("*application*.log"))
        if not log_files:
            print(f"[本地地图] 未找到application.log: {latest_log_dir}")
            return

        # Use the first application log
        log_file_path = str(log_files[0])
        print(f"[本地地图] 检测到日志文件: {log_files[0].name}")

        print(f"[本地地图] 开始监控日志文件: {log_file_path}")

        try:
            self.log_monitor = LogMonitor(
                log_file_path=log_file_path,
                on_raid_start=self._on_raid_start_detected,
                on_raid_end=None,
                start_from_end=True  # 启动时跳过现有内容，只监控新增内容
            )
            self.log_monitor.start()
            print("[本地地图] 日志监控已启动")
            if hasattr(self, 'log_status_label'):
                self.log_status_label.configure(text=t("local_map.core_functions.log_monitor_status_on"), text_color="green")
        except Exception as e:
            print(f"[本地地图] 启动日志监控失败: {e}")
            self.log_monitor = None

    def _stop_log_monitoring(self):
        """停止监控日志文件"""
        if self.log_monitor:
            self.log_monitor.stop()
            self.log_monitor = None
            print("[本地地图] 日志监控已停止")
            if hasattr(self, 'log_status_label'):
                self.log_status_label.configure(text=t("local_map.core_functions.log_monitor_stopped"), text_color="gray")

    def _on_config_change(self, key: str, value: str):
        """
        全局配置变更回调

        当用户在"全局设置"修改路径时,此方法会被调用
        """
        if key == 'screenshots_path':
            old_path = self.screenshots_path
            self.screenshots_path = value

            print(f"[本地地图] 截图路径已更新: {old_path} -> {value}")

            # 重启截图监控
            self._stop_screenshot_monitoring()
            if value:  # 路径非空才启动
                self._start_screenshot_monitoring()

        elif key == 'logs_path':
            old_path = self.logs_path
            self.logs_path = value
            print(f"[本地地图] 日志路径已更新: {old_path} -> {value}")

            # 重启日志监控
            self._stop_log_monitoring()
            if value:  # 路径非空才启动
                self._start_log_monitoring()

    def _on_new_screenshot(self, file_path: str):
        """检测到新截图"""
        # 如果两个模式都没开启，直接返回
        if not self.calibration_mode and not self.tracking_mode:
            return

        if not self.current_map_id:
            return

        # 解析截图
        player_pos = ScreenshotParser.parse(file_path, self.current_map_id)
        if not player_pos:
            return

        # 保存完整的玩家位置（包括旋转）
        self.latest_screenshot_pos = player_pos

        # 获取地图配置
        map_config = self.config_manager.get_map_config(self.current_map_id)
        if not map_config:
            return

        # === 新的智能层级选择逻辑 ===
        # 1. 获取大地图
        base_map = map_config.get_base_map()
        if not base_map:
            # 没有大地图，回退到旧逻辑（向后兼容）
            layer = map_config.get_layer_by_height(player_pos.position.y)
            if not layer:
                layer = map_config.get_layer_by_id(self.current_layer_id)
            if not layer:
                return
        else:
            # 有大地图，使用新的智能选择
            # 2. 计算玩家在大地图上的坐标（如果大地图已校准）
            base_map_transform = None
            if base_map.is_calibrated():
                try:
                    # === 改：使用全局缓存 ===
                    from modules.local_map.map_resource_cache import get_resource_cache
                    resource_cache = get_resource_cache()

                    base_map_transform = resource_cache.get_transform(
                        self.config_manager,
                        self.current_map_id,
                        base_map.layer_id,
                        player_pos=player_pos.position
                    )
                    # === 改动结束 ===
                except Exception as e:
                    print(f"计算大地图坐标变换失败: {e}")

            # 3. 智能选择激活的层级（区域+高度）
            layer = map_config.get_active_layer(
                player_pos.position,
                base_map_transform
            )
            if not layer:
                return
        # 如果是校准模式，只显示坐标信息
        if self.calibration_mode:
            layer_type = t("local_map.base_map") if layer.is_base_map else t("local_map.floor_map")
            self.status_label.configure(
                text=t("local_map.status.screenshot_detected",
                       position=player_pos.position,
                       height=f"{player_pos.position.y:.2f}",
                       layer_name=layer.name,
                       layer_type=layer_type
                       )
            )
            print(f"新截图: {player_pos.position}, 自动层级: {layer.name}")
            return

        # 位置追踪模式：如果已完成校准，自动显示玩家位置
        if self.tracking_mode and layer.is_calibrated():
            try:
                # T2手动修复层级自动跳转逻辑。
                layer_str = f"Layer {layer.layer_id}: {layer.name}"
                if layer_str != self.latest_layer:
                    self.layer_selector.set(layer_str)
                    self._on_layer_selected(layer_str)
                    self.latest_layer = layer_str
                    
                # === 改：使用全局缓存的Transform ===
                from modules.local_map.map_resource_cache import get_resource_cache
                resource_cache = get_resource_cache()

                transform = resource_cache.get_transform(
                    self.config_manager,
                    self.current_map_id,
                    layer.layer_id,
                    player_pos=player_pos.position  # 启用局部插值
                )
                # === 改动结束 ===

                # 转换游戏坐标到地图坐标
                map_x, map_y = transform.transform(player_pos.position)

                # 计算朝向角度
                yaw = player_pos.rotation.to_yaw()

                # 应用地图旋转偏移（修正地图方向）
                # 如果地图旋转了（如180°），需要补偿这个旋转
                corrected_yaw = yaw + layer.rotation_offset

                
                # 在地图上显示玩家位置
                self.map_canvas.show_player_position(map_x, map_y, corrected_yaw)
                
                # 更新状态栏（显示当前层级信息）
                layer_info = f"[{layer.name}]" if not layer.is_base_map else f"[{t('local_map.base_map')}]"
                self.status_label.configure(
                    text=t("local_map.status.coord_transformed", layer_info=layer_info, game_x=f"{player_pos.position.x:.1f}", game_z=f"{player_pos.position.z:.1f}", map_x=f"{map_x:.1f}", map_y=f"{map_y:.1f}", yaw=yaw)
                )

                # 同时更新悬浮小地图
                self._update_overlay_position()
                
            except Exception as e:
                print(f"转换坐标失败: {e}")
                self.status_label.configure(
                    text=t("local_map.status.transform_failed", error=str(e))
                )

    def _on_raid_start_detected(self, raid_info):
        """
        日志监控检测到战局开始，自动切换地图

        Args:
            raid_info: RaidInfo 对象，包含 map_id, raid_id 等信息
        """
        detected_map_id = raid_info.map_id

        print(f"[本地地图] 检测到战局开始: {detected_map_id} (RaidID: {raid_info.raid_id})")

        # 验证地图 ID 是否有效
        map_config = self.config_manager.get_map_config(detected_map_id)
        if not map_config:
            print(f"[本地地图] 地图 '{detected_map_id}' 不在配置中，跳过自动切换")
            return

        # 转换为 UI 选择格式: "DisplayName (map_id)"
        selection_text = f"{map_config.display_name} ({detected_map_id})"

        print(f"[本地地图] 自动切换到地图: {selection_text}")

        # 在主线程中更新 UI (回调在后台线程)
        def update_ui():
            self.map_selector.set(selection_text)
            self._on_map_selected(selection_text)

            # Update status bar with notification
            if hasattr(self, 'status_label'):
                self.status_label.configure(
                    text=t("local_map.status.auto_switched_map", map_name=map_config.display_name),
                    text_color="green"
                )

        self.after(0, update_ui)

    def _on_canvas_click(self, map_x: float, map_y: float):
        """Canvas点击事件"""
        # 区域标记模式优先级最高
        if self.region_marking_mode:
            self._handle_region_marking_click(map_x, map_y)
            return

        # 删除模式次优先
        if self.deletion_mode:
            self._handle_deletion_click(map_x, map_y)
            return

        # 原有的校准模式
        if not self.calibration_mode:
            return

        if not self.latest_screenshot_pos:
            messagebox.showinfo(t("common.info"), t("local_map.messages.no_screenshot"))
            return

        # 添加校准点
        if self.current_map_id:
            self.config_manager.add_calibration_point(
                self.current_map_id,
                self.current_layer_id,
                self.latest_screenshot_pos.position,
                map_x,
                map_y
            )

            # 在Canvas上显示标记
            map_config = self.config_manager.get_map_config(self.current_map_id)
            if map_config:
                layer = map_config.get_layer_by_id(self.current_layer_id)
                if layer:
                    count = len(layer.calibration_points)
                    self.map_canvas.add_calibration_marker(
                        map_x, map_y,
                        f"P{count}"
                    )
                    self._update_calibration_info(layer)

                    if count >= 3:
                        messagebox.showinfo(
                            t("common.success"),
                            t("local_map.messages.calibration_point_enough", count=count)
                        )

        # 清除最新截图状态
        self.latest_screenshot_pos = None

    def _display_calibration_points(self, layer: MapLayer):
        """显示校准点"""
        self.map_canvas.clear_calibration_markers()
        for i, point in enumerate(layer.calibration_points, 1):
            self.map_canvas.add_calibration_marker(
                point.map_x,
                point.map_y,
                f"P{i}"
            )
        self._update_calibration_info(layer)

    def _update_calibration_info(self, layer: MapLayer):
        """更新校准信息显示"""
        count = len(layer.calibration_points)
        status = t("local_map.calibration.calibration_ready") if count >= 3 else t("local_map.calibration.calibration_not_ready")
        self.calibration_info.configure(
            text=t("local_map.calibration.calibration_info_with_status", count=count, status=status)
        )

    def _clear_calibration(self):
        """清除校准点"""
        if not self.current_map_id:
            return

        if messagebox.askyesno(t("common.confirm"), t("local_map.messages.clear_calibration_confirm")):
            self.config_manager.clear_calibration_points(
                self.current_map_id,
                self.current_layer_id
            )
            self.map_canvas.clear_calibration_markers()
            self.calibration_info.configure(text=t("local_map.calibration.calibration_info", count=0))
            messagebox.showinfo(t("common.success"), t("local_map.messages.calibration_cleared"))

    def _find_nearest_calibration_point(
        self,
        map_x: float,
        map_y: float,
        max_distance: float = 20.0
    ) -> Optional[Tuple[int, CalibrationPoint, float]]:
        """
        查找最近的校准点

        Args:
            map_x: 点击的地图 X 坐标
            map_y: 点击的地图 Y 坐标
            max_distance: 最大匹配距离(像素)

        Returns:
            (index, point, distance) 或 None
        """
        map_config = self.config_manager.get_map_config(self.current_map_id)
        if not map_config:
            return None

        layer = map_config.get_layer_by_id(self.current_layer_id)
        if not layer:
            return None

        nearest_point = None
        nearest_index = -1
        min_distance = float('inf')

        for i, point in enumerate(layer.calibration_points):
            dx = point.map_x - map_x
            dy = point.map_y - map_y
            distance = math.sqrt(dx**2 + dy**2)

            if distance < min_distance and distance <= max_distance:
                min_distance = distance
                nearest_point = point
                nearest_index = i

        if nearest_point:
            return (nearest_index, nearest_point, min_distance)
        return None

    def _confirm_delete_calibration_point(
        self,
        index: int,
        point: CalibrationPoint,
        distance: float
    ) -> bool:
        """
        显示删除确认对话框

        Returns:
            bool: 用户是否确认删除
        """
        marker_label = f"P{index + 1}"
        message = ( t("local_map.messages.confirm_delete_calibration_point_message", marker_label=marker_label, game_x=f"{point.game_pos.x:.1f}", game_z=f"{point.game_pos.z:.1f}", distance=f"{distance:.1f}", map_x=point.map_x, map_y=point.map_y, timestamp=f"{point.timestamp}"))

        return messagebox.askyesno(t("common.confirm"), message)

    def _delete_calibration_point(self, index: int):
        """删除指定索引的校准点"""
        map_config = self.config_manager.get_map_config(self.current_map_id)
        if not map_config:
            return

        layer = map_config.get_layer_by_id(self.current_layer_id)
        if not layer:
            return

        # 删除点
        deleted_point = layer.calibration_points.pop(index)

        # 保存配置
        self.config_manager.save_config()

        # 刷新显示
        self._display_calibration_points(layer)
        self._update_calibration_info(layer)

        # 提示
        messagebox.showinfo(
            t("common.success"),
            t("local_map.messages.calibration_point_deleted", game_x=f"{deleted_point.game_pos.x:.1f}", game_z=f"{deleted_point.game_pos.z:.1f}")
        )

    def _toggle_deletion_mode(self):
        """切换删除校准点模式"""
        self.deletion_mode = not self.deletion_mode

        if self.deletion_mode:
            # 进入删除模式
            self.clear_calibration_btn.configure(
                text=t("local_map.calibration.exit_deletion_mode"),
                fg_color="red"
            )
            # 状态信息可通过calibration_info显示
            self.calibration_info.configure(
                text=t("local_map.calibration.deletion_mode_active")
            )
        else:
            # 退出删除模式
            self.clear_calibration_btn.configure(
                text=t("local_map.calibration.delete_points"),
                fg_color="darkred"
            )
            # 恢复原有校准点信息显示
            if self.current_map_id:
                map_config = self.config_manager.get_map_config(self.current_map_id)
                if map_config:
                    layer = map_config.get_layer_by_id(self.current_layer_id)
                    if layer:
                        self._update_calibration_info(layer)

    def _handle_deletion_click(self, map_x: float, map_y: float):
        """处理删除模式下的点击"""
        result = self._find_nearest_calibration_point(map_x, map_y)

        if not result:
            messagebox.showinfo(
                t("common.warning"),
                t("local_map.messages.no_calibration_point_nearby")
            )
            return

        index, point, distance = result

        # 确认删除
        if self._confirm_delete_calibration_point(index, point, distance):
            self._delete_calibration_point(index)

    def _toggle_region_marking_mode(self):
        """切换区域标记模式"""
        if not self.current_map_id:
            messagebox.showwarning(t("common.warning"), t("local_map.messages.no_map_selected"))
            return

        map_config = self.config_manager.get_map_config(self.current_map_id)
        if not map_config:
            return

        # 检查当前层级是否为楼层图
        layer = map_config.get_layer_by_id(self.current_layer_id)
        if not layer:
            messagebox.showwarning(t("common.info"), t("local_map.messages.no_layer_selected"))
            return

        if layer.is_base_map:
            messagebox.showwarning(t("common.info"), t("local_map.messages.cannot_mark_base_map"))
            return

        # 检查大地图是否存在并已加载
        base_map = map_config.get_base_map()
        if not base_map:
            messagebox.showwarning(t("common.info"), t("local_map.messages.no_base_map_configured"))
            return

        self.region_marking_mode = not self.region_marking_mode

        if self.region_marking_mode:
            # 进入区域标记模式
            # 切换到大地图显示
            from utils import path_manager
            base_map_path = path_manager.get_absolute_path(base_map.image_path)

            if not os.path.exists(base_map_path):
                messagebox.showerror(t("common.error"), t("local_map.messages.base_map_not_exist", base_map_path=base_map_path))
                self.region_marking_mode = False
                return

            # 加载大地图
            self.map_canvas.load_map(base_map_path)

            # 如果当前层级已有区域，显示现有区域点
            effective_region = layer.get_effective_region(map_config)
            if effective_region and effective_region.points:
                self.region_temp_points = list(effective_region.points)
                self._display_region_markers()

                # 显示区域来源信息
                if layer.is_region_owner():
                    self.region_info.configure(
                        text=t("local_map.floor_regions.current_region_owned", count=len(self.region_temp_points))
                    )
                else:
                    if layer.region_owner_layer_id is not None:
                        owner_layer = map_config.get_layer_by_id(layer.region_owner_layer_id)
                        owner_name = owner_layer.name if owner_layer else "None"
                        self.region_info.configure(
                            text=t("local_map.floor_regions.referenced_region", layer_id=layer.region_owner_layer_id, owner_name=owner_name, count=len(self.region_temp_points))
                        )
                    else:
                        self.region_info.configure(
                            text=t("local_map.floor_regions.current_points", count=len(self.region_temp_points))
                        )
            else:
                self.region_temp_points = []
                self.region_info.configure(
                    text=t("local_map.floor_regions.marking_mode_active", count=len(self.region_temp_points))
                )

            # 更新按钮和提示
            self.mark_region_btn.configure(
                text=t("local_map.floor_regions.complete_marking"),
                fg_color="orange"
            )
            self.status_label.configure(
                text=t("local_map.floor_regions.marking_mode_boundary", count=len(self.region_temp_points))
            )
        else:
            # 退出区域标记模式
            if len(self.region_temp_points) >= 3:
                # 保存区域
                self._save_region()
            else:
                # 点数不足，清除临时点
                self.region_temp_points = []
                # 清除Canvas上的区域标记
                self.map_canvas.clear_region_markers()

            # 恢复按钮
            self.mark_region_btn.configure(
                text=t("local_map.floor_regions.mark_region"),
                fg_color="#2d5a2d"
            )
            self.region_info.configure(
                text=t("local_map.floor_regions.region_info", count=len(self.region_temp_points))
            )

            # 切换回当前层级地图
            self._on_layer_selected(self.layer_selector.get())

    def _handle_region_marking_click(self, map_x: float, map_y: float):
        """处理区域标记模式下的点击"""
        # 添加新的区域点
        self.region_temp_points.append((map_x, map_y))

        # 在Canvas上显示标记
        self.map_canvas.add_region_point(map_x, map_y, len(self.region_temp_points))

        # 如果点数>=2，绘制连线
        if len(self.region_temp_points) >= 2:
            self.map_canvas.draw_region_lines(self.region_temp_points)

        # 更新提示信息
        count = len(self.region_temp_points)
        status = t("local_map.calibration.calibration_ready") if count >= 3 else t("local_map.calibration.calibration_not_ready")
        self.region_info.configure(
            text=t("local_map.floor_regions.marking_status", count=count, status=status)
        )
        self.status_label.configure(
            text=t("local_map.floor_regions.marking_summary", count=count, status_text="OK" if count >= 3 else "Need 3+ points")
        )

    def _display_region_markers(self):
        """显示区域标记点"""
        self.map_canvas.clear_region_markers()
        for i, (x, y) in enumerate(self.region_temp_points, 1):
            self.map_canvas.add_region_point(x, y, i)
        if len(self.region_temp_points) >= 2:
            self.map_canvas.draw_region_lines(self.region_temp_points)

    def _save_region(self):
        """保存区域标记"""
        if len(self.region_temp_points) < 3:
            messagebox.showwarning(t("common.warning"), t("local_map.messages.region_points_not_enough"))
            return

        if not self.current_map_id:
            messagebox.showerror(t("common.error"), t("local_map.messages.no_map_selected"))
            return

        from .models import Region

        # 创建新区域
        new_region = Region(points=list(self.region_temp_points))

        # 获取当前layer和map_config
        map_config = self.config_manager.get_map_config(self.current_map_id)
        if not map_config:
            return

        layer = map_config.get_layer_by_id(self.current_layer_id)
        if not layer:
            return

        # 如果当前layer是owner且已有区域，检查是否有其他layer引用
        if layer.is_region_owner() and layer.region:
            sharing_layers = map_config.get_layers_sharing_region(layer.layer_id)
            if sharing_layers:
                layer_list = "\n".join([f"Layer {l.layer_id}: {l.name}" for l in sharing_layers])
                msg = t("local_map.messages.region_sharing_warning", layer_list=layer_list)
                if not messagebox.askyesno(t("common.warning"), msg):
                    return

        # 验证区域不与现有区域重合（返回重合区域的owner信息）
        valid, error_msg, owner_info = self.config_manager.validate_region_no_overlap(
            self.current_map_id,
            new_region,
            exclude_layer_id=self.current_layer_id
        )

        if not valid:
            # 检测到重合，询问用户是否复用
            if owner_info is None:
                messagebox.showerror(t("common.error"), error_msg or t("local_map.messages.region_overlap_error"))
                return

            owner_layer_id, owner_layer_name = owner_info
            msg = t("local_map.messages.region_overlap_warning", owner_layer_id=owner_layer_id, owner_layer_name=owner_layer_name)

            if messagebox.askyesno(t("common.warning"), msg):
                # 用户选择复用
                # 验证高度范围不冲突
                valid, error_msg = self.config_manager.validate_height_in_region(
                    self.current_map_id,
                    self.current_layer_id,
                    layer.height_min,
                    layer.height_max,
                    new_region
                )

                if not valid:
                    messagebox.showerror(t("common.error"), error_msg)
                    return

                # 绑定到owner_layer
                self.config_manager.bind_layer_to_region(
                    self.current_map_id,
                    self.current_layer_id,
                    owner_layer_id
                )

                # 清除临时点
                self.region_temp_points = []
                self.map_canvas.clear_region_markers()

                messagebox.showinfo(t("common.success"), t("local_map.messages.region_bound", owner_layer_id=owner_layer_id, owner_layer_name=owner_layer_name))
                self.status_label.configure(text=t("local_map.status.region_saved"))
            else:
                # 用户取消
                messagebox.showinfo(t("common.info"), t("local_map.messages.region_cancel"))

            return

        # 没有重合，验证同区域内高度范围不冲突
        valid, error_msg = self.config_manager.validate_height_in_region(
            self.current_map_id,
            self.current_layer_id,
            layer.height_min,
            layer.height_max,
            new_region
        )

        if not valid:
            messagebox.showerror(t("common.error"), error_msg)
            return

        # 保存新区域（作为owner）
        self.config_manager.set_layer_region(
            self.current_map_id,
            self.current_layer_id,
            new_region
        )

        # 清除临时点
        self.region_temp_points = []
        self.map_canvas.clear_region_markers()

        messagebox.showinfo(t("common.success"), t("local_map.messages.region_saved", count=len(new_region.points)))
        self.status_label.configure(text=t("local_map.status.region_marking_saved"))

    def _reset_region_binding(self):
        """重置当前层级的区域绑定"""
        if not self.current_map_id:
            messagebox.showwarning(t("common.warning"), t("local_map.messages.no_map_selected"))
            return

        map_config = self.config_manager.get_map_config(self.current_map_id)
        if not map_config:
            return

        layer = map_config.get_layer_by_id(self.current_layer_id)
        if not layer:
            messagebox.showwarning(t("common.warning"), t("local_map.messages.no_layer_selected"))
            return

        if layer.is_base_map:
            messagebox.showwarning(t("common.warning"), t("local_map.messages.cannot_mark_base_map"))
            return

        # 检查是否有区域绑定
        effective_region = layer.get_effective_region(map_config)
        if not effective_region:
            messagebox.showinfo(t("common.info"), t("local_map.messages.layer_has_no_region"))
            return

        # 确认操作
        if layer.is_region_owner():
            # 拥有区域，检查是否有其他层引用
            sharing_layers = map_config.get_layers_sharing_region(layer.layer_id)
            if sharing_layers:
                layer_list = "\n".join([f"Layer {l.layer_id}: {l.name}" for l in sharing_layers])
                msg = t("local_map.messages.region_sharing_warning", layer_list=layer_list)
                if not messagebox.askyesno(t("common.confirm"), msg):
                    return
        else:
            # 引用区域
            if layer.region_owner_layer_id is None:
                messagebox.showwarning(t("common.warning"), t("local_map.messages.layer_has_no_region"))
                return

            owner_info = f"Layer {layer.region_owner_layer_id}"
            owner_layer = map_config.get_layer_by_id(layer.region_owner_layer_id)
            if owner_layer:
                owner_info = f"Layer {owner_layer.layer_id}: {owner_layer.name}"

            msg = t("local_map.messages.unbind_region_confirm", owner_info=owner_info)
            if not messagebox.askyesno(t("common.confirm"), msg):
                return

        # 执行重置
        self.config_manager.unbind_layer_region(self.current_map_id, self.current_layer_id)

        messagebox.showinfo(t("common.success"), t("local_map.messages.region_unbound_success"))
        self.region_info.configure(text=t("local_map.floor_regions.region_info", count=0))

    def _delete_layer(self):
        """删除当前选中的层级"""
        if not self.current_map_id:
            messagebox.showwarning(t("common.warning"), t("local_map.messages.no_map_selected"))
            return

        map_config = self.config_manager.get_map_config(self.current_map_id)
        if not map_config:
            return

        layer = map_config.get_layer_by_id(self.current_layer_id)
        if not layer:
            messagebox.showwarning(t("common.info"), t("local_map.messages.select_layer_first"))
            return

        # 防止删除大地图
        if layer.is_base_map:
            messagebox.showerror(t("common.error"), t("local_map.messages.cannot_delete_base_map"))
            return

        # 构建确认信息
        confirm_msg = t("local_map.messages.delete_layer_confirm", layer_id=layer.layer_id, layer_name=layer.name)

        # 如果是区域母层级，警告会影响其他层级
        if layer.is_region_owner():
            sharing_layers = map_config.get_layers_sharing_region(layer.layer_id)
            if sharing_layers:
                layer_list = "\n".join([f"  - Layer {l.layer_id}: {l.name}" for l in sharing_layers])
                confirm_msg += t("local_map.messages.region_owner_deletion_warning", layer_list=layer_list)

        # 警告信息
        confirm_msg += t("local_map.messages.irreversible_action_warning")

        # 确认对话框
        if not messagebox.askyesno(t("local_map.messages.delete_layer_title"), confirm_msg, icon="warning"):
            return

        # 执行删除
        success, error_msg = self.config_manager.delete_layer(
            self.current_map_id,
            self.current_layer_id
        )

        if success:
            messagebox.showinfo(t("common.success"), t("local_map.messages.layer_deleted_detail", layer_id=layer.layer_id, layer_name=layer.name))

            # 重新加载地图配置（刷新层级列表）
            self._on_map_selected(self.map_selector.get())

            # 如果没有层级了，清空状态
            if not map_config.layers:
                self.current_layer_id = 0
                self.layer_selector.configure(values=["None"])
                self.layer_selector.set("None")
                self.status_label.configure(text=t("local_map.status.all_layers_deleted"))

            self.status_label.configure(text=t("local_map.status.layer_deleted", layer_id=layer.layer_id))
        else:
            messagebox.showerror(t("local_map.messages.deletion_failed"), error_msg or t("local_map.messages.unknown_error"))

    def _on_zoom_changed(self, value):
        """缩放滑块改变"""
        self.map_canvas.set_zoom(float(value))

    def _reset_view(self):
        """重置视图"""
        self.map_canvas.reset_view()
        self.zoom_slider.set(1.0)

    def _open_settings(self):
        """打开路径设置对话框"""
        dialog = PathSettingsDialog(
            self,
            current_screenshots_path=self.screenshots_path,
            current_logs_path=self.logs_path
        )

        if dialog.result:
            screenshots_path, logs_path = dialog.result
            self.screenshots_path = screenshots_path
            self.logs_path = logs_path

            # 如果校准模式开启，重启监控
            if self.calibration_mode:
                self._stop_screenshot_monitoring()
                self._start_screenshot_monitoring()

            messagebox.showinfo(t("common.success"), t("local_map.messages.settings_updated"))

    def _toggle_overlay(self):
        """显示/隐藏悬浮地图"""
        if not self.current_map_id or not self.current_layer_id is not None:
            messagebox.showwarning(t("common.info"), t("local_map.messages.select_map_and_layer"))
            return

        map_config = self.config_manager.get_map_config(self.current_map_id)
        if not map_config:
            return

        layer = map_config.get_layer_by_id(self.current_layer_id)
        if not layer or not os.path.exists(layer.image_path):
            messagebox.showwarning(t("common.info"), t("local_map.messages.map_image_not_exist"))
            return

        if not self.overlay_window:
            # 创建悬浮窗
            self.overlay_window = OverlayMapWindow(self.winfo_toplevel())
            self.overlay_window.load_map(layer.image_path)

            # 设置状态变化回调（自动保存）
            self.overlay_window.on_state_changed = self._save_overlay_state

            # 加载保存的状态
            self._load_overlay_state()

            # 绑定关闭事件，自动保存状态
            self.overlay_window.protocol("WM_DELETE_WINDOW", self._on_overlay_close)

        if self.overlay_visible:
            # 隐藏
            self.overlay_window.hide_window()
            self.overlay_visible = False
            self.overlay_toggle_btn.configure(text=t("local_map.core_functions.show_btn"))
            self.overlay_lock_btn.configure(state="disabled")
        else:
            # 显示
            self.overlay_window.show_window()
            self.overlay_visible = True
            self.overlay_toggle_btn.configure(text=t("local_map.core_functions.hide_btn"))
            self.overlay_lock_btn.configure(state="normal")

            # 如果有玩家位置，更新到悬浮窗
            if self.latest_screenshot_pos:
                self._update_overlay_position()

    def _toggle_overlay_lock(self):
        """切换悬浮窗锁定状态"""
        if self.overlay_window:
            new_state = not self.overlay_window.is_locked
            self.overlay_window.set_lock_state(new_state)

            if new_state:
                self.overlay_lock_btn.configure(text=t("local_map.core_functions.unlock_btn"))
            else:
                self.overlay_lock_btn.configure(text=t("local_map.core_functions.lock_btn"))

    def _on_opacity_changed(self, value):
        """透明度改变"""
        if self.overlay_window:
            self.overlay_window.set_opacity(value)
            # 自动保存状态
            self._save_overlay_state()

    def _load_overlay_state(self):
        """加载悬浮窗状态"""
        if not self.overlay_window:
            return

        try:
            import json
            config_path = "map_config.json"
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    overlay_state = data.get("overlay_state")
                    if overlay_state:
                        self.overlay_window.load_state(overlay_state)
                        # 同步UI控件
                        self.opacity_slider.set(overlay_state.get("opacity", 0.85))
                        if overlay_state.get("player_centered", True):
                            self.player_centered_switch.select()
                        else:
                            self.player_centered_switch.deselect()

                        # 同步尺寸输入框
                        width = overlay_state.get("width", 400)
                        height = overlay_state.get("height", 400)
                        self.overlay_width_entry.delete(0, "end")
                        self.overlay_width_entry.insert(0, str(width))
                        self.overlay_height_entry.delete(0, "end")
                        self.overlay_height_entry.insert(0, str(height))
        except Exception as e:
            print(f"加载悬浮窗状态失败: {e}")

    def _save_overlay_state(self):
        """保存悬浮窗状态"""
        if not self.overlay_window:
            return

        try:
            import json
            config_path = "map_config.json"

            # 读取现有配置
            data = {}
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            # 更新悬浮窗状态
            data["overlay_state"] = self.overlay_window.get_state()

            # 保存
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存悬浮窗状态失败: {e}")

    def _on_overlay_close(self):
        """悬浮窗关闭事件"""
        # 保存状态
        self._save_overlay_state()
        # 隐藏窗口而不是销毁
        self._toggle_overlay()

    def _toggle_player_centered(self):
        """切换玩家居中模式"""
        if self.overlay_window:
            new_state = not self.overlay_window.player_centered
            self.overlay_window.set_player_centered(new_state)

    def _apply_settings(self):
        """应用窗口尺寸和缩放步进设置"""
        try:
            # 应用窗口尺寸
            width = int(self.overlay_width_entry.get())
            height = int(self.overlay_height_entry.get())

            if width < 200 or height < 200:
                messagebox.showerror(t("common.error"), t("local_map.messages.window_size_too_small"))
                return

            if self.overlay_window:
                self.overlay_window.geometry(f"{width}x{height}")
                self.overlay_window.window_width = width
                self.overlay_window.window_height = height

            # 应用缩放步进值
            try:
                step = float(self.zoom_step_entry.get())
                if 0.01 <= step <= 1.0:
                    self.zoom_step = step
                    self.func_config.update_zoom_step(step)
                else:
                    raise ValueError("步进值必须在0.01-1.0之间")
            except ValueError as e:
                messagebox.showerror(t("common.error"), t("local_map.messages.zoom_step_invalid", error=str(e)))
                return

            messagebox.showinfo(t("common.success"), t("local_map.messages.settings_applied"))
        except ValueError:
            messagebox.showerror(t("common.error"), t("local_map.messages.invalid_number"))

    def _update_overlay_position(self):
        """更新悬浮窗玩家位置"""
        if not self.overlay_window or not self.overlay_visible:
            return

        if not self.latest_screenshot_pos:
            return

        if not self.current_map_id:
            return

        # 计算地图坐标
        try:
            # 获取地图配置
            map_config = self.config_manager.get_map_config(self.current_map_id)
            if not map_config:
                return

            # === 新的智能层级选择逻辑（与主Canvas逻辑完全一致）===
            # 1. 获取大地图
            base_map = map_config.get_base_map()
            if not base_map:
                # 没有大地图，回退到旧逻辑（向后兼容）
                layer = map_config.get_layer_by_height(self.latest_screenshot_pos.position.y)
                if not layer:
                    layer = map_config.get_layer_by_id(self.current_layer_id)
                if not layer:
                    return
            else:
                # 有大地图，使用新的智能选择
                # 2. 计算玩家在大地图上的坐标（如果大地图已校准）
                base_map_transform = None
                if base_map.is_calibrated():
                    try:
                        # === 改：使用全局缓存（避免重复计算）===
                        from modules.local_map.map_resource_cache import get_resource_cache
                        resource_cache = get_resource_cache()

                        base_map_transform = resource_cache.get_transform(
                            self.config_manager,
                            self.current_map_id,
                            base_map.layer_id,
                            player_pos=self.latest_screenshot_pos.position
                        )
                        # === 改动结束 ===
                    except Exception as e:
                        print(f"悬浮窗: 计算大地图坐标变换失败: {e}")

                # 3. 智能选择激活的层级（区域+高度）
                layer = map_config.get_active_layer(
                    self.latest_screenshot_pos.position,
                    base_map_transform
                )

                if not layer:
                    return

            # === 改：使用全局缓存的Transform（避免重复计算）===
            from modules.local_map.map_resource_cache import get_resource_cache
            resource_cache = get_resource_cache()

            transform = resource_cache.get_transform(
                self.config_manager,
                self.current_map_id,
                layer.layer_id,
                player_pos=self.latest_screenshot_pos.position  # 启用局部插值
            )
            # === 改动结束 ===

            map_x, map_y = transform.transform(self.latest_screenshot_pos.position)
            yaw = self.latest_screenshot_pos.rotation.to_yaw()

            # 应用旋转偏移
            yaw += layer.rotation_offset

            # 更新悬浮窗位置
            self.overlay_window.update_player_position(map_x, map_y, yaw)
        except Exception as e:
            print(f"更新悬浮窗位置失败: {e}")

    def _set_overlay_hotkey(self):
        """设置悬浮窗快捷键"""
        self.hotkey_btn.configure(text=t("local_map.core_functions.hotkey_press_any"))

        def on_key_captured(key_name):
            """Callback when key is captured"""
            self.after(0, lambda: self._finish_overlay_hotkey_assignment(key_name))

        self.hotkey_manager.enter_assignment_mode(
            requester_id="local_map.overlay_toggle",
            callback=on_key_captured,
            timeout=10.0
        )

    def _finish_overlay_hotkey_assignment(self, key_name: str):
        """Finish overlay hotkey assignment"""
        # Unregister old hotkey
        if self.overlay_hotkey:
            self.hotkey_manager.unregister_hotkey("local_map.overlay_toggle")

        # Update config
        self.overlay_hotkey = key_name
        self.func_config.update_overlay_hotkey(key_name)

        # Register new hotkey
        self.hotkey_manager.register_hotkey(
            hotkey_id="local_map.overlay_toggle",
            key=key_name,
            callback=self._on_overlay_hotkey,
            context="global",
            debounce=0.2
        )

        # Update UI
        self.hotkey_btn.configure(text=t("local_map.core_functions.overlay_hotkey", overlay_hotkey=key_name))
        messagebox.showinfo(t("common.success"), t("local_map.messages.overlay_hotkey_set_success", key_name=key_name))

    def _set_zoom_in_hotkey(self):
        """设置放大快捷键"""
        self.zoom_in_hotkey_btn.configure(text=t("local_map.core_functions.hotkey_press_any"))

        def on_key_captured(key_name):
            """Callback when key is captured"""
            self.after(0, lambda: self._finish_zoom_in_hotkey_assignment(key_name))

        self.hotkey_manager.enter_assignment_mode(
            requester_id="local_map.zoom_in",
            callback=on_key_captured,
            timeout=10.0
        )

    def _finish_zoom_in_hotkey_assignment(self, key_name: str):
        """Finish zoom in hotkey assignment"""
        # Unregister old hotkey
        if self.zoom_in_hotkey:
            self.hotkey_manager.unregister_hotkey("local_map.zoom_in")

        # Update config
        self.zoom_in_hotkey = key_name
        self.func_config.update_zoom_hotkeys(key_name, self.zoom_out_hotkey)

        # Register new hotkey
        self.hotkey_manager.register_hotkey(
            hotkey_id="local_map.zoom_in",
            key=key_name,
            callback=self._on_zoom_in_hotkey,
            context="global",
            debounce=0.15
        )

        # Update UI
        self.zoom_in_hotkey_btn.configure(text=t("local_map.core_functions.zoom_in_hotkey", zoom_in_hotkey=key_name))
        messagebox.showinfo(t("common.success"), t("local_map.messages.zoom_in_hotkey_set_success", key_name=key_name))

    def _set_zoom_out_hotkey(self):
        """设置缩小快捷键"""
        self.zoom_out_hotkey_btn.configure(text=t("local_map.core_functions.hotkey_press_any"))

        def on_key_captured(key_name):
            """Callback when key is captured"""
            self.after(0, lambda: self._finish_zoom_out_hotkey_assignment(key_name))

        self.hotkey_manager.enter_assignment_mode(
            requester_id="local_map.zoom_out",
            callback=on_key_captured,
            timeout=10.0
        )

    def _finish_zoom_out_hotkey_assignment(self, key_name: str):
        """Finish zoom out hotkey assignment"""
        # Unregister old hotkey
        if self.zoom_out_hotkey:
            self.hotkey_manager.unregister_hotkey("local_map.zoom_out")

        # Update config
        self.zoom_out_hotkey = key_name
        self.func_config.update_zoom_hotkeys(self.zoom_in_hotkey, key_name)

        # Register new hotkey
        self.hotkey_manager.register_hotkey(
            hotkey_id="local_map.zoom_out",
            key=key_name,
            callback=self._on_zoom_out_hotkey,
            context="global",
            debounce=0.15
        )

        # Update UI
        self.zoom_out_hotkey_btn.configure(text=t("local_map.core_functions.zoom_out_hotkey", zoom_out_hotkey=key_name))
        messagebox.showinfo(t("common.success"), t("local_map.messages.zoom_out_hotkey_set_success", key_name=key_name))

    def _register_hotkeys(self):
        """Register all hotkeys with the unified hotkey manager"""
        # Register overlay toggle hotkey
        if self.overlay_hotkey:
            self.hotkey_manager.register_hotkey(
                hotkey_id="local_map.overlay_toggle",
                key=self.overlay_hotkey,
                callback=self._on_overlay_hotkey,
                context="global",
                debounce=0.2
            )

        # Register zoom in hotkey
        if self.zoom_in_hotkey:
            self.hotkey_manager.register_hotkey(
                hotkey_id="local_map.zoom_in",
                key=self.zoom_in_hotkey,
                callback=self._on_zoom_in_hotkey,
                context="global",
                debounce=0.15
            )

        # Register zoom out hotkey
        if self.zoom_out_hotkey:
            self.hotkey_manager.register_hotkey(
                hotkey_id="local_map.zoom_out",
                key=self.zoom_out_hotkey,
                callback=self._on_zoom_out_hotkey,
                context="global",
                debounce=0.15
            )

    def _unregister_hotkeys(self):
        """Unregister all hotkeys from the unified hotkey manager"""
        self.hotkey_manager.unregister_hotkey("local_map.overlay_toggle")
        self.hotkey_manager.unregister_hotkey("local_map.zoom_in")
        self.hotkey_manager.unregister_hotkey("local_map.zoom_out")

    def _on_overlay_hotkey(self):
        """Callback when overlay toggle hotkey is pressed"""
        self.after(0, self._toggle_overlay)

    def _on_zoom_in_hotkey(self):
        """Callback when zoom in hotkey is pressed"""
        # Only zoom if overlay window exists and is visible
        if self.overlay_window and self.overlay_window.winfo_exists():
            self.after(0, lambda: self._hotkey_zoom(self.zoom_step))

    def _on_zoom_out_hotkey(self):
        """Callback when zoom out hotkey is pressed"""
        # Only zoom if overlay window exists and is visible
        if self.overlay_window and self.overlay_window.winfo_exists():
            self.after(0, lambda: self._hotkey_zoom(-self.zoom_step))

    def _hotkey_zoom(self, delta: float):
        """
        通过快捷键调整悬浮窗缩放

        Args:
            delta: 缩放变化量（正数放大，负数缩小）
        """
        if not self.overlay_window or not self.overlay_window.winfo_exists():
            return

        try:
            current_zoom = self.overlay_window.map_canvas.zoom
            new_zoom = current_zoom + delta

            # 限制在有效范围内
            new_zoom = max(
                self.overlay_window.map_canvas.min_zoom,
                min(self.overlay_window.map_canvas.max_zoom, new_zoom)
            )

            # 应用缩放
            self.overlay_window.map_canvas.set_zoom(new_zoom)
            self.overlay_window._saved_zoom = new_zoom

            # 如果是玩家居中模式，重新计算offset
            if self.overlay_window.player_centered:
                self.overlay_window._update_player_centering()
        except Exception as e:
            print(f"快捷键缩放失败: {e}")

    def _export_map_config(self):
        """导出地图配置（包括图片和校准点）"""
        if not self.current_map_id:
            messagebox.showwarning(t("common.info"), t("local_map.messages.select_export_map"))
            return

        try:
            import zipfile
            import json
            from datetime import datetime
            from pathlib import Path

            map_config = self.config_manager.get_map_config(self.current_map_id)
            if not map_config:
                messagebox.showerror(t("common.error"), t("local_map.messages.map_config_not_exist"))
                return

            # 选择保存位置
            filename = filedialog.asksaveasfilename(
                title=t("local_map.messages.export_map_config_title"),
                defaultextension=".zip",
                initialfile=f"map_{map_config.map_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
            )

            if not filename:
                return

            # 创建ZIP文件
            with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 导出配置JSON
                config_data = {
                    "version": "1.0",
                    "export_date": datetime.now().isoformat(),
                    "map_id": map_config.map_id,
                    "display_name": map_config.display_name,
                    "default_layer_id": map_config.default_layer_id,
                    "layers": []
                }

                # 使用路径管理器
                from utils import path_manager

                # 导出每个层级
                for layer in map_config.layers:
                    # 将相对路径转换为绝对路径
                    absolute_image_path = path_manager.get_absolute_path(layer.image_path)

                    # 添加层级配置
                    layer_data = {
                        "layer_id": layer.layer_id,
                        "name": layer.name,
                        "image_filename": Path(absolute_image_path).name,  # 只保存文件名
                        "height_min": layer.height_min,
                        "height_max": layer.height_max,
                        "rotation_offset": layer.rotation_offset,
                        "calibration_points": [
                            {
                                "game_pos": {"x": pt.game_pos.x, "y": pt.game_pos.y, "z": pt.game_pos.z},
                                "map_x": pt.map_x,
                                "map_y": pt.map_y,
                                "timestamp": pt.timestamp.isoformat()
                            }
                            for pt in layer.calibration_points
                        ]
                    }
                    config_data["layers"].append(layer_data)

                    # 添加图片文件到ZIP（使用绝对路径）
                    if os.path.exists(absolute_image_path):
                        zipf.write(
                            absolute_image_path,
                            f"images/{Path(absolute_image_path).name}"
                        )

                # 写入配置JSON
                zipf.writestr("config.json", json.dumps(config_data, ensure_ascii=False, indent=2))

            messagebox.showinfo(t("common.success"), t("local_map.messages.export_success", filename=filename, layer_count=len(map_config.layers)))
        except Exception as e:
            messagebox.showerror(t("common.error"), t("local_map.messages.export_failed", error=str(e)))
            import traceback
            traceback.print_exc()

    def _import_map_config(self):
        """导入地图配置（包括图片和校准点）"""
        try:
            import zipfile
            import json
            from datetime import datetime
            from pathlib import Path
            from .models import MapConfig, MapLayer, CalibrationPoint, Position3D

            # 选择ZIP文件
            filename = filedialog.askopenfilename(
                title=t("local_map.messages.import_map_config_title"),
                filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
            )

            if not filename:
                return

            # 临时目录用于解压
            temp_dir = "temp_map_import"
            os.makedirs(temp_dir, exist_ok=True)

            try:
                # 解压ZIP
                with zipfile.ZipFile(filename, 'r') as zipf:
                    zipf.extractall(temp_dir)

                # 读取配置文件
                config_path = os.path.join(temp_dir, "config.json")
                if not os.path.exists(config_path):
                    messagebox.showerror(t("common.error"), t("local_map.messages.invalid_map_package"))
                    return

                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                # 检查是否已存在同ID的地图
                map_id = config_data["map_id"]
                existing = self.config_manager.get_map_config(map_id)

                if existing:
                    response = messagebox.askyesnocancel(
                        "地图已存在",
                        f"地图 '{config_data['display_name']}' (ID: {map_id}) 已存在。\n\n是：覆盖\n否：取消导入"
                    )

                    if not response:  # No or Cancel
                        return

                # 使用路径管理器获取地图目录
                from utils import path_manager
                map_images_dir = path_manager.get_map_dir(map_id)

                # 导入层级
                layers = []
                for layer_data in config_data["layers"]:
                    # 复制图片文件
                    image_filename = layer_data["image_filename"]
                    source_image = os.path.join(temp_dir, "images", image_filename)
                    target_image = os.path.join(map_images_dir, image_filename)

                    if os.path.exists(source_image):
                        import shutil
                        shutil.copy2(source_image, target_image)

                    # 转换为相对路径
                    relative_image_path = path_manager.get_relative_path(target_image)

                    # 创建校准点
                    calibration_points = [
                        CalibrationPoint(
                            game_pos=Position3D(
                                x=pt["game_pos"]["x"],
                                y=pt["game_pos"]["y"],
                                z=pt["game_pos"]["z"]
                            ),
                            map_x=pt["map_x"],
                            map_y=pt["map_y"],
                            timestamp=datetime.fromisoformat(pt["timestamp"])
                        )
                        for pt in layer_data["calibration_points"]
                    ]

                    # 创建层级（使用相对路径）
                    layer = MapLayer(
                        layer_id=layer_data["layer_id"],
                        name=layer_data["name"],
                        image_path=relative_image_path,
                        height_min=layer_data["height_min"],
                        height_max=layer_data["height_max"],
                        rotation_offset=layer_data.get("rotation_offset", 0.0),
                        calibration_points=calibration_points
                    )
                    layers.append(layer)

                # 创建地图配置
                map_config = MapConfig(
                    map_id=map_id,
                    display_name=config_data["display_name"],
                    default_layer_id=config_data["default_layer_id"],
                    layers=layers
                )

                # 保存到配置管理器
                if existing:
                    # 删除旧的
                    del self.config_manager.maps[map_id]

                self.config_manager.maps[map_id] = map_config
                self.config_manager.save_config()

                # 刷新UI
                self._load_maps()

                messagebox.showinfo(
                    "导入成功",
                    f"地图 '{config_data['display_name']}' 导入成功！\n\n包含 {len(layers)} 个层级"
                )

            finally:
                # 清理临时目录
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

        except Exception as e:
            messagebox.showerror(t("common.error"), t("local_map.messages.import_failed_detail", error=str(e)))
            import traceback
            traceback.print_exc()

    def cleanup(self):
        """清理资源"""
        # 停止快捷键线程
        self.running = False

        # Unregister all hotkeys
        self._unregister_hotkeys()

        self._stop_screenshot_monitoring()
        self._stop_log_monitoring()

        # 关闭悬浮窗
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None

    def _migrate_config_if_needed(self):
        """
        从旧的map_config.json迁移overlay_hotkey到map_function_config.json
        仅在首次运行且检测到旧配置时执行
        """
        old_config_file = "map_config.json"
        new_config_file = "map_function_config.json"

        # 如果新配置文件已存在，跳过迁移
        if os.path.exists(new_config_file):
            return

        try:
            # 读取旧配置文件中的overlay_hotkey
            if os.path.exists(old_config_file):
                with open(old_config_file, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    old_hotkey = old_data.get("overlay_hotkey")

                # 如果存在旧的快捷键配置，迁移到新文件
                if old_hotkey:
                    self.func_config.config.overlay_hotkey = old_hotkey
                    self.func_config.save()
                    print(f"已迁移overlay_hotkey: {old_hotkey} -> {new_config_file}")

                    # 从旧文件中删除overlay_hotkey字段
                    del old_data["overlay_hotkey"]
                    with open(old_config_file, "w", encoding="utf-8") as f:
                        json.dump(old_data, f, ensure_ascii=False, indent=2)
                    print(f"已从 {old_config_file} 中移除 overlay_hotkey 字段")
        except Exception as e:
            print(f"配置迁移失败: {e}")


class LayerConfigDialog(ctk.CTkToplevel):
    """层级配置对话框"""

    def __init__(self, parent, title: str, layer_id: int = 0, layer_name: str = "",
                 height_min: float = 0.0, height_max: float = 10.0, rotation_offset: float = 0.0,
                 is_base_map: bool = False):
        super().__init__(parent)

        self.result = None

        self.title(title)
        self.geometry("420x480")
        self.resizable(True, True)
        self.minsize(420, 480)

        # 创建滚动框架
        scroll_frame = ctk.CTkScrollableFrame(self, width=380, height=360)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        # === 导入类型选择 ===
        ctk.CTkLabel(
            scroll_frame,
            text="导入类型:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(10, 5))

        type_hint = ctk.CTkLabel(
            scroll_frame,
            text="大地图：全景地图，作为基础层（每个地图必须先导入大地图）\n楼层图：特定建筑的楼层地图（需要在大地图上标记激活区域）",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        type_hint.pack(pady=(0, 5))

        self.map_type_var = ctk.StringVar(value="base_map" if is_base_map else "floor_map")

        type_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        type_frame.pack(pady=(0, 10))

        ctk.CTkRadioButton(
            type_frame,
            text="大地图 (Base Map)",
            variable=self.map_type_var,
            value="base_map"
        ).pack(side="left", padx=10)

        ctk.CTkRadioButton(
            type_frame,
            text="楼层图 (Floor Map)",
            variable=self.map_type_var,
            value="floor_map"
        ).pack(side="left", padx=10)

        # 分隔线
        ctk.CTkFrame(scroll_frame, height=1, fg_color="gray40").pack(fill="x", padx=15, pady=10)

        # 层级ID
        ctk.CTkLabel(scroll_frame, text="层级ID:").pack(pady=(5, 5))
        self.layer_id_entry = ctk.CTkEntry(scroll_frame, width=360)
        self.layer_id_entry.insert(0, str(layer_id))
        self.layer_id_entry.pack(pady=(0, 10))

        # 层级名称
        ctk.CTkLabel(scroll_frame, text="层级名称:").pack(pady=(5, 5))
        self.layer_name_entry = ctk.CTkEntry(scroll_frame, width=360)
        self.layer_name_entry.insert(0, layer_name or "Ground Floor")
        self.layer_name_entry.pack(pady=(0, 10))

        # 最小高度
        ctk.CTkLabel(scroll_frame, text="最小高度 (Y坐标):").pack(pady=(5, 5))
        self.height_min_entry = ctk.CTkEntry(scroll_frame, width=360)
        self.height_min_entry.insert(0, str(height_min))
        self.height_min_entry.pack(pady=(0, 10))

        # 最大高度
        ctk.CTkLabel(scroll_frame, text="最大高度 (Y坐标):").pack(pady=(5, 5))
        self.height_max_entry = ctk.CTkEntry(scroll_frame, width=360)
        self.height_max_entry.insert(0, str(height_max))
        self.height_max_entry.pack(pady=(0, 10))

        # 地图旋转偏移
        ctk.CTkLabel(scroll_frame, text="地图旋转偏移 (度数):").pack(pady=(5, 5))
        rotation_hint = ctk.CTkLabel(
            scroll_frame,
            text="如果地图相对游戏世界旋转了，请输入旋转角度\n例如：地图上北下南 = 0°，地图旋转180° = 180°",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        rotation_hint.pack(pady=(0, 5))
        self.rotation_offset_entry = ctk.CTkEntry(scroll_frame, width=360)
        self.rotation_offset_entry.insert(0, str(rotation_offset))
        self.rotation_offset_entry.pack(pady=(0, 15))

        # 按钮框架（固定在底部）
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame,
            text="确定",
            command=self._on_ok,
            width=120
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.destroy,
            width=120
        ).pack(side="left", padx=10)

        # 模态对话框
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def _on_ok(self):
        """确定按钮"""
        try:
            layer_id = int(self.layer_id_entry.get())
            layer_name = self.layer_name_entry.get()
            height_min = float(self.height_min_entry.get())
            height_max = float(self.height_max_entry.get())
            rotation_offset = float(self.rotation_offset_entry.get())
            is_base_map = (self.map_type_var.get() == "base_map")

            if not layer_name:
                messagebox.showwarning(t("common.info"), t("local_map.messages.enter_layer_name"))
                return

            if height_min >= height_max:
                messagebox.showwarning(t("common.info"), t("local_map.messages.height_min_max_error"))
                return

            self.result = (layer_id, layer_name, height_min, height_max, rotation_offset, is_base_map)
            self.destroy()

        except ValueError:
            messagebox.showwarning(t("common.info"), t("local_map.messages.invalid_number_value"))


class PathSettingsDialog(ctk.CTkToplevel):
    """路径设置对话框"""

    def __init__(self, parent, current_screenshots_path: str = "", current_logs_path: str = ""):
        super().__init__(parent)

        self.result = None

        self.title("路径设置")
        self.geometry("600x300")
        self.resizable(True, True)
        self.minsize(600, 300)

        # 说明文本
        info_label = ctk.CTkLabel(
            self,
            text="配置塔科夫截图和日志文件夹路径",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        info_label.pack(pady=(20, 10))

        # 截图路径
        screenshot_frame = ctk.CTkFrame(self, fg_color="transparent")
        screenshot_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(screenshot_frame, text="截图文件夹:").pack(anchor="w", pady=(0, 5))

        screenshot_input_frame = ctk.CTkFrame(screenshot_frame, fg_color="transparent")
        screenshot_input_frame.pack(fill="x")

        self.screenshots_entry = ctk.CTkEntry(screenshot_input_frame, width=450)
        self.screenshots_entry.insert(0, current_screenshots_path)
        self.screenshots_entry.pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            screenshot_input_frame,
            text="浏览",
            command=self._browse_screenshots,
            width=80
        ).pack(side="left")

        # 日志路径
        logs_frame = ctk.CTkFrame(self, fg_color="transparent")
        logs_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(logs_frame, text="日志文件夹:").pack(anchor="w", pady=(0, 5))

        logs_input_frame = ctk.CTkFrame(logs_frame, fg_color="transparent")
        logs_input_frame.pack(fill="x")

        self.logs_entry = ctk.CTkEntry(logs_input_frame, width=450)
        self.logs_entry.insert(0, current_logs_path)
        self.logs_entry.pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            logs_input_frame,
            text="浏览",
            command=self._browse_logs,
            width=80
        ).pack(side="left")

        # 提示信息
        hint_label = ctk.CTkLabel(
            self,
            text="提示: 截图路径通常在\"文档\\Escape From Tarkov\\Screenshots\"\n"
                 "日志路径通常在游戏安装目录的\"Logs\"文件夹",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        hint_label.pack(pady=10)

        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="确定",
            command=self._on_ok,
            width=120
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.destroy,
            width=120
        ).pack(side="left", padx=10)

        # 模态对话框
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def _browse_screenshots(self):
        """浏览截图文件夹"""
        folder = filedialog.askdirectory(
            title=t("local_map.messages.select_screenshot_folder"),
            initialdir=self.screenshots_entry.get()
        )
        if folder:
            self.screenshots_entry.delete(0, "end")
            self.screenshots_entry.insert(0, folder)

    def _browse_logs(self):
        """浏览日志文件夹"""
        folder = filedialog.askdirectory(
            title=t("local_map.messages.select_log_folder"),
            initialdir=self.logs_entry.get()
        )
        if folder:
            self.logs_entry.delete(0, "end")
            self.logs_entry.insert(0, folder)

    def _on_ok(self):
        """确定按钮"""
        screenshots_path = self.screenshots_entry.get().strip()
        logs_path = self.logs_entry.get().strip()

        if not screenshots_path:
            messagebox.showwarning(t("common.info"), t("local_map.messages.enter_screenshot_path"))
            return

        if not os.path.exists(screenshots_path):
            if not messagebox.askyesno(
                "确认",
                f"截图文件夹不存在:\n{screenshots_path}\n\n是否继续使用此路径？"
            ):
                return

        self.result = (screenshots_path, logs_path)
        self.destroy()
