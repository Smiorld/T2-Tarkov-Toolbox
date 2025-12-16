"""
地图资源缓存管理器 - 单例模式
负责集中管理PIL Image、PhotoImage缓存和Transform结果

解决问题：
1. 消除主UI和悬浮窗的重复地图加载（2倍IO开销）
2. 消除重复的坐标变换计算（2倍运算开销）
3. 避免文件IO竞态条件错误
"""

import threading
from PIL import Image, ImageEnhance, ImageTk
from typing import Dict, Tuple, Optional
import numpy as np


class MapResourceCache:
    """
    地图资源缓存管理器（单例）

    职责：
    1. 缓存PIL Image对象（全局唯一，避免重复IO）
    2. 缓存PhotoImage对象（可被多个Canvas共享）
    3. 缓存CoordinateTransform结果（避免重复计算）

    线程安全：使用threading.Lock保护缓存访问
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # PIL Image缓存: {image_path: PIL.Image}
        self._image_cache: Dict[str, Image.Image] = {}

        # PhotoImage缓存: {cache_key: ImageTk.PhotoImage}
        # cache_key = (image_path, zoom, brightness, contrast, gamma)
        self._photo_cache: Dict[Tuple, ImageTk.PhotoImage] = {}

        # Transform缓存: {cache_key: CoordinateTransform}
        # cache_key = (map_id, layer_id, player_pos_hash)
        self._transform_cache: Dict[Tuple, any] = {}

        # 缓存大小限制
        self.photo_cache_max_size = 20  # 最多20个不同缩放级别
        self.transform_cache_max_size = 50  # 最多50个transform结果

        self._initialized = True

    # ==================== PIL Image管理 ====================

    def get_image(self, image_path: str) -> Optional[Image.Image]:
        """
        获取PIL Image对象（带缓存）

        Args:
            image_path: 图片文件路径（绝对路径）

        Returns:
            PIL.Image 或 None（加载失败）
        """
        with self._lock:
            if image_path in self._image_cache:
                return self._image_cache[image_path]

        try:
            print(f"[加载新图] PIL Image: {image_path}")
            img = Image.open(image_path)

            # 限制图片尺寸（防止内存溢出）
            max_dimension = 4096
            img_width, img_height = img.size
            if img_width > max_dimension or img_height > max_dimension:
                scale = max_dimension / max(img_width, img_height)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"  图片已缩小至 {new_width}x{new_height}")

            with self._lock:
                self._image_cache[image_path] = img

            return img

        except Exception as e:
            print(f"[错误] 加载图片失败: {e}")
            return None

    def clear_image(self, image_path: str):
        """清除指定图片缓存"""
        with self._lock:
            if image_path in self._image_cache:
                try:
                    img = self._image_cache.pop(image_path)
                    img.close()
                    print(f"[清除] PIL Image: {image_path}")
                except:
                    pass

                # 同时清除相关的PhotoImage缓存
                keys_to_remove = [k for k in self._photo_cache.keys() if k[0] == image_path]
                for key in keys_to_remove:
                    try:
                        del self._photo_cache[key]
                    except:
                        pass

    def clear_all_images(self):
        """清除所有图片缓存"""
        with self._lock:
            for img in self._image_cache.values():
                try:
                    img.close()
                except:
                    pass
            self._image_cache.clear()
            self._photo_cache.clear()
            print("[清除] 所有图片缓存已清空")

    # ==================== PhotoImage管理 ====================

    def get_photo_image(
        self,
        image_path: str,
        zoom: float,
        brightness: float = 0.0,
        contrast: float = 0.0,
        gamma: float = 1.0
    ) -> Optional[ImageTk.PhotoImage]:
        """
        获取PhotoImage对象（带缓存和滤镜处理）

        Args:
            image_path: 图片路径
            zoom: 缩放比例
            brightness: 亮度偏移 (-1.0 to 1.0)
            contrast: 对比度偏移 (-0.5 to 0.5)
            gamma: 伽马值 (0.5 to 3.5)

        Returns:
            ImageTk.PhotoImage 或 None
        """
        # 量化参数（避免过多缓存）
        cache_key = (
            image_path,
            round(zoom, 2),
            round(brightness, 2),
            round(contrast, 2),
            round(gamma, 2)
        )

        with self._lock:
            if cache_key in self._photo_cache:
                return self._photo_cache[cache_key]

        # 获取PIL Image
        base_image = self.get_image(image_path)
        if base_image is None:
            return None

        try:
            # 缩放
            img_width, img_height = base_image.size
            scaled_width = max(1, int(img_width * zoom))
            scaled_height = max(1, int(img_height * zoom))

            resample = Image.Resampling.LANCZOS if zoom < 1.0 else Image.Resampling.BILINEAR
            scaled_image = base_image.resize((scaled_width, scaled_height), resample)

            # 应用滤镜
            if brightness != 0.0 or contrast != 0.0 or gamma != 1.0:
                scaled_image = self._apply_filters(scaled_image, brightness, contrast, gamma)

            # 创建PhotoImage
            photo = ImageTk.PhotoImage(scaled_image)

            # 缓存管理（LRU简化版：删除最旧的）
            with self._lock:
                if len(self._photo_cache) >= self.photo_cache_max_size:
                    oldest_key = next(iter(self._photo_cache))
                    old_photo = self._photo_cache.pop(oldest_key)
                    try:
                        del old_photo
                    except:
                        pass

                self._photo_cache[cache_key] = photo
                print(f"[新建缓存] PhotoImage: zoom={zoom:.2f}, 缓存大小={len(self._photo_cache)}")

            return photo

        except Exception as e:
            print(f"[错误] 创建PhotoImage失败: {e}")
            return None

    def _apply_filters(self, image: Image.Image, brightness: float, contrast: float, gamma: float) -> Image.Image:
        """应用图片滤镜"""
        result = image.convert("RGB")

        # 亮度
        if brightness != 0.0:
            factor = max(0.0, min(2.0, 1.0 + brightness))
            enhancer = ImageEnhance.Brightness(result)
            result = enhancer.enhance(factor)

        # 对比度
        if contrast != 0.0:
            factor = max(0.0, min(2.0, 1.0 + contrast))
            enhancer = ImageEnhance.Contrast(result)
            result = enhancer.enhance(factor)

        # 伽马
        if gamma != 1.0:
            img_array = np.array(result, dtype=np.float32) / 255.0
            gamma_val = max(0.1, gamma)
            img_array = np.power(img_array, 1.0 / gamma_val)
            img_array = np.clip(img_array * 255.0, 0, 255).astype(np.uint8)
            result = Image.fromarray(img_array, mode="RGB")

        return result

    # ==================== CoordinateTransform管理 ====================

    def get_transform(
        self,
        config_manager: any,
        map_id: str,
        layer_id: int,
        player_pos: Optional[any] = None
    ) -> Optional[any]:
        """
        获取坐标变换矩阵（带缓存）

        Args:
            config_manager: 配置管理器实例
            map_id: 地图ID
            layer_id: 层级ID
            player_pos: 玩家位置（用于局部插值）

        Returns:
            CoordinateTransform 或 None
        """
        # 缓存键：将player_pos量化到10游戏单位精度
        player_hash = None
        if player_pos:
            player_hash = (
                round(player_pos.x / 10) * 10,
                round(player_pos.z / 10) * 10
            )

        cache_key = (map_id, layer_id, player_hash)

        with self._lock:
            if cache_key in self._transform_cache:
                return self._transform_cache[cache_key]

        # 计算新的transform
        try:
            print(f"[计算新Transform] {map_id} layer={layer_id}")
            transform = config_manager.calculate_transform(map_id, layer_id, player_pos)

            if transform:
                with self._lock:
                    # 缓存管理
                    if len(self._transform_cache) >= self.transform_cache_max_size:
                        oldest_key = next(iter(self._transform_cache))
                        self._transform_cache.pop(oldest_key)

                    self._transform_cache[cache_key] = transform
                    print(f"  Transform已缓存，大小={len(self._transform_cache)}")

            return transform

        except Exception as e:
            print(f"[错误] 计算Transform失败: {e}")
            return None

    def invalidate_transform(self, map_id: str, layer_id: int):
        """
        使指定层级的Transform缓存失效

        用于校准点变化后强制重新计算
        """
        with self._lock:
            keys_to_remove = [
                k for k in self._transform_cache.keys()
                if k[0] == map_id and k[1] == layer_id
            ]
            for key in keys_to_remove:
                self._transform_cache.pop(key, None)

            if keys_to_remove:
                print(f"[失效] 清除了 {len(keys_to_remove)} 个Transform缓存")

    def clear_all_transforms(self):
        """清除所有Transform缓存"""
        with self._lock:
            self._transform_cache.clear()
            print("[清除] 所有Transform缓存已清空")


# 全局单例实例（方便导入使用）
_resource_cache = MapResourceCache()


def get_resource_cache() -> MapResourceCache:
    """获取全局资源缓存实例"""
    return _resource_cache
