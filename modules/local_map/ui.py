import customtkinter as ctk


class LocalMapUI(ctk.CTkFrame):
    """Local Map Tab UI Component - To be implemented"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        # Placeholder content
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        placeholder = ctk.CTkFrame(self)
        placeholder.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        title = ctk.CTkLabel(
            placeholder,
            text="本地地图",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=50)

        description = ctk.CTkLabel(
            placeholder,
            text="此模块将实现：\n\n"
                 "• 监控游戏截图文件夹\n"
                 "• 读取截图EXIF数据获取地图和位置信息\n"
                 "• 在预设地图上显示玩家位置标记\n"
                 "• 显示出生点、提取点、任务点、战利品点\n\n"
                 "参考项目：TarkovMonitor",
            font=ctk.CTkFont(size=14),
            justify="left"
        )
        description.pack(pady=20)

    def cleanup(self):
        """Clean up resources when tab is closed"""
        pass
