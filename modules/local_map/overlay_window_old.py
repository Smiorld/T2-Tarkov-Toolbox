"""
Local Map Module - Overlay Window

悬浮小地图窗口
"""

import customtkinter as ctk
from tkinter import Canvas
from PIL import Image, ImageTk
import math
from typing import Optional, Tuple, Callable


class OverlayMapWindow(ctk.CTkToplevel):
    """悬浮小地图窗口"""

    def __init__(self, parent):
        super().__init__(parent)

        # 窗口状态
        self.is_locked = False
        self.player_centered = True
        self.current_map_image: Optional[Image.Image] = None
        self.current_photo: Optional[ImageTk.PhotoImage] = None

        # 玩家位置
        self.player_x: Optional[float] = None
        self.player_y: Optional[float] = None
        self.player_yaw: Optional[float] = None

        # 视图参数
        self.zoom_level = 1.0
        self.view_offset_x = 0.0  # 非居中模式的偏移
        self.view_offset_y = 0.0

        # 窗口参数（记忆用户设置）
        self.window_width = 400
        self.window_height = 400
        self.window_x = 100
        self.window_y = 100
        self.opacity = 0.85

        # 拖拽状态
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._dragging = False

        # 调整大小状态
        self._resize_edge = None  # 'n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_width = 0
        self._resize_start_height = 0
        self._resize_start_pos_x = 0
        self._resize_start_pos_y = 0

        self._setup_window()
        self._setup_ui()
        self._bind_events()

    def _setup_window(self):
        """设置窗口属性"""
        self.title("小地图")

        # 设置窗口大小和位置
        self.geometry(f"{self.window_width}x{self.window_height}+{self.window_x}+{self.window_y}")

        # 无边框
        self.overrideredirect(True)

        # 置顶
        self.attributes("-topmost", True)

        # 透明度
        self.attributes("-alpha", self.opacity)

        # 工具窗口（在任务栏不显示）
        self.attributes("-toolwindow", True)

    def _setup_ui(self):
        """设置UI"""
        # 主容器（带边框用于调整大小）
        self.container = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0, border_width=2, border_color="#444444")
        self.container.pack(fill="both", expand=True)

        # Canvas用于显示地图
        self.canvas = Canvas(
            self.container,
            bg="#000000",
            highlightthickness=0,
            cursor="hand2"
        )
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)

        # 移除控制栏 - 所有控制通过主UI完成

    def _bind_events(self):
        """绑定事件"""
        # 右键拖拽窗口和调整大小（仅解锁状态）
        self.bind("<Button-3>", self._on_window_click)
        self.bind("<B3-Motion>", self._on_window_drag)
        self.bind("<ButtonRelease-3>", self._on_window_release)
        self.bind("<Motion>", self._on_window_motion)

        # Canvas事件 - 左键拖拽地图内容
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # 窗口大小调整
        self.bind("<Configure>", self._on_window_resize)

    def _get_resize_edge(self, x, y):
        """判断鼠标在哪个边缘（用于调整大小）"""
        if self.is_locked:
            return None

        edge_size = 8  # 边缘检测区域大小
        width = self.winfo_width()
        height = self.winfo_height()

        on_left = x < edge_size
        on_right = x > width - edge_size
        on_top = y < edge_size
        on_bottom = y > height - edge_size

        if on_top and on_left:
            return 'nw'
        elif on_top and on_right:
            return 'ne'
        elif on_bottom and on_left:
            return 'sw'
        elif on_bottom and on_right:
            return 'se'
        elif on_top:
            return 'n'
        elif on_bottom:
            return 's'
        elif on_left:
            return 'w'
        elif on_right:
            return 'e'
        else:
            return None

    def _get_cursor_for_edge(self, edge):
        """根据边缘返回光标样式"""
        cursors = {
            'n': 'sb_v_double_arrow',
            's': 'sb_v_double_arrow',
            'e': 'sb_h_double_arrow',
            'w': 'sb_h_double_arrow',
            'ne': 'size_ne_sw',
            'nw': 'size_nw_se',
            'se': 'size_nw_se',
            'sw': 'size_ne_sw'
        }
        return cursors.get(edge, 'arrow')

    def _on_window_motion(self, event):
        """鼠标移动（更新光标）"""
        if self.is_locked:
            return

        edge = self._get_resize_edge(event.x, event.y)
        if edge:
            self.configure(cursor=self._get_cursor_for_edge(edge))
        else:
            self.configure(cursor="arrow")

    def _on_window_click(self, event):
        """窗口点击事件"""
        if self.is_locked:
            return

        self._resize_edge = self._get_resize_edge(event.x, event.y)

        if self._resize_edge:
            # 开始调整大小
            self._resize_start_x = event.x_root
            self._resize_start_y = event.y_root
            self._resize_start_width = self.winfo_width()
            self._resize_start_height = self.winfo_height()
            self._resize_start_pos_x = self.winfo_x()
            self._resize_start_pos_y = self.winfo_y()
        else:
            # 开始拖拽窗口
            self._drag_start_x = event.x
            self._drag_start_y = event.y
            self._dragging = True

    def _on_window_drag(self, event):
        """窗口拖拽事件"""
        if self.is_locked:
            return

        if self._resize_edge:
            # 调整大小
            dx = event.x_root - self._resize_start_x
            dy = event.y_root - self._resize_start_y

            new_width = self._resize_start_width
            new_height = self._resize_start_height
            new_x = self._resize_start_pos_x
            new_y = self._resize_start_pos_y

            if 'e' in self._resize_edge:
                new_width = max(200, self._resize_start_width + dx)
            if 'w' in self._resize_edge:
                new_width = max(200, self._resize_start_width - dx)
                new_x = self._resize_start_pos_x + dx
                if new_width == 200:
                    new_x = self._resize_start_pos_x + self._resize_start_width - 200

            if 's' in self._resize_edge:
                new_height = max(200, self._resize_start_height + dy)
            if 'n' in self._resize_edge:
                new_height = max(200, self._resize_start_height - dy)
                new_y = self._resize_start_pos_y + dy
                if new_height == 200:
                    new_y = self._resize_start_pos_y + self._resize_start_height - 200

            self.geometry(f"{int(new_width)}x{int(new_height)}+{int(new_x)}+{int(new_y)}")

        elif self._dragging:
            # 拖拽窗口
            x = self.winfo_x() + event.x - self._drag_start_x
            y = self.winfo_y() + event.y - self._drag_start_y
            self.geometry(f"+{x}+{y}")

    def _on_window_release(self, event):
        """窗口释放事件"""
        if self._resize_edge or self._dragging:
            # 保存最终位置和大小
            self.window_width = self.winfo_width()
            self.window_height = self.winfo_height()
            self.window_x = self.winfo_x()
            self.window_y = self.winfo_y()

        self._resize_edge = None
        self._dragging = False

    def _on_mouse_wheel(self, event):
        """鼠标滚轮缩放"""
        if not self.is_locked:
            # 缩放
            if event.delta > 0:
                self.zoom_level *= 1.1
            else:
                self.zoom_level /= 1.1

            # 限制缩放范围
            self.zoom_level = max(0.1, min(5.0, self.zoom_level))

            self._redraw_map()

    def _on_canvas_click(self, event):
        """Canvas点击事件 - 左键拖拽地图内容"""
        if not self.is_locked:
            self._drag_start_x = event.x
            self._drag_start_y = event.y

    def _on_canvas_drag(self, event):
        """Canvas拖拽（平移地图）- 左键拖拽"""
        if not self.is_locked:
            dx = event.x - self._drag_start_x
            dy = event.y - self._drag_start_y

            self.view_offset_x += dx
            self.view_offset_y += dy

            self._drag_start_x = event.x
            self._drag_start_y = event.y

            # 拖拽地图时自动退出玩家居中模式
            if self.player_centered:
                self.player_centered = False

            self._redraw_map()

    def _on_canvas_release(self, event):
        """Canvas释放"""
        pass

    def _on_window_resize(self, event):
        """窗口大小改变"""
        if event.widget == self:
            self.window_width = event.width
            self.window_height = event.height
            self._redraw_map()

    def set_lock_state(self, is_locked: bool):
        """设置锁定/解锁状态（从主UI控制）"""
        if self.is_locked == is_locked:
            return

        self.is_locked = is_locked

        if self.is_locked:
            # 锁定：启用鼠标穿透
            self.canvas.configure(cursor="")

            # 启用鼠标穿透（Windows）
            try:
                import win32gui
                import win32con
                hwnd = int(self.wm_frame(), 16)
                extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(
                    hwnd,
                    win32con.GWL_EXSTYLE,
                    extended_style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
                )
            except:
                pass
        else:
            # 解锁：禁用鼠标穿透
            self.canvas.configure(cursor="hand2")

            # 禁用鼠标穿透
            try:
                import win32gui
                import win32con
                hwnd = int(self.wm_frame(), 16)
                extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(
                    hwnd,
                    win32con.GWL_EXSTYLE,
                    extended_style & ~win32con.WS_EX_TRANSPARENT
                )
            except:
                pass

    def set_player_centered(self, centered: bool):
        """设置玩家居中模式（从主UI控制）"""
        self.player_centered = centered

        if self.player_centered:
            self.view_offset_x = 0
            self.view_offset_y = 0

        self._redraw_map()

    def set_opacity(self, opacity: float):
        """设置透明度"""
        self.opacity = max(0.1, min(1.0, opacity))
        self.attributes("-alpha", self.opacity)

    def load_map(self, image_path: str) -> bool:
        """加载地图图片"""
        try:
            self.current_map_image = Image.open(image_path)
            self._redraw_map()
            return True
        except Exception as e:
            print(f"加载地图失败: {e}")
            return False

    def update_player_position(self, map_x: float, map_y: float, yaw: Optional[float] = None):
        """更新玩家位置"""
        self.player_x = map_x
        self.player_y = map_y
        self.player_yaw = yaw
        self._redraw_map()

    def _redraw_map(self):
        """重绘地图 - 使用与主Canvas相同的坐标系统"""
        if not self.current_map_image:
            return

        # 清空Canvas
        self.canvas.delete("all")

        canvas_width = self.canvas.winfo_width() or self.window_width
        canvas_height = self.canvas.winfo_height() or self.window_height

        if canvas_width <= 1 or canvas_height <= 1:
            return

        img_width, img_height = self.current_map_image.size

        # 计算offset（与主Canvas完全一致的逻辑）
        # 关键：center_map始终是地图图片中心，通过调整offset来实现不同视图
        if self.player_centered and self.player_x is not None and self.player_y is not None:
            # 玩家居中模式：调整offset使玩家显示在Canvas中心
            # 计算玩家相对于地图中心的偏移
            player_dx = (self.player_x - img_width / 2) * self.zoom_level
            player_dy = (self.player_y - img_height / 2) * self.zoom_level
            # 反向偏移offset，使玩家显示在Canvas中心
            offset_x = canvas_width / 2 - player_dx
            offset_y = canvas_height / 2 - player_dy
        else:
            # 自由视图模式：固定offset + 用户拖拽偏移
            offset_x = canvas_width / 2 + self.view_offset_x
            offset_y = canvas_height / 2 + self.view_offset_y

        # 使用与主Canvas完全相同的坐标转换逻辑
        def map_to_canvas(map_x, map_y):
            """地图坐标 -> Canvas坐标（与主Canvas的_map_to_canvas_coords完全一致）"""
            # 计算相对于地图中心的偏移（始终使用地图图片中心）
            dx = (map_x - img_width / 2) * self.zoom_level
            dy = (map_y - img_height / 2) * self.zoom_level

            # 转换为Canvas坐标
            canvas_x = offset_x + dx
            canvas_y = offset_y + dy

            return canvas_x, canvas_y

        # 绘制地图图片
        # 缩放地图图片
        scaled_width = int(img_width * self.zoom_level)
        scaled_height = int(img_height * self.zoom_level)

        if scaled_width > 0 and scaled_height > 0:
            scaled_image = self.current_map_image.resize(
                (scaled_width, scaled_height),
                Image.Resampling.LANCZOS
            )

            self.current_photo = ImageTk.PhotoImage(scaled_image)

            # 使用center锚点绘制地图（与主Canvas完全一致）
            # offset_x, offset_y 就是地图图片中心在Canvas上的位置
            self.canvas.create_image(
                offset_x, offset_y,
                image=self.current_photo,
                anchor="center"
            )

        # 绘制玩家位置
        if self.player_x is not None and self.player_y is not None:
            # 使用相同的坐标转换
            px, py = map_to_canvas(self.player_x, self.player_y)

            # 绘制玩家标记（与主Canvas风格一致）
            radius = 8

            # 外圈（黑色）
            self.canvas.create_oval(
                px - radius - 1, py - radius - 1,
                px + radius + 1, py + radius + 1,
                fill="#000000", outline=""
            )

            # 内圈（绿色）
            self.canvas.create_oval(
                px - radius, py - radius,
                px + radius, py + radius,
                fill="#00ff00", outline="#ffffff", width=2
            )

            # 绘制朝向箭头
            if self.player_yaw is not None:
                arrow_length = 15
                yaw_rad = math.radians(self.player_yaw)

                # 箭头终点
                end_x = px + arrow_length * math.sin(yaw_rad)
                end_y = py - arrow_length * math.cos(yaw_rad)

                # 绘制箭头
                self.canvas.create_line(
                    px, py, end_x, end_y,
                    fill="#00ff00", width=3,
                    arrow="last", arrowshape=(10, 12, 5)
                )

    def show_window(self):
        """显示窗口"""
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide_window(self):
        """隐藏窗口"""
        self.withdraw()

    def get_state(self) -> dict:
        """获取窗口状态（用于保存配置）"""
        return {
            "width": self.window_width,
            "height": self.window_height,
            "x": self.window_x,
            "y": self.window_y,
            "opacity": self.opacity,
            "zoom_level": self.zoom_level,
            "player_centered": self.player_centered,
            "is_locked": self.is_locked
        }

    def load_state(self, state: dict):
        """加载窗口状态"""
        self.window_width = state.get("width", 400)
        self.window_height = state.get("height", 400)
        self.window_x = state.get("x", 100)
        self.window_y = state.get("y", 100)
        self.opacity = state.get("opacity", 0.85)
        self.zoom_level = state.get("zoom_level", 1.0)
        self.player_centered = state.get("player_centered", True)

        # 应用设置
        self.geometry(f"{self.window_width}x{self.window_height}+{self.window_x}+{self.window_y}")
        self.set_opacity(self.opacity)

        # 加载锁定状态
        is_locked = state.get("is_locked", False)
        if is_locked != self.is_locked:
            self.set_lock_state(is_locked)
