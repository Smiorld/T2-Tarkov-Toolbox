import customtkinter as ctk
from modules.screen_filter.ui import ScreenFilterUI
from modules.local_map.ui import LocalMapUI
from modules.quest_tracker.ui import QuestTrackerUI


class MainWindow(ctk.CTk):
    """Main application window with tab-based navigation"""

    def __init__(self):
        super().__init__()

        self.title("T2 Tarkov Toolbox")
        self.geometry("1200x800")

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Add tabs
        self.tabview.add("屏幕滤镜")
        self.tabview.add("本地地图")
        self.tabview.add("任务追踪")

        # Initialize tab content
        self.screen_filter_tab = ScreenFilterUI(self.tabview.tab("屏幕滤镜"))
        self.screen_filter_tab.pack(fill="both", expand=True)

        self.local_map_tab = LocalMapUI(self.tabview.tab("本地地图"))
        self.local_map_tab.pack(fill="both", expand=True)

        self.quest_tracker_tab = QuestTrackerUI(self.tabview.tab("任务追踪"))
        self.quest_tracker_tab.pack(fill="both", expand=True)

        # Set default tab
        self.tabview.set("屏幕滤镜")

    def on_closing(self):
        """Clean up resources before closing"""
        # Clean up each tab
        self.screen_filter_tab.cleanup()
        self.local_map_tab.cleanup()
        self.quest_tracker_tab.cleanup()

        self.destroy()
