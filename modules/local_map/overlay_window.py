"""
Local Map Module - Overlay Window V2

悬浮小地图窗口 - 使用MapCanvas实现
"""

import customtkinter as ctk
from typing import Optional
from .map_canvas import MapCanvas


class OverlayMapWindow(ctk.CTkToplevel):
    """悬浮小地图窗口 - 使用MapCanvas"""

    def __init__(self, parent):
        super().__init__(parent)

        # 窗口状态
        self.is_locked = False
        self.player_centered = True

        # 窗口参数（记忆用户设置）
        self.window_width = 400
        self.window_height = 400
        self.window_x = 100
        self.window_y = 100
        self.opacity = 0.85

        # 状态变化回调
        self.on_state_changed = None

        # 拖拽状态
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._dragging = False
        self._drag_widget = None  # 记录触发拖拽的widget

        # 调整大小状态
        self._resize_edge = None
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_width = 0
        self._resize_start_height = 0
        self._resize_start_pos_x = 0
        self._resize_start_pos_y = 0

        # 玩家居中相关
        self._player_map_x: Optional[float] = None
        self._player_map_y: Optional[float] = None
        self._player_yaw: Optional[float] = None
        self._auto_follow_timer = None

        # 记住的缩放级别
        self._saved_zoom = 1.0

        self._setup_window()
        self._setup_ui()
        self._bind_events()

    def _setup_window(self):
        """设置窗口属性"""
        self.title("小地图")
        self.geometry(f"{self.window_width}x{self.window_height}+{self.window_x}+{self.window_y}")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", self.opacity)
        self.attributes("-toolwindow", True)

    def _setup_ui(self):
        """设置UI"""
        # 主容器
        self.container = ctk.CTkFrame(
            self,
            fg_color="#1a1a1a",
            corner_radius=0,
            border_width=2,
            border_color="#444444"
        )
        self.container.pack(fill="both", expand=True)

        # 使用MapCanvas（复用主UI的地图渲染逻辑）
        self.map_canvas = MapCanvas(
            self.container,
            width=self.window_width - 4,
            height=self.window_height - 4
        )
        self.map_canvas.pack(fill="both", expand=True, padx=2, pady=2)

        # 禁用MapCanvas的点击回调（悬浮窗不需要）
        self.map_canvas.set_click_callback(None)

    def _bind_events(self):
        """绑定事件"""
        # 对于窗口本身和 container，绑定左键用于边缘调整大小，右键用于拖动窗口
        for widget in [self, self.container]:
            # 左键：仅用于边缘调整大小
            widget.bind("<Button-1>", self._on_edge_resize_start)
            widget.bind("<B1-Motion>", self._on_edge_resize_drag)
            widget.bind("<ButtonRelease-1>", self._on_edge_resize_end)

            # 右键：用于拖动窗口（非边缘区域）
            widget.bind("<Button-3>", self._on_window_click)
            widget.bind("<B3-Motion>", self._on_window_drag)
            widget.bind("<ButtonRelease-3>", self._on_window_release)

        # map_canvas 不绑定任何窗口操作事件！
        # 保持 MapCanvas 内部的左键拖拽地图功能

        # Motion 事件用于光标变化（所有区域）
        for widget in [self, self.container, self.map_canvas]:
            widget.bind("<Motion>", self._on_window_motion)

            # 滚轮缩放（在整个窗口上都生效）
            widget.bind("<MouseWheel>", self._on_mouse_wheel)
            # Linux系统的滚轮事件
            widget.bind("<Button-4>", self._on_mouse_wheel)
            widget.bind("<Button-5>", self._on_mouse_wheel)

        # Configure事件只需要绑定到窗口本身
        self.bind("<Configure>", self._on_window_resize)

    def _get_resize_edge(self, x, y):
        """判断鼠标在哪个边缘"""
        if self.is_locked:
            return None

        edge_size = 8
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
        """鼠标移动"""
        if self.is_locked:
            return

        # 转换为相对于窗口的坐标
        if event.widget != self:
            x = event.widget.winfo_x() + event.x
            y = event.widget.winfo_y() + event.y
        else:
            x = event.x
            y = event.y

        edge = self._get_resize_edge(x, y)
        if edge:
            self.configure(cursor=self._get_cursor_for_edge(edge))
        else:
            self.configure(cursor="arrow")

    def _on_edge_resize_start(self, event):
        """左键点击，检查是否在边缘（用于调整大小）"""
        if self.is_locked:
            return

        # 转换为相对于窗口的坐标
        if event.widget != self:
            x = event.widget.winfo_x() + event.x
            y = event.widget.winfo_y() + event.y
        else:
            x = event.x
            y = event.y

        # 检查是否在边缘
        edge = self._get_resize_edge(x, y)

        if edge:
            # 在边缘，开始调整大小
            self._resize_edge = edge
            self._resize_start_x = event.x_root
            self._resize_start_y = event.y_root
            self._resize_start_width = self.winfo_width()
            self._resize_start_height = self.winfo_height()
            self._resize_start_pos_x = self.winfo_x()
            self._resize_start_pos_y = self.winfo_y()
        # 不在边缘 → 什么都不做，让 MapCanvas 处理

    def _on_edge_resize_drag(self, event):
        """左键拖拽，仅处理边缘调整大小"""
        if not self._resize_edge:
            return

        # 调整大小逻辑（复用现有代码）
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y

        new_width = self._resize_start_width
        new_height = self._resize_start_height
        new_x = self._resize_start_pos_x
        new_y = self._resize_start_pos_y

        # 计算新尺寸（与现有的 _on_window_drag 逻辑相同）
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

    def _on_edge_resize_end(self, event):
        """左键释放，结束边缘调整大小"""
        if self._resize_edge:
            # 保存最终位置和大小
            self.window_width = self.winfo_width()
            self.window_height = self.winfo_height()
            self.window_x = self.winfo_x()
            self.window_y = self.winfo_y()

        self._resize_edge = None

    def _on_window_click(self, event):
        """窗口点击（右键）"""
        if self.is_locked:
            return

        # 转换为相对于窗口的坐标
        if event.widget != self:
            x = event.widget.winfo_x() + event.x
            y = event.widget.winfo_y() + event.y
        else:
            x = event.x
            y = event.y

        # 右键不处理边缘调整大小，只处理窗口拖动
        edge = self._get_resize_edge(x, y)

        if not edge:
            # 不在边缘，启动窗口拖动
            self._drag_start_x = event.x
            self._drag_start_y = event.y
            self._drag_widget = event.widget
            self._dragging = True

    def _on_window_drag(self, event):
        """窗口拖拽"""
        if self.is_locked:
            return

        # if self._resize_edge:
        #     # 调整大小模式：不实时更新，只记录鼠标位置
        #     # 松开时再应用变化
        #     pass

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
            # 移动窗口模式：实时移动
            new_x = event.x_root - self._drag_start_x
            new_y = event.y_root - self._drag_start_y

            # 如果拖拽从子widget开始，需要调整偏移
            if hasattr(self, '_drag_widget') and self._drag_widget != self:
                widget_offset_x = self._drag_widget.winfo_rootx() - self.winfo_rootx()
                widget_offset_y = self._drag_widget.winfo_rooty() - self.winfo_rooty()
                new_x -= widget_offset_x
                new_y -= widget_offset_y

            self.geometry(f"+{int(new_x)}+{int(new_y)}")

    # def _on_window_release(self, event):
    #     """窗口释放"""
    #     if self._resize_edge:
    #         # 调整大小模式：现在应用大小变化
    #         dx = event.x_root - self._resize_start_x
    #         dy = event.y_root - self._resize_start_y

    #         new_width = self._resize_start_width
    #         new_height = self._resize_start_height
    #         new_x = self._resize_start_pos_x
    #         new_y = self._resize_start_pos_y

    #         # 计算新尺寸
    #         if 'e' in self._resize_edge:
    #             new_width = max(200, self._resize_start_width + dx)
    #         if 'w' in self._resize_edge:
    #             new_width = max(200, self._resize_start_width - dx)
    #             new_x = self._resize_start_pos_x + dx
    #             if new_width == 200:
    #                 new_x = self._resize_start_pos_x + self._resize_start_width - 200

    #         if 's' in self._resize_edge:
    #             new_height = max(200, self._resize_start_height + dy)
    #         if 'n' in self._resize_edge:
    #             new_height = max(200, self._resize_start_height - dy)
    #             new_y = self._resize_start_pos_y + dy
    #             if new_height == 200:
    #                 new_y = self._resize_start_pos_y + self._resize_start_height - 200

    #         # 应用新的几何尺寸
    #         print(f"{int(new_width)}x{int(new_height)}+{int(new_x)}+{int(new_y)}")
    #         self.geometry(f"{int(new_width)}x{int(new_height)}+{int(new_x)}+{int(new_y)}")

    #         # 更新记录的尺寸
    #         self.window_width = int(new_width)
    #         self.window_height = int(new_height)
    #         self.window_x = int(new_x)
    #         self.window_y = int(new_y)

    #         # 通知状态变化
    #         if self.on_state_changed:
    #             self.on_state_changed()

    #     elif self._dragging:
    #         # 移动模式：更新位置
    #         self.window_width = self.winfo_width()
    #         self.window_height = self.winfo_height()
    #         self.window_x = self.winfo_x()
    #         self.window_y = self.winfo_y()

    #         # 通知状态变化
    #         if self.on_state_changed:
    #             self.on_state_changed()

    #     self._resize_edge = None
    #     self._dragging = False
    
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

    def _on_window_resize(self, event):
        """窗口大小改变"""
        if event.widget == self:
            self.window_width = event.width
            self.window_height = event.height

    def _on_mouse_wheel(self, event):
        """滚轮缩放"""
        # 如果窗口被锁定，不处理滚轮事件
        if self.is_locked:
            return

        # 计算缩放因子
        if event.num == 4 or event.delta > 0:  # 向上滚动
            zoom_factor = 1.1
        elif event.num == 5 or event.delta < 0:  # 向下滚动
            zoom_factor = 0.9
        else:
            return

        # 计算新的缩放级别
        new_zoom = self.map_canvas.zoom * zoom_factor
        new_zoom = max(self.map_canvas.min_zoom, min(self.map_canvas.max_zoom, new_zoom))

        # 应用缩放
        self.map_canvas.set_zoom(new_zoom)

        # 保存缩放级别
        self._saved_zoom = new_zoom

        # 不在缩放时重新居中，让用户自由缩放查看
        # 下次位置更新时会自动居中（如果居中模式仍开启）

    def set_lock_state(self, is_locked: bool):
        """设置锁定/解锁状态"""
        if self.is_locked == is_locked:
            return

        self.is_locked = is_locked

        if self.is_locked:
            # 启用鼠标穿透
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
        """设置玩家居中模式"""
        self.player_centered = centered
        if self.player_centered:
            self._start_auto_follow()
        else:
            self._stop_auto_follow()

    def _start_auto_follow(self):
        """开始自动跟随玩家"""
        self._stop_auto_follow()
        self._update_player_centering()

    def _stop_auto_follow(self):
        """停止自动跟随"""
        if self._auto_follow_timer:
            self.after_cancel(self._auto_follow_timer)
            self._auto_follow_timer = None

    def _update_player_centering(self):
        """更新玩家居中（仅在新位置数据到达时调用一次）"""
        if not self.player_centered or self._player_map_x is None:
            return

        # 获取Canvas尺寸
        # canvas_width = self.map_canvas.canvas_width
        # canvas_height = self.map_canvas.canvas_height
        canvas_width = self.map_canvas.winfo_width()
        canvas_height = self.map_canvas.winfo_height()
        # 计算需要的offset使玩家在中心
        if self.map_canvas.map_image:
            img_width, img_height = self.map_canvas.map_image.size
            zoom = self.map_canvas.zoom

            # 计算玩家相对于地图中心的偏移
            player_dx = (self._player_map_x - img_width / 2) * zoom
            player_dy = (self._player_map_y - img_height / 2) * zoom

            # 设置offset使玩家在Canvas中心
            self.map_canvas.offset_x = canvas_width / 2 - player_dx
            self.map_canvas.offset_y = canvas_height / 2 - player_dy

            # 触发重绘
            self.map_canvas._render()

        # 不再设置定时器，只在新位置到达时才居中
        # 用户可以自由拖动地图，直到下次位置更新

    def set_opacity(self, opacity: float):
        """设置透明度"""
        self.opacity = max(0.1, min(1.0, opacity))
        self.attributes("-alpha", self.opacity)

    def set_compensation(self, brightness: float = 0.0, contrast: float = 0.0, gamma: float = 1.0):
        """
        设置悬浮窗对冲参数（用于抵消屏幕滤镜效果）

        Args:
            brightness: 亮度偏移 (-1.0 到 1.0)
            contrast: 对比度偏移 (-0.5 到 0.5)
            gamma: 伽马偏移 (0.5 到 3.5)
        """
        self.map_canvas.set_filters(brightness, contrast, gamma)

    def load_map(self, image_path: str) -> bool:
        """加载地图图片"""
        return self.map_canvas.load_map(image_path)

    def update_player_position(self, map_x: float, map_y: float, yaw: Optional[float] = None):
        """更新玩家位置"""
        self._player_map_x = map_x
        self._player_map_y = map_y
        self._player_yaw = yaw

        # 在地图上显示玩家
        self.map_canvas.show_player_position(map_x, map_y, yaw or 0.0)

        # 如果是居中模式，立即更新居中
        if self.player_centered:
            self._update_player_centering()

    def show_window(self):
        """显示窗口"""
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide_window(self):
        """隐藏窗口"""
        self.withdraw()

    def get_state(self) -> dict:
        """获取窗口状态"""
        return {
            "width": self.window_width,
            "height": self.window_height,
            "x": self.window_x,
            "y": self.window_y,
            "opacity": self.opacity,
            "zoom_level": self._saved_zoom,
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
        self.player_centered = state.get("player_centered", True)

        self.geometry(f"{self.window_width}x{self.window_height}+{self.window_x}+{self.window_y}")
        self.set_opacity(self.opacity)

        # 恢复缩放级别
        zoom = state.get("zoom_level", 1.0)
        self._saved_zoom = zoom
        self.map_canvas.set_zoom(zoom)

        is_locked = state.get("is_locked", False)
        if is_locked != self.is_locked:
            self.set_lock_state(is_locked)

        if self.player_centered:
            self._start_auto_follow()
