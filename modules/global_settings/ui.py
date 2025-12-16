"""
Global Settings Module - UI
全局设置UI
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import winreg
from utils.i18n import t


class GlobalSettingsUI(ctk.CTkFrame):
    """全局设置UI"""

    def __init__(self, parent):
        super().__init__(parent)

        # 获取全局配置实例
        from utils.global_config import get_global_config
        self.global_config = get_global_config()

        # 优先从配置文件读取路径
        self.screenshots_path = self.global_config.get_screenshots_path()
        self.logs_path = self.global_config.get_logs_path()

        # 如果配置为空,进行自动检测
        if not self.screenshots_path:
            self.screenshots_path = self._detect_screenshots_path()
            self.global_config.set_screenshots_path(self.screenshots_path)

        if not self.logs_path:
            self.logs_path = self._detect_logs_path()
            self.global_config.set_logs_path(self.logs_path)

        self._setup_ui()

    def _detect_screenshots_path(self) -> str:
        """
        自动检测截图路径（支持中文Windows和非标准路径）

        检测策略：
        1. Windows Shell API - 获取用户Documents文件夹（支持中文）
        2. 遍历常见驱动器 - 查找 Escape from Tarkov\Screenshots
        3. 硬编码路径 - 兼容旧逻辑
        """
        import ctypes.wintypes
        from ctypes import windll, create_unicode_buffer

        # 策略1: 使用Windows Shell API获取Documents文件夹（截图默认在文档目录）
        try:
            # CSIDL_PERSONAL = 0x0005 (My Documents)
            CSIDL_PERSONAL = 0x05
            SHGFP_TYPE_CURRENT = 0

            buf = create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)

            documents_folder = buf.value
            tarkov_screenshots = os.path.join(documents_folder, "Escape from Tarkov", "Screenshots")

            if os.path.exists(tarkov_screenshots):
                print(f"[全局设置] 检测到截图路径（Shell API - Documents）: {tarkov_screenshots}")
                return tarkov_screenshots
        except Exception as e:
            print(f"[全局设置] Shell API检测失败: {e}")

        # 策略2: 遍历常见驱动器查找 Escape from Tarkov\Screenshots
        try:
            common_drives = ['C:', 'D:', 'E:']
            common_subdirs = [
                'tool/document',  # 用户的自定义路径
                'Users/{username}/Documents',  # 标准Windows文档路径
                'Users/Public/Documents'  # 公共文档路径
            ]

            username = os.environ.get('USERNAME', '')

            for drive in common_drives:
                for subdir in common_subdirs:
                    # 替换用户名占位符
                    subdir = subdir.replace('{username}', username)

                    # 构建可能的路径
                    possible_path = os.path.join(drive, subdir, 'Escape from Tarkov', 'Screenshots')

                    if os.path.exists(possible_path):
                        print(f"[全局设置] 检测到截图路径（驱动器遍历）: {possible_path}")
                        return possible_path
        except Exception as e:
            print(f"[全局设置] 驱动器遍历检测失败: {e}")

        # 策略3: 硬编码路径（向后兼容）
        possible_paths = [
            os.path.expanduser("~/Pictures/Escape from Tarkov"),
            "C:/Users/Public/Pictures/Escape from Tarkov",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                print(f"[全局设置] 检测到截图路径（硬编码）: {path}")
                return path

        print("[全局设置] 未能自动检测截图路径，请手动选择")
        return ""

    def _detect_logs_path(self) -> str:
        """自动检测日志路径"""
        try:
            # 尝试从注册表读取
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
        """设置UI"""
        # 配置网格
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # === 标题区域 ===
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text=t("global_settings.title"),
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text=t("global_settings.subtitle"),
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        subtitle_label.pack(anchor="w", pady=(5, 0))

        # === 设置内容区域（可滚动） ===
        self.settings_scroll = ctk.CTkScrollableFrame(self)
        self.settings_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        self.settings_scroll.grid_columnconfigure(0, weight=1)

        # === 路径设置 ===
        self._create_path_settings_section()

    def _create_path_settings_section(self):
        """创建路径设置区域"""
        # 区域标题
        path_title_frame = ctk.CTkFrame(self.settings_scroll, fg_color="#2a2d2e", corner_radius=8)
        path_title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        path_title_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            path_title_frame,
            text=f"📁 {t('global_settings.sections.paths')}",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=15, pady=10)

        # 内容框架
        content_frame = ctk.CTkFrame(self.settings_scroll, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="ew", padx=10)
        content_frame.grid_columnconfigure(1, weight=1)

        # 截图路径
        row = 0
        ctk.CTkLabel(
            content_frame,
            text=t("global_settings.paths.screenshots"),
            font=ctk.CTkFont(size=13)
        ).grid(row=row, column=0, sticky="w", padx=10, pady=10)

        self.screenshots_path_entry = ctk.CTkEntry(
            content_frame,
            placeholder_text=t("global_settings.paths.placeholder_screenshots"),
            height=35
        )
        self.screenshots_path_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=10)
        self.screenshots_path_entry.insert(0, self.screenshots_path)

        screenshots_browse_btn = ctk.CTkButton(
            content_frame,
            text=t("global_settings.paths.browse"),
            command=lambda: self._browse_folder(self.screenshots_path_entry),
            width=80,
            height=35
        )
        screenshots_browse_btn.grid(row=row, column=2, padx=10, pady=10)

        # 日志路径
        row += 1
        ctk.CTkLabel(
            content_frame,
            text=t("global_settings.paths.logs"),
            font=ctk.CTkFont(size=13)
        ).grid(row=row, column=0, sticky="w", padx=10, pady=10)

        self.logs_path_entry = ctk.CTkEntry(
            content_frame,
            placeholder_text=t("global_settings.paths.placeholder_logs"),
            height=35
        )
        self.logs_path_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=10)
        self.logs_path_entry.insert(0, self.logs_path)

        logs_browse_btn = ctk.CTkButton(
            content_frame,
            text=t("global_settings.paths.browse"),
            command=lambda: self._browse_folder(self.logs_path_entry),
            width=80,
            height=35
        )
        logs_browse_btn.grid(row=row, column=2, padx=10, pady=10)

        # 说明文本
        row += 1
        info_text = ctk.CTkTextbox(
            content_frame,
            height=80,
            fg_color="#2a2d2e",
            wrap="word"
        )
        info_text.grid(row=row, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 20))
        info_text.insert("1.0", t("global_settings.paths.help_text"))
        info_text.configure(state="disabled")

        # 新增: 重新检测路径按钮
        row += 1
        redetect_btn = ctk.CTkButton(
            content_frame,
            text=f"🔍 {t('global_settings.paths.auto_detect')}",
            command=self._redetect_paths,
            height=40,
            fg_color="#2d4a5a",
            hover_color="#4a7a8d",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        redetect_btn.grid(row=row, column=0, columnspan=3, pady=10)

        # 保存按钮
        row += 1
        save_btn = ctk.CTkButton(
            content_frame,
            text=t("global_settings.buttons.save"),
            command=self._save_settings,
            height=40,
            fg_color="#2d5a2d",
            hover_color="#4a9d4a",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        save_btn.grid(row=row, column=0, columnspan=3, pady=20)

    def _browse_folder(self, entry_widget):
        """浏览文件夹"""
        folder = filedialog.askdirectory(
            title="选择文件夹",
            initialdir=entry_widget.get() or os.path.expanduser("~")
        )

        if folder:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, folder)

    def _redetect_paths(self):
        """重新检测截图和日志路径"""
        # 检测截图路径
        new_screenshots_path = self._detect_screenshots_path()
        # 检测日志路径
        new_logs_path = self._detect_logs_path()

        if new_screenshots_path or new_logs_path:
            if new_screenshots_path:
                self.screenshots_path_entry.delete(0, "end")
                self.screenshots_path_entry.insert(0, new_screenshots_path)
            if new_logs_path:
                self.logs_path_entry.delete(0, "end")
                self.logs_path_entry.insert(0, new_logs_path)

            messagebox.showinfo(
                t("common.success"),
                t("global_settings.messages.auto_detect_success",
                  screenshots=new_screenshots_path or t("common.info"),
                  logs=new_logs_path or t("common.info"))
            )
        else:
            messagebox.showwarning(
                t("common.warning"),
                t("global_settings.messages.auto_detect_failed")
            )

    def _save_settings(self):
        """保存设置"""
        new_screenshots_path = self.screenshots_path_entry.get()
        new_logs_path = self.logs_path_entry.get()

        # 更新全局配置 (会自动保存到文件并通知监听者)
        self.global_config.set_screenshots_path(new_screenshots_path)
        self.global_config.set_logs_path(new_logs_path)

        # 更新本地缓存
        self.screenshots_path = new_screenshots_path
        self.logs_path = new_logs_path

        print(f"[全局设置] 保存路径配置:")
        print(f"  截图路径: {self.screenshots_path}")
        print(f"  日志路径: {self.logs_path}")

        messagebox.showinfo(t("common.success"), t("global_settings.messages.save_success"))

    def get_screenshots_path(self) -> str:
        """获取截图路径"""
        return self.screenshots_path

    def get_logs_path(self) -> str:
        """获取日志路径"""
        return self.logs_path

    def cleanup(self):
        """清理资源"""
        pass
