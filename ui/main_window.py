import customtkinter as ctk
import webbrowser
from tkinter import messagebox
from typing import Optional
from modules.screen_filter.ui import ScreenFilterUI
from modules.local_map.ui import LocalMapUI
from modules.global_settings.ui import GlobalSettingsUI
from utils.global_config import get_global_config
from utils.i18n import t
from utils.version_checker import get_version_checker
from version import __version__ as VERSION

class MainWindow(ctk.CTk):
    """Main application window with tab-based navigation"""

    def __init__(self):
        super().__init__()

        self.title(t("main_window.title"))
        self.geometry("1200x800")

        # Get global config
        self.global_config = get_global_config()

        # Initialize version checker
        self.version_checker = get_version_checker()
        self.latest_version = None
        self.update_available = False

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Toolbar row (fixed height)
        self.grid_rowconfigure(1, weight=1)  # Tabview row (expandable)
        # self.grid_rowconfigure(2, weight=0)  # Credit row (fixed height)

        # Create toolbar
        self._create_toolbar()

        # # Create credit row
        # self._create_credit_row()

        # Create tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=0)

        # Add tabs
        self.tabview.add(t("screen_filter.title"))
        self.tabview.add(t("local_map.title"))
        self.tabview.add(t("global_settings.title"))

        # ========== 调整初始化顺序 ==========

        # 1. 先初始化全局设置 (检测并加载路径配置)
        self.global_settings_tab = GlobalSettingsUI(self.tabview.tab(t("global_settings.title")))
        self.global_settings_tab.pack(fill="both", expand=True)

        # 2. 初始化屏幕滤镜
        self.screen_filter_tab = ScreenFilterUI(self.tabview.tab(t("screen_filter.title")))
        self.screen_filter_tab.pack(fill="both", expand=True)

        # 3. 最后初始化本地地图 (从全局配置读取路径)
        self.local_map_tab = LocalMapUI(self.tabview.tab(t("local_map.title")))
        self.local_map_tab.pack(fill="both", expand=True)

        # 连接屏幕滤镜到悬浮窗
        self.screen_filter_tab.set_overlay_window_callback(
            lambda: self.local_map_tab.overlay_window
        )

        # 设置默认tab
        self.tabview.set(t("screen_filter.title"))

        # Start auto version check in background
        self._start_auto_version_check()

    def _create_toolbar(self):
        """创建顶部工具栏"""
        toolbar_frame = ctk.CTkFrame(self, height=50, corner_radius=0)
        toolbar_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        toolbar_frame.grid_propagate(False)  # 固定高度

        def open_github(event=None):
            webbrowser.open("https://github.com/Smiorld")
            
        def open_bilibili(event=None):
            webbrowser.open("https://space.bilibili.com/2148654")
            
        def open_douyin(event=None):
            webbrowser.open("https://v.douyin.com/01DEXWMY_nU/ 2@2.com")
            
        def open_QQgroup(event=None):
            webbrowser.open("https://qun.qq.com/universal-share/share?ac=1&authKey=xj8N4Mi2kwX09D28RcK5O6YxZGxKKsmh%2B2VfaEjhQ8Vfb%2B2uZY8BhFVr8uGx%2FpV8&busi_data=eyJncm91cENvZGUiOiI4NjI4ODIwNzIiLCJ0b2tlbiI6InZ1c0xndDlQMTN2OWdNYkwwdktuVjk5V250cW1EdVlTYmo3cWxMNWNLc0krWWpEN1RSd1R4dGc3NnYxTVNxbHoiLCJ1aW4iOiIxNTQxNTk5NzQ1In0%3D&data=tminb8kZoG8JR_1CBx5j2cON35eXHis6xI-vy-fu2ah1ty_c8dJ3_atbbNyEmgdkoRk0msKfYwwihh6Cr3-KVg&svctype=4&tempid=h5_group_info")

        def open_buymeacoffee(event=None):
            webbrowser.open("https://www.buymeacoffee.com/t2chips")
            
        def open_aifadian(event=None):
            webbrowser.open("https://afdian.com/a/T2Chips")

        def open_releases(event=None):
            webbrowser.open(self.version_checker.get_releases_url())

        # Version text with update notification frame
        version_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
        version_frame.pack(side="left", padx=(10, 6))

        credit_text = ctk.CTkLabel(
            version_frame,
            text=f"v{VERSION} · Created by T2薯条（Smiorld） | ",
            font=("Arial", 15),
            text_color="gray60"
        )
        credit_text.pack(side="left")

        # Red update notification link (hidden initially)
        self.update_notification_label = ctk.CTkLabel(
            version_frame,
            text="",  # Will be set dynamically
            font=("Arial", 15, "bold", "underline"),
            text_color="#FF4444",  # Red color
            cursor="hand2"
        )
        self.update_notification_label.pack(side="left", padx=(5, 0))
        self.update_notification_label.pack_forget()  # Hide initially
        self.update_notification_label.bind("<Button-1>", open_releases)

        credit_link = ctk.CTkLabel(
            toolbar_frame,
            text="GitHub",
            font=("Arial", 15, "underline"),
            text_color="#1D7FAF",
            cursor="hand2"
        )
        credit_link.pack(side="left", padx=(0, 6))
        credit_link.bind("<Button-1>", open_github)
        
        credit_link1 = ctk.CTkLabel(
            toolbar_frame,
            text="Bilibili",
            font=("Arial", 15, "underline"),
            text_color="#1D7FAF",
            cursor="hand2"
        )
        credit_link1.pack(side="left", padx=(0, 6))
        credit_link1.bind("<Button-1>", open_bilibili)
        
        credit_link2 = ctk.CTkLabel(
            toolbar_frame,
            text="Douyin",
            font=("Arial", 15, "underline"),
            text_color="#1D7FAF",
            cursor="hand2"
        )
        credit_link2.pack(side="left", padx=(0, 6))
        credit_link2.bind("<Button-1>", open_douyin)
        
        credit_link3 = ctk.CTkLabel(
            toolbar_frame,
            text="QQ群",
            font=("Arial", 15, "underline"),
            text_color="#1D7FAF",
            cursor="hand2"
        )
        credit_link3.pack(side="left", padx=(0, 6))
        credit_link3.bind("<Button-1>", open_QQgroup)
        
        credit_text = ctk.CTkLabel(
            toolbar_frame,
            text="|  Support me at: ",
            font=("Arial", 15),
            text_color="gray60"
        )
        credit_text.pack(side="left", padx=(10, 6))
        
        credit_link4 = ctk.CTkLabel(
            toolbar_frame,
            text="Buy me a coffee",
            font=("Arial", 15, "underline"),
            text_color="#1D7FAF",
            cursor="hand2"
        )
        credit_link4.pack(side="left", padx=(0, 6))
        credit_link4.bind("<Button-1>", open_buymeacoffee)
        
        credit_link5 = ctk.CTkLabel(
            toolbar_frame,
            text="爱发电",
            font=("Arial", 15, "underline"),
            text_color="#1D7FAF",
            cursor="hand2"
        )
        credit_link5.pack(side="left", padx=(0, 6))
        credit_link5.bind("<Button-1>", open_aifadian)

        # Separator
        separator_text = ctk.CTkLabel(
            toolbar_frame,
            text=" | ",
            font=("Arial", 15),
            text_color="gray60"
        )
        separator_text.pack(side="left", padx=(10, 6))

        # Manual version check button
        check_update_btn = ctk.CTkButton(
            toolbar_frame,
            text=t("main_window.version_check.button"),
            width=100,
            height=28,
            font=("Arial", 13),
            command=self._manual_check_for_updates
        )
        check_update_btn.pack(side="left", padx=(0, 10))

        # 语言选择器（分段按钮）
        current_lang = self.global_config.get_language()

        self.language_selector = ctk.CTkSegmentedButton(
            toolbar_frame,
            values=["中文", "English"],
            command=self._on_language_change
        )
        self.language_selector.pack(side="right", padx=10, pady=10)

        # 设置当前选中的语言
        if current_lang == "zh_CN":
            self.language_selector.set("中文")
        else:
            self.language_selector.set("English")

    def _on_language_change(self, selected_lang: str):
        """语言切换回调"""
        # 转换显示名称到语言代码
        lang_map = {
            "中文": "zh_CN",
            "English": "en_US"
        }
        new_lang = lang_map.get(selected_lang)

        if not new_lang:
            return

        current_lang = self.global_config.get_language()
        if new_lang == current_lang:
            return  # 未改变

        # 保存新语言设置
        self.global_config.set_language(new_lang, save=True)

        # 提示用户需要手动重启
        messagebox.showinfo(
            t("main_window.restart_title"),
            t("main_window.restart_prompt")
        )

        # 恢复原选择显示（因为当前会话不会改变）
        if current_lang == "zh_CN":
            self.language_selector.set("中文")
        else:
            self.language_selector.set("English")

    # def _create_credit_row(self):
    #     credit_frame = ctk.CTkFrame(self, height=30, fg_color="transparent")
    #     credit_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
    #     credit_frame.grid_propagate(False)

    #     def open_github(event=None):
    #         webbrowser.open("https://github.com/Smiorld")
            
    #     def open_bilibili(event=None):
    #         webbrowser.open("https://space.bilibili.com/2148654")
            
    #     def open_douyin(event=None):
    #         webbrowser.open("https://v.douyin.com/01DEXWMY_nU/ 2@2.com")

    #     credit_text = ctk.CTkLabel(
    #         credit_frame,
    #         text="v1.0.0 · Created by T2薯条（Smiorld） | ",
    #         font=("Arial", 10),
    #         text_color="gray60"
    #     )
    #     credit_text.pack(side="left", padx=(10, 6))

    #     credit_link = ctk.CTkLabel(
    #         credit_frame,
    #         text="GitHub",
    #         font=("Arial", 10, "underline"),
    #         text_color="#1D7FAF",
    #         cursor="hand2"
    #     )
    #     credit_link.pack(side="left", padx=(0, 6))
    #     credit_link.bind("<Button-1>", open_github)
        
    #     credit_link1 = ctk.CTkLabel(
    #         credit_frame,
    #         text="Bilibili",
    #         font=("Arial", 10, "underline"),
    #         text_color="#1D7FAF",
    #         cursor="hand2"
    #     )
    #     credit_link1.pack(side="left", padx=(0, 6))
    #     credit_link1.bind("<Button-1>", open_bilibili)
        
    #     credit_link2 = ctk.CTkLabel(
    #         credit_frame,
    #         text="Douyin",
    #         font=("Arial", 10, "underline"),
    #         text_color="#1D7FAF",
    #         cursor="hand2"
    #     )
    #     credit_link2.pack(side="left", padx=(0, 6))
    #     credit_link2.bind("<Button-1>", open_douyin)

    # ========== Version Check Methods ==========

    def _start_auto_version_check(self):
        """Start automatic version check on startup with rate limiting"""
        if self.version_checker.should_check():
            print("[MainWindow] Starting auto version check")
            self._check_version_async(is_auto_check=True)
        else:
            # Use cached version if available
            cached_version = self.version_checker._get_cached_latest_version()
            if cached_version:
                print(f"[MainWindow] Using cached version: {cached_version}")
                self._handle_version_check_result(True, cached_version, None, is_auto_check=True)

    def _check_version_async(self, is_auto_check: bool = False):
        """Check for version asynchronously"""
        def callback(success: bool, latest_version: Optional[str], error_msg: Optional[str]):
            # Use .after() to safely update UI from background thread
            self.after(0, lambda: self._handle_version_check_result(
                success, latest_version, error_msg, is_auto_check
            ))

        self.version_checker.check_for_updates_async(
            callback=callback,
            force=not is_auto_check  # Force check for manual requests
        )

    def _handle_version_check_result(self,
                                     success: bool,
                                     latest_version: Optional[str],
                                     error_msg: Optional[str],
                                     is_auto_check: bool):
        """Handle version check result and update UI"""
        if not success:
            # Only show error dialog for manual checks
            if not is_auto_check:
                messagebox.showerror(
                    t("main_window.version_check.error_title"),
                    t("main_window.version_check.error", error=error_msg)
                )
            return

        self.latest_version = latest_version
        self.update_available = self.version_checker.has_update_available(latest_version)

        if self.update_available:
            print(f"[MainWindow] Update available: v{latest_version}")
            # Show red update notification link
            self.update_notification_label.configure(
                text=t("main_window.version_check.update_link", version=f"v{latest_version}")
            )
            self.update_notification_label.pack(side="left", padx=(5, 0))

            # For manual checks, also show a dialog
            if not is_auto_check:
                messagebox.showinfo(
                    t("main_window.version_check.available_title"),
                    t("main_window.version_check.available", version=f"v{latest_version}")
                )
        else:
            print("[MainWindow] Already on latest version")
            # Hide update notification
            self.update_notification_label.pack_forget()

            # For manual checks, inform user they're up to date
            if not is_auto_check:
                messagebox.showinfo(
                    t("main_window.version_check.latest_title"),
                    t("main_window.version_check.latest")
                )

    def _manual_check_for_updates(self):
        """Manually check for updates (triggered by button)"""
        print("[MainWindow] Manual version check requested")
        self._check_version_async(is_auto_check=False)

    def on_closing(self):
        """Clean up resources before closing"""
        # Clean up each tab
        self.screen_filter_tab.cleanup()
        self.local_map_tab.cleanup()
        self.global_settings_tab.cleanup()

        self.destroy()
