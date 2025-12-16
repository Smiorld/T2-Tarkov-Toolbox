"""
Local Map Module - Map Canvas Renderer

Canvas地图渲染器，支持缩放、平移、标记显示
优化版：使用图片缓存和Canvas原生缩放避免内存问题
"""

import customtkinter as ctk
from tkinter import Canvas
from PIL import Image, ImageTk, ImageEnhance
import math
from typing import Optional, List, Tuple, Dict


class MapCanvas(ctk.CTkFrame):
    """
    地图Canvas渲染器（优化版）

    功能：
    - 加载和显示地图图片
    - 鼠标拖拽平移
    - 滚轮缩放
    - 显示玩家位置标记
    - 显示校准点
    - 支持点击事件（用于校准）

    优化：
    - 图片缓存：避免重复缩放
    - 延迟渲染：拖拽时只移动，释放后才重新渲染
    - 内存管理：正确清理旧的PhotoImage对象
    """

    def __init__(self, parent, width=800, height=600):
        super().__init__(parent)

        self.canvas_width = width
        self.canvas_height = height

        # Canvas设置
        self.canvas = Canvas(
            self,
            width=width,
            height=height,
            bg="#2b2b2b",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # 地图图片相关
        self.map_image: Optional[Image.Image] = None  # 原始图片
        self.map_photo: Optional[ImageTk.PhotoImage] = None  # 当前显示的PhotoImage
        self.image_item = None

        # 图片缓存（不同缩放级别的预缩放图片）
        self.image_cache: Dict[float, ImageTk.PhotoImage] = {}
        self.cache_max_size = 10  # 最多缓存10个不同缩放级别

        # 视图状态
        self.zoom = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        # 拖拽状态
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False

        # 标记数据（用于重绘）
        self.calibration_points: List[Tuple[float, float, str]] = []  # (map_x, map_y, label)
        self.player_pos: Optional[Tuple[float, float, float]] = None  # (map_x, map_y, yaw)
        self.region_points: List[Tuple[float, float]] = []  # 区域标记点 [(map_x, map_y), ...]
        self.region_lines: List[Tuple[float, float]] = []  # 区域连线的点列表

        # 回调函数
        self.on_click_callback = None

        # 图片滤镜参数（用于悬浮窗对冲）
        self.filter_brightness = 0.0  # -1.0 to 1.0
        self.filter_contrast = 0.0    # -0.5 to 0.5
        self.filter_gamma = 1.0       # 0.5 to 3.5

        # 绑定事件
        self._bind_events()

    def _bind_events(self):
        """绑定鼠标事件"""
        # 拖拽
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        # 缩放
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)  # Linux
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)  # Linux

    def load_map(self, image_path: str) -> bool:
        """
        加载地图图片（使用全局缓存优化）

        Args:
            image_path: 图片文件路径

        Returns:
            bool: 是否加载成功
        """
        try:
            # 清除旧缓存（只清本地PhotoImage，不清全局PIL Image）
            if hasattr(self, '_current_image_path') and self._current_image_path != image_path:
                self._clear_cache()

            # === 改用全局缓存获取Image ===
            from .map_resource_cache import get_resource_cache
            resource_cache = get_resource_cache()

            self.map_image = resource_cache.get_image(image_path)
            self._current_image_path = image_path  # 记录当前路径

            if self.map_image is None:
                print(f"加载地图图片失败: {image_path}")
                return False
            # === 改动结束 ===

            self._reset_view()
            self._render()
            return True
        except Exception as e:
            print(f"加载地图图片失败: {e}")
            return False

    def _clear_cache(self):
        """清空本地PhotoImage缓存（不清除全局PIL Image缓存）"""
        # 注意：不清除全局PIL Image缓存，只清除本地PhotoImage引用
        for photo in self.image_cache.values():
            try:
                del photo
            except:
                pass
        self.image_cache.clear()

        if self.map_photo:
            try:
                del self.map_photo
            except:
                pass
            self.map_photo = None

    def _reset_view(self):
        """重置视图到初始状态"""
        if not self.map_image:
            return

        # 计算初始缩放比例，使地图适应Canvas
        img_width, img_height = self.map_image.size
        zoom_x = self.canvas_width / img_width
        zoom_y = self.canvas_height / img_height
        self.zoom = min(zoom_x, zoom_y) * 0.9  # 留10%边距

        # 居中
        self.offset_x = self.canvas_width / 2
        self.offset_y = self.canvas_height / 2

    def _get_cached_photo(self, zoom: float) -> ImageTk.PhotoImage:
        """
        获取缓存的PhotoImage（改用全局缓存）

        Args:
            zoom: 缩放比例

        Returns:
            ImageTk.PhotoImage: 缩放后的图片
        """
        # === 改用全局缓存 ===
        from .map_resource_cache import get_resource_cache
        resource_cache = get_resource_cache()

        if not hasattr(self, '_current_image_path'):
            # 回退到旧逻辑（理论上不会执行）
            return self._get_cached_photo_legacy(zoom)

        photo = resource_cache.get_photo_image(
            self._current_image_path,
            zoom,
            self.filter_brightness,
            self.filter_contrast,
            self.filter_gamma
        )

        return photo if photo else self._get_cached_photo_legacy(zoom)
        # === 改动结束 ===

    def _get_cached_photo_legacy(self, zoom: float) -> ImageTk.PhotoImage:
        """旧的缓存逻辑（保留作为回退）"""
        # 量化缩放级别和滤镜参数（避免过多缓存）
        zoom_key = (
            round(zoom, 2),
            round(self.filter_brightness, 2),
            round(self.filter_contrast, 2),
            round(self.filter_gamma, 2)
        )

        if zoom_key in self.image_cache:
            return self.image_cache[zoom_key]

        # 创建新的缩放图片
        img_width, img_height = self.map_image.size
        scaled_width = int(img_width * zoom)
        scaled_height = int(img_height * zoom)

        if scaled_width <= 0 or scaled_height <= 0:
            scaled_width = max(1, scaled_width)
            scaled_height = max(1, scaled_height)

        # 根据缩放比例选择合适的重采样方法
        if zoom < 1.0:
            # 缩小：使用LANCZOS获得更好质量
            resample = Image.Resampling.LANCZOS
        else:
            # 放大：使用BILINEAR速度更快
            resample = Image.Resampling.BILINEAR

        scaled_image = self.map_image.resize(
            (scaled_width, scaled_height),
            resample
        )

        # 应用图片滤镜（用于悬浮窗对冲屏幕滤镜）
        scaled_image = self._apply_image_filters(scaled_image)

        photo = ImageTk.PhotoImage(scaled_image)

        # 缓存管理：如果缓存太大，删除最旧的
        if len(self.image_cache) >= self.cache_max_size:
            # 删除第一个（最旧的）
            oldest_key = next(iter(self.image_cache))
            old_photo = self.image_cache.pop(oldest_key)
            try:
                del old_photo
            except:
                pass

        self.image_cache[zoom_key] = photo
        return photo

    def _apply_image_filters(self, image: Image.Image) -> Image.Image:
        """
        应用图片滤镜（亮度、对比度、伽马）

        这用于悬浮窗对冲屏幕滤镜效果，防止过曝。
        使用PIL的ImageEnhance进行图片级别的调整。

        Args:
            image: 要处理的图片

        Returns:
            Image.Image: 处理后的图片
        """
        # 如果所有滤镜都是默认值，直接返回
        if (self.filter_brightness == 0.0 and
            self.filter_contrast == 0.0 and
            self.filter_gamma == 1.0):
            return image

        result = image.convert("RGB")

        # 1. 应用亮度调整
        # filter_brightness范围: -1.0到1.0
        # ImageEnhance.Brightness factor: 0.0=黑色, 1.0=原图, 2.0=加倍亮度
        if self.filter_brightness != 0.0:
            brightness_factor = 1.0 + self.filter_brightness
            brightness_factor = max(0.0, min(2.0, brightness_factor))
            enhancer = ImageEnhance.Brightness(result)
            result = enhancer.enhance(brightness_factor)

        # 2. 应用对比度调整
        # filter_contrast范围: -0.5到0.5
        # ImageEnhance.Contrast factor: 0.0=灰色, 1.0=原图, 2.0=加倍对比度
        if self.filter_contrast != 0.0:
            contrast_factor = 1.0 + self.filter_contrast
            contrast_factor = max(0.0, min(2.0, contrast_factor))
            enhancer = ImageEnhance.Contrast(result)
            result = enhancer.enhance(contrast_factor)

        # 3. 应用伽马校正
        # filter_gamma范围: 0.5到3.5
        # 伽马校正需要手动实现：output = input^(1/gamma)
        if self.filter_gamma != 1.0:
            import numpy as np

            # 转换为numpy数组
            img_array = np.array(result, dtype=np.float32) / 255.0

            # 应用伽马校正
            gamma = max(0.1, self.filter_gamma)  # 防止除以0
            img_array = np.power(img_array, 1.0 / gamma)

            # 转换回PIL图片
            img_array = np.clip(img_array * 255.0, 0, 255).astype(np.uint8)
            result = Image.fromarray(img_array, mode="RGB")

        return result

    def set_filters(self, brightness: float = 0.0, contrast: float = 0.0, gamma: float = 1.0):
        """
        设置图片滤镜参数

        Args:
            brightness: 亮度偏移 (-1.0 到 1.0)
            contrast: 对比度偏移 (-0.5 到 0.5)
            gamma: 伽马值 (0.5 到 3.5)
        """
        # 检查参数是否改变
        changed = (
            self.filter_brightness != brightness or
            self.filter_contrast != contrast or
            self.filter_gamma != gamma
        )

        if changed:
            self.filter_brightness = brightness
            self.filter_contrast = contrast
            self.filter_gamma = gamma

            # 清空缓存（因为滤镜参数改变了）
            self.image_cache.clear()

            # 重新渲染
            self._render()

    def _render(self):
        """重新渲染Canvas"""
        if not self.map_image:
            return

        # 清空Canvas
        self.canvas.delete("all")

        # 使用缓存的图片
        try:
            self.map_photo = self._get_cached_photo(self.zoom)

            # 计算图片位置（以中心点为基准）
            x = self.offset_x
            y = self.offset_y

            self.image_item = self.canvas.create_image(
                x, y,
                image=self.map_photo,
                anchor="center"
            )
        except Exception as e:
            print(f"渲染地图失败: {e}")
            return

        # 重新绘制所有标记
        self._redraw_markers()

    def _redraw_markers(self):
        """重新绘制所有标记"""
        # 绘制区域连线（最底层）
        if len(self.region_lines) >= 2:
            self._draw_region_lines_internal()

        # 绘制区域标记点
        for i, (map_x, map_y) in enumerate(self.region_points, 1):
            self._draw_region_marker(map_x, map_y, i)

        # 绘制校准点
        for map_x, map_y, label in self.calibration_points:
            self._draw_calibration_marker(map_x, map_y, label)

        # 绘制玩家位置
        if self.player_pos:
            map_x, map_y, yaw = self.player_pos
            self._draw_player_marker(map_x, map_y, yaw)

    def _draw_calibration_marker(self, map_x: float, map_y: float, label: str = ""):
        """绘制单个校准点标记"""
        canvas_x, canvas_y = self._map_to_canvas_coords(map_x, map_y)

        # 绘制圆圈
        radius = 8
        self.canvas.create_oval(
            canvas_x - radius, canvas_y - radius,
            canvas_x + radius, canvas_y + radius,
            fill="red",
            outline="white",
            width=2,
            tags="calibration"
        )

        # 绘制标签
        if label:
            self.canvas.create_text(
                canvas_x, canvas_y - 15,
                text=label,
                fill="white",
                font=("Arial", 10, "bold"),
                tags="calibration"
            )

    def _draw_player_marker(self, map_x: float, map_y: float, yaw: float = 0.0):
        """绘制玩家位置标记"""
        canvas_x, canvas_y = self._map_to_canvas_coords(map_x, map_y)

        # 绘制玩家标记（圆形）
        radius = 10
        self.canvas.create_oval(
            canvas_x - radius, canvas_y - radius,
            canvas_x + radius, canvas_y + radius,
            fill="#00ff00",
            outline="#ffffff",
            width=3,
            tags="player"
        )

        # 绘制方向箭头
        arrow_length = 20
        arrow_rad = math.radians(yaw+180)
        end_x = canvas_x + arrow_length * math.sin(arrow_rad)
        end_y = canvas_y - arrow_length * math.cos(arrow_rad)

        self.canvas.create_line(
            canvas_x, canvas_y,
            end_x, end_y,
            fill="#00ff00",
            width=3,
            arrow="last",
            arrowshape=(10, 12, 5),
            tags="player"
        )

    def _draw_region_marker(self, map_x: float, map_y: float, index: int):
        """绘制单个区域标记点"""
        canvas_x, canvas_y = self._map_to_canvas_coords(map_x, map_y)

        # 绘制圆圈（蓝色）
        radius = 6
        self.canvas.create_oval(
            canvas_x - radius, canvas_y - radius,
            canvas_x + radius, canvas_y + radius,
            fill="#0080ff",
            outline="white",
            width=2,
            tags="region"
        )

        # 绘制标签（区域点编号）
        self.canvas.create_text(
            canvas_x, canvas_y - 12,
            text=f"R{index}",
            fill="white",
            font=("Arial", 9, "bold"),
            tags="region"
        )

    def _draw_region_lines_internal(self):
        """绘制区域连线（内部方法，用于重绘）"""
        if len(self.region_lines) < 2:
            return

        # 转换所有点到Canvas坐标
        canvas_points = []
        for map_x, map_y in self.region_lines:
            canvas_x, canvas_y = self._map_to_canvas_coords(map_x, map_y)
            canvas_points.extend([canvas_x, canvas_y])

        # 绘制多边形边界线
        for i in range(0, len(canvas_points) - 2, 2):
            self.canvas.create_line(
                canvas_points[i], canvas_points[i+1],
                canvas_points[i+2], canvas_points[i+3],
                fill="#0080ff",
                width=2,
                dash=(5, 3),
                tags="region"
            )

        # 绘制闭合线（连接最后一个点和第一个点）
        if len(self.region_lines) >= 3:
            self.canvas.create_line(
                canvas_points[-2], canvas_points[-1],
                canvas_points[0], canvas_points[1],
                fill="#0080ff",
                width=2,
                dash=(5, 3),
                tags="region"
            )

        # 绘制半透明填充区域
        if len(self.region_lines) >= 3:
            self.canvas.create_polygon(
                *canvas_points,
                fill="#0080ff",
                stipple="gray50",
                outline="",
                tags="region"
            )

    def _on_mouse_down(self, event):
        """鼠标按下"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.is_dragging = False

    def _on_mouse_drag(self, event):
        """鼠标拖拽"""
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        # 判断是否是拖拽（移动超过5像素）
        if abs(dx) > 5 or abs(dy) > 5:
            self.is_dragging = True

        if self.is_dragging:
            # 只移动Canvas内容，不重新渲染
            self.canvas.move("all", dx, dy)
            self.offset_x += dx
            self.offset_y += dy
            self.drag_start_x = event.x
            self.drag_start_y = event.y

    def _on_mouse_up(self, event):
        """鼠标释放"""
        if not self.is_dragging and self.on_click_callback:
            # 这是点击而不是拖拽，触发点击回调
            map_x, map_y = self._canvas_to_map_coords(event.x, event.y)
            if map_x is not None:
                self.on_click_callback(map_x, map_y)

        self.is_dragging = False

    def _on_mouse_wheel(self, event):
        """鼠标滚轮缩放"""
        # 获取鼠标位置
        mouse_x = event.x
        mouse_y = event.y

        # 计算缩放因子
        if event.num == 4 or event.delta > 0:  # 向上滚动
            zoom_factor = 1.1
        elif event.num == 5 or event.delta < 0:  # 向下滚动
            zoom_factor = 0.9
        else:
            return

        # 计算新的缩放比例
        new_zoom = self.zoom * zoom_factor
        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return

        # 以鼠标位置为中心缩放
        # 1. 计算鼠标相对于图片中心的偏移
        dx = mouse_x - self.offset_x
        dy = mouse_y - self.offset_y

        # 2. 缩放后调整偏移，使鼠标下的点保持不变
        scale_ratio = new_zoom / self.zoom
        self.offset_x = mouse_x - dx * scale_ratio
        self.offset_y = mouse_y - dy * scale_ratio

        self.zoom = new_zoom
        self._render()

    def _canvas_to_map_coords(self, canvas_x: float, canvas_y: float) -> Tuple[Optional[float], Optional[float]]:
        """
        将Canvas坐标转换为地图图片坐标

        Args:
            canvas_x, canvas_y: Canvas上的像素坐标

        Returns:
            (map_x, map_y): 地图图片上的像素坐标，如果超出范围返回(None, None)
        """
        if not self.map_image:
            return None, None

        # 计算相对于图片中心的偏移
        dx = canvas_x - self.offset_x
        dy = canvas_y - self.offset_y

        # 转换为地图坐标（图片左上角为原点）
        img_width, img_height = self.map_image.size
        map_x = img_width / 2 + dx / self.zoom
        map_y = img_height / 2 + dy / self.zoom

        # 检查是否在地图范围内
        if 0 <= map_x <= img_width and 0 <= map_y <= img_height:
            return map_x, map_y

        return None, None

    def _map_to_canvas_coords(self, map_x: float, map_y: float) -> Tuple[float, float]:
        """
        将地图图片坐标转换为Canvas坐标

        Args:
            map_x, map_y: 地图图片上的像素坐标

        Returns:
            (canvas_x, canvas_y): Canvas上的像素坐标
        """
        if not self.map_image:
            return 0, 0

        # 计算相对于图片中心的偏移
        img_width, img_height = self.map_image.size
        dx = (map_x - img_width / 2) * self.zoom
        dy = (map_y - img_height / 2) * self.zoom

        # 转换为Canvas坐标
        canvas_x = self.offset_x + dx
        canvas_y = self.offset_y + dy

        return canvas_x, canvas_y

    def add_calibration_marker(self, map_x: float, map_y: float, label: str = ""):
        """
        添加校准点标记

        Args:
            map_x, map_y: 地图图片坐标
            label: 标签文字
        """
        # 保存到数据
        self.calibration_points.append((map_x, map_y, label))

        # 绘制标记
        self._draw_calibration_marker(map_x, map_y, label)

    def clear_calibration_markers(self):
        """清除所有校准点标记"""
        self.canvas.delete("calibration")
        self.calibration_points.clear()

    def show_player_position(self, map_x: float, map_y: float, yaw: float = 0.0):
        """
        显示玩家位置标记

        Args:
            map_x, map_y: 地图图片坐标
            yaw: 玩家朝向角度（度数，0为正北）
        """
        # 保存到数据
        self.player_pos = (map_x, map_y, yaw)

        # 清除旧标记
        self.canvas.delete("player")

        # 绘制新标记
        self._draw_player_marker(map_x, map_y, yaw)

    def clear_player_marker(self):
        """清除玩家标记"""
        self.canvas.delete("player")
        self.player_pos = None

    def add_region_point(self, map_x: float, map_y: float, index: int):
        """
        添加区域标记点

        Args:
            map_x, map_y: 地图图片坐标
            index: 点的序号（用于显示标签）
        """
        # 保存到数据
        self.region_points.append((map_x, map_y))

        # 绘制标记
        self._draw_region_marker(map_x, map_y, index)

    def draw_region_lines(self, points: List[Tuple[float, float]]):
        """
        绘制区域连线

        Args:
            points: 区域点列表 [(map_x, map_y), ...]
        """
        # 保存到数据
        self.region_lines = list(points)

        # 清除旧的连线
        self.canvas.delete("region")

        # 重新绘制所有区域元素
        if len(self.region_lines) >= 2:
            self._draw_region_lines_internal()

        # 重新绘制区域标记点
        for i, (map_x, map_y) in enumerate(self.region_points, 1):
            self._draw_region_marker(map_x, map_y, i)

    def clear_region_markers(self):
        """清除所有区域标记"""
        self.canvas.delete("region")
        self.region_points.clear()
        self.region_lines.clear()

    def set_zoom(self, zoom: float):
        """
        设置缩放比例

        Args:
            zoom: 缩放比例
        """
        zoom = max(self.min_zoom, min(self.max_zoom, zoom))
        if zoom != self.zoom:
            self.zoom = zoom
            self._render()

    def reset_view(self):
        """重置视图到默认状态"""
        self._reset_view()
        self._render()

    def set_click_callback(self, callback):
        """
        设置点击回调函数

        Args:
            callback: 回调函数 callback(map_x, map_y)
        """
        self.on_click_callback = callback


# 测试代码
if __name__ == "__main__":
    import os

    root = ctk.CTk()
    root.title("地图Canvas测试")
    root.geometry("900x700")

    # 创建MapCanvas
    map_canvas = MapCanvas(root, width=800, height=600)
    map_canvas.pack(padx=20, pady=20)

    # 测试：尝试加载一张测试图片
    # 如果有地图图片，可以在这里加载
    test_image_path = "test_map.png"
    if os.path.exists(test_image_path):
        map_canvas.load_map(test_image_path)

        # 添加测试标记
        map_canvas.add_calibration_marker(100, 100, "Point 1")
        map_canvas.add_calibration_marker(300, 200, "Point 2")
        map_canvas.show_player_position(200, 150, yaw=45)
    else:
        print(f"测试图片不存在: {test_image_path}")

    # 点击回调测试
    def on_click(map_x, map_y):
        print(f"点击地图: ({map_x:.1f}, {map_y:.1f})")
        map_canvas.add_calibration_marker(map_x, map_y)

    map_canvas.set_click_callback(on_click)

    root.mainloop()
