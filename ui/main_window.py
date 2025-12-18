import customtkinter as ctk
import webbrowser
from tkinter import messagebox
from modules.screen_filter.ui import ScreenFilterUI
from modules.local_map.ui import LocalMapUI
from modules.global_settings.ui import GlobalSettingsUI
from utils.global_config import get_global_config
from utils.i18n import t

VERSION = "1.0.1"

class MainWindow(ctk.CTk):
    """Main application window with tab-based navigation"""

    def __init__(self):
        super().__init__()

        self.title(t("main_window.title"))
        self.geometry("1200x800")

        # Get global config
        self.global_config = get_global_config()

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

        credit_text = ctk.CTkLabel(
            toolbar_frame,
            text=f"v{VERSION} · Created by T2薯条（Smiorld） | ",
            font=("Arial", 15),
            text_color="gray60"
        )
        credit_text.pack(side="left", padx=(10, 6))

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
        
        

    def on_closing(self):
        """Clean up resources before closing"""
        # Clean up each tab
        self.screen_filter_tab.cleanup()
        self.local_map_tab.cleanup()
        self.global_settings_tab.cleanup()

        self.destroy()
