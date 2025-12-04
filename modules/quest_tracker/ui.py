import customtkinter as ctk


class QuestTrackerUI(ctk.CTkFrame):
    """Quest Tracker Tab UI Component - To be implemented"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        # Placeholder content
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        placeholder = ctk.CTkFrame(self)
        placeholder.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        title = ctk.CTkLabel(
            placeholder,
            text="任务追踪",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=50)

        description = ctk.CTkLabel(
            placeholder,
            text="此模块将实现：\n\n"
                 "• 从 tarkov.dev API 获取任务综合数据\n"
                 "• 显示所有任务列表（按商人分组）\n"
                 "• 标记任务完成状态\n"
                 "• 用 tarkovtracker.org API 云端同步管理任务进度\n"
                 "• 支持纯本地追踪任务进度功能",
            font=ctk.CTkFont(size=14),
            justify="left"
        )
        description.pack(pady=20)

    def cleanup(self):
        """Clean up resources when tab is closed"""
        pass
