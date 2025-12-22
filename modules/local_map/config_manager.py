"""
Local Map Module - Configuration Manager

管理地图配置的加载、保存和持久化
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path
from .models import (
    MapConfig, MapLayer, CalibrationPoint, Position3D,
    FloatingMapConfig, CoordinateTransform, Rotation, Region
)
from datetime import datetime


class MapConfigManager:
    """地图配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        # 使用路径管理器获取配置文件路径
        if config_file is None:
            from utils import path_manager
            config_file = path_manager.get_map_config_path()

        self.config_file = config_file
        self.maps: Dict[str, MapConfig] = {}
        self.floating_config = FloatingMapConfig()
        self.load_config()

    def load_config(self):
        """从文件加载配置"""
        if not os.path.exists(self.config_file):
            self._create_default_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载地图配置
            for map_id, map_data in data.get('maps', {}).items():
                self.maps[map_id] = self._deserialize_map_config(map_data)

            # 加载浮动地图配置
            if 'floating_map' in data:
                self.floating_config = self._deserialize_floating_config(
                    data['floating_map']
                )

        except Exception as e:
            print(f"加载地图配置失败: {e}")
            self._create_default_config()

    def save_config(self):
        """保存配置到文件"""
        data = {
            'maps': {
                map_id: self._serialize_map_config(map_config)
                for map_id, map_config in self.maps.items()
            },
            'floating_map': self._serialize_floating_config(self.floating_config)
        }

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存地图配置失败: {e}")

    def _create_default_config(self):
        """创建默认配置"""
        # 创建默认的地图配置（空配置，等待用户导入地图）
        default_maps = [
            ("bigmap", "Customs"),
            ("Interchange", "Interchange"),
            ("Lighthouse", "Lighthouse"),
            ("TarkovStreets", "Streets of Tarkov"),
            ("Woods", "Woods"),
            ("Shoreline", "Shoreline"),
            ("RezervBase", "Reserve"),
            ("factory4_day", "Factory (Day)"),
            ("factory4_night", "Factory (Night)"),
            ("laboratory", "Laboratory"),
            ("Sandbox", "Ground Zero"),
        ]

        for map_id, display_name in default_maps:
            self.maps[map_id] = MapConfig(
                map_id=map_id,
                display_name=display_name,
                layers=[],
                default_layer_id=0
            )

        self.save_config()

    def get_map_config(self, map_id: str) -> Optional[MapConfig]:
        """获取指定地图的配置"""
        return self.maps.get(map_id)

    def set_map_image(self, map_id: str, layer_id: int, image_path: str,
                      layer_name: str = "Ground Floor",
                      height_min: float = 0.0,
                      height_max: float = 10.0,
                      rotation_offset: float = 0.0):
        """
        设置地图图片

        Args:
            map_id: 地图ID
            layer_id: 层级ID
            image_path: 图片文件路径
            layer_name: 层级名称
            height_min: 最小高度
            height_max: 最大高度
            rotation_offset: 地图旋转偏移（度数）
        """
        if map_id not in self.maps:
            print(f"地图ID '{map_id}' 不存在")
            return

        map_config = self.maps[map_id]
        existing_layer = map_config.get_layer_by_id(layer_id)

        if existing_layer:
            # 更新现有层级
            existing_layer.image_path = image_path
            existing_layer.name = layer_name
            existing_layer.height_min = height_min
            existing_layer.height_max = height_max
            existing_layer.rotation_offset = rotation_offset
        else:
            # 创建新层级
            new_layer = MapLayer(
                layer_id=layer_id,
                name=layer_name,
                image_path=image_path,
                height_min=height_min,
                height_max=height_max,
                calibration_points=[],
                rotation_offset=rotation_offset
            )
            map_config.add_layer(new_layer)

        self.save_config()

    def add_calibration_point(self, map_id: str, layer_id: int,
                              game_pos: Position3D, map_x: float, map_y: float):
        """
        添加校准点

        Args:
            map_id: 地图ID
            layer_id: 层级ID
            game_pos: 游戏世界坐标
            map_x: 地图图片X坐标
            map_y: 地图图片Y坐标
        """
        map_config = self.get_map_config(map_id)
        if not map_config:
            print(f"地图ID '{map_id}' 不存在")
            return

        layer = map_config.get_layer_by_id(layer_id)
        if not layer:
            print(f"层级ID '{layer_id}' 不存在")
            return

        calibration_point = CalibrationPoint(
            game_pos=game_pos,
            map_x=map_x,
            map_y=map_y
        )
        layer.calibration_points.append(calibration_point)
        self.save_config()

    def clear_calibration_points(self, map_id: str, layer_id: int):
        """清除指定层级的所有校准点"""
        map_config = self.get_map_config(map_id)
        if not map_config:
            return

        layer = map_config.get_layer_by_id(layer_id)
        if layer:
            layer.calibration_points.clear()
            self.save_config()

    def calculate_transform(
        self,
        map_id: str,
        layer_id: int,
        player_pos: Optional[Position3D] = None
    ) -> Optional[CoordinateTransform]:
        """
        计算指定层级的坐标变换矩阵

        Args:
            map_id: 地图ID
            layer_id: 层级ID
            player_pos: 玩家当前位置（可选，用于局部插值）

        Returns:
            CoordinateTransform or None
        """
        map_config = self.get_map_config(map_id)
        if not map_config:
            return None

        layer = map_config.get_layer_by_id(layer_id)
        if not layer or not layer.is_calibrated():
            return None

        try:
            return CoordinateTransform.calculate_from_points(
                layer.calibration_points,
                player_pos=player_pos
            )
        except Exception as e:
            print(f"计算坐标变换失败: {e}")
            return None

    def get_all_maps(self) -> List[MapConfig]:
        """获取所有地图配置"""
        return list(self.maps.values())

    def _serialize_map_config(self, map_config: MapConfig) -> dict:
        """序列化地图配置为字典"""
        return {
            'map_id': map_config.map_id,
            'display_name': map_config.display_name,
            'default_layer_id': map_config.default_layer_id,
            'layers': [self._serialize_layer(layer) for layer in map_config.layers]
        }

    def _deserialize_map_config(self, data: dict) -> MapConfig:
        """从字典反序列化地图配置"""
        return MapConfig(
            map_id=data['map_id'],
            display_name=data['display_name'],
            default_layer_id=data.get('default_layer_id', 0),
            layers=[self._deserialize_layer(layer_data) for layer_data in data.get('layers', [])]
        )

    def _serialize_layer(self, layer: MapLayer) -> dict:
        """序列化层级为字典"""
        result = {
            'layer_id': layer.layer_id,
            'name': layer.name,
            'image_path': layer.image_path,
            'height_min': layer.height_min,
            'height_max': layer.height_max,
            'rotation_offset': layer.rotation_offset,
            'is_base_map': layer.is_base_map,
            'region_owner_layer_id': layer.region_owner_layer_id,
            'calibration_points': [
                self._serialize_calibration_point(point)
                for point in layer.calibration_points
            ]
        }

        # 只序列化拥有的区域（非引用）
        if layer.is_region_owner():
            result['region'] = self._serialize_region(layer.region)

        return result

    def _deserialize_layer(self, data: dict) -> MapLayer:
        """从字典反序列化层级"""
        # 向后兼容：如果没有is_base_map字段，则layer_id=0被认为是大地图
        is_base_map = data.get('is_base_map', data['layer_id'] == 0)

        # 获取region_owner_layer_id（向后兼容：默认为None）
        region_owner_layer_id = data.get('region_owner_layer_id')

        # 只有在没有region_owner_layer_id时才反序列化region
        region = None
        if region_owner_layer_id is None:
            region_data = data.get('region')
            region = self._deserialize_region(region_data) if region_data else None

        return MapLayer(
            layer_id=data['layer_id'],
            name=data['name'],
            image_path=data['image_path'],
            height_min=data['height_min'],
            height_max=data['height_max'],
            rotation_offset=data.get('rotation_offset', 0.0),
            is_base_map=is_base_map,
            region=region,
            region_owner_layer_id=region_owner_layer_id,
            calibration_points=[
                self._deserialize_calibration_point(point_data)
                for point_data in data.get('calibration_points', [])
            ]
        )

    def _serialize_region(self, region: Region) -> dict:
        """序列化区域为字典"""
        return {
            'points': region.points
        }

    def _deserialize_region(self, data: dict) -> Region:
        """从字典反序列化区域"""
        return Region(
            points=data.get('points', [])
        )

    def _serialize_calibration_point(self, point: CalibrationPoint) -> dict:
        """序列化校准点为字典"""
        return {
            'game_pos': {
                'x': point.game_pos.x,
                'y': point.game_pos.y,
                'z': point.game_pos.z
            },
            'map_x': point.map_x,
            'map_y': point.map_y,
            'timestamp': point.timestamp.isoformat()
        }

    def _deserialize_calibration_point(self, data: dict) -> CalibrationPoint:
        """从字典反序列化校准点"""
        return CalibrationPoint(
            game_pos=Position3D(
                x=data['game_pos']['x'],
                y=data['game_pos']['y'],
                z=data['game_pos']['z']
            ),
            map_x=data['map_x'],
            map_y=data['map_y'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )

    def _serialize_floating_config(self, config: FloatingMapConfig) -> dict:
        """序列化浮动地图配置为字典"""
        return {
            'enabled': config.enabled,
            'width': config.width,
            'height': config.height,
            'pos_x': config.pos_x,
            'pos_y': config.pos_y,
            'opacity': config.opacity,
            'locked': config.locked,
            'always_on_top': config.always_on_top,
            'hotkey': config.hotkey,
            'zoom': config.zoom,
            'center_on_player': config.center_on_player
        }

    def _deserialize_floating_config(self, data: dict) -> FloatingMapConfig:
        """从字典反序列化浮动地图配置"""
        return FloatingMapConfig(
            enabled=data.get('enabled', False),
            width=data.get('width', 400),
            height=data.get('height', 400),
            pos_x=data.get('pos_x', 100),
            pos_y=data.get('pos_y', 100),
            opacity=data.get('opacity', 0.8),
            locked=data.get('locked', False),
            always_on_top=data.get('always_on_top', True),
            hotkey=data.get('hotkey', 'F5'),
            zoom=data.get('zoom', 1.0),
            center_on_player=data.get('center_on_player', True)
        )

    # ==================== 区域管理方法 ====================

    def set_layer_region(self, map_id: str, layer_id: int, region: Region):
        """
        设置楼层图的激活区域

        Args:
            map_id: 地图ID
            layer_id: 层级ID
            region: 区域对象
        """
        map_config = self.get_map_config(map_id)
        if not map_config:
            print(f"地图ID '{map_id}' 不存在")
            return

        layer = map_config.get_layer_by_id(layer_id)
        if not layer:
            print(f"层级ID '{layer_id}' 不存在")
            return

        if layer.is_base_map:
            print(f"大地图不需要设置区域")
            return

        layer.region = region
        self.save_config()

    def clear_layer_region(self, map_id: str, layer_id: int):
        """清除楼层图的激活区域"""
        map_config = self.get_map_config(map_id)
        if not map_config:
            return

        layer = map_config.get_layer_by_id(layer_id)
        if layer:
            layer.region = None
            self.save_config()

    def validate_region_no_overlap(
        self,
        map_id: str,
        new_region: Region,
        exclude_layer_id: Optional[int] = None
    ) -> tuple[bool, Optional[str], Optional[tuple[int, str]]]:
        """
        检查新区域是否与现有区域重合

        Args:
            map_id: 地图ID
            new_region: 新区域
            exclude_layer_id: 排除的层级ID（编辑现有区域时使用）

        Returns:
            (是否有效, 错误信息, owner_info)
            owner_info: (layer_id, layer_name) if overlap detected
        """
        map_config = self.get_map_config(map_id)
        if not map_config:
            return True, None, None

        for layer in map_config.get_floor_maps():
            # 跳过要排除的层级
            if exclude_layer_id is not None and layer.layer_id == exclude_layer_id:
                continue

            # 只检查拥有区域的layer（避免重复检查引用）
            if not layer.is_region_owner():
                continue

            # 跳过没有区域的层级
            if layer.region is None:
                continue

            # 检查是否重合
            if new_region.intersects_with(layer.region):
                owner_info = (layer.layer_id, layer.name)
                error_msg = f"新区域与楼层 '{layer.name}' (ID:{layer.layer_id}) 的区域重合"
                return False, error_msg, owner_info

        return True, None, None

    def validate_height_in_region(
        self,
        map_id: str,
        layer_id: int,
        height_min: float,
        height_max: float,
        region: Optional[Region] = None
    ) -> tuple[bool, Optional[str]]:
        """
        检查同区域内高度范围是否冲突

        Args:
            map_id: 地图ID
            layer_id: 当前层级ID（用于排除自己）
            height_min: 最小高度
            height_max: 最大高度
            region: 当前层级的区域（如果为None则不检查）

        Returns:
            (是否有效, 错误信息)
        """
        if region is None:
            # 没有区域，不需要检查
            return True, None

        map_config = self.get_map_config(map_id)
        if not map_config:
            return True, None

        for layer in map_config.get_floor_maps():
            # 跳过自己
            if layer.layer_id == layer_id:
                continue

            # 跳过没有区域的层级
            if layer.region is None:
                continue

            # 检查区域是否相同（通过点列表比较）
            if layer.region.points == region.points:
                # 同一区域，检查高度是否重合
                if not (height_max <= layer.height_min or height_min >= layer.height_max):
                    return False, f"高度范围与同区域的楼层 '{layer.name}' (ID:{layer.layer_id}, {layer.height_min}~{layer.height_max}) 重合"

        return True, None

    def get_layers_by_region(self, map_id: str, region: Region) -> List[MapLayer]:
        """
        获取与指定区域相交的所有楼层

        Args:
            map_id: 地图ID
            region: 区域

        Returns:
            相交的楼层列表
        """
        map_config = self.get_map_config(map_id)
        if not map_config:
            return []

        result = []
        for layer in map_config.get_floor_maps():
            if layer.region and layer.region.intersects_with(region):
                result.append(layer)

        return result

    def bind_layer_to_region(self, map_id: str, layer_id: int, owner_layer_id: int):
        """
        将楼层绑定到另一个楼层的区域

        Args:
            map_id: 地图ID
            layer_id: 当前层级ID
            owner_layer_id: 母layer的ID
        """
        map_config = self.get_map_config(map_id)
        if not map_config:
            return

        layer = map_config.get_layer_by_id(layer_id)
        owner_layer = map_config.get_layer_by_id(owner_layer_id)

        if not layer or not owner_layer:
            return

        # 检查owner_layer是否拥有区域
        if not owner_layer.is_region_owner():
            print(f"错误: Layer {owner_layer_id} 没有拥有区域")
            return

        # 清除当前layer的区域（如果有）
        layer.region = None
        # 设置引用
        layer.region_owner_layer_id = owner_layer_id

        self.save_config()

    def unbind_layer_region(self, map_id: str, layer_id: int):
        """
        解除楼层的区域绑定

        Args:
            map_id: 地图ID
            layer_id: 层级ID
        """
        map_config = self.get_map_config(map_id)
        if not map_config:
            return

        layer = map_config.get_layer_by_id(layer_id)
        if not layer:
            return

        layer.region = None
        layer.region_owner_layer_id = None

        self.save_config()

    def get_region_owner_info(self, map_id: str, region: Region) -> Optional[tuple[int, str]]:
        """
        查找拥有指定区域的layer信息

        Args:
            map_id: 地图ID
            region: 区域

        Returns:
            (layer_id, layer_name) 或 None
        """
        map_config = self.get_map_config(map_id)
        if not map_config:
            return None

        for layer in map_config.get_floor_maps():
            if layer.is_region_owner() and layer.region:
                # 检查区域是否重合
                if layer.region.intersects_with(region):
                    return (layer.layer_id, layer.name)

        return None

    def delete_layer(self, map_id: str, layer_id: int) -> tuple[bool, Optional[str]]:
        """
        删除地图中的指定层级

        如果删除的是区域母层级，会自动清除所有引用该层级的子层级的绑定

        Args:
            map_id: 地图ID
            layer_id: 要删除的层级ID

        Returns:
            (是否成功, 错误信息)
        """
        map_config = self.get_map_config(map_id)
        if not map_config:
            return False, f"地图ID '{map_id}' 不存在"

        # 查找要删除的层级
        target_layer = map_config.get_layer_by_id(layer_id)
        if not target_layer:
            return False, f"层级ID '{layer_id}' 不存在"

        # 防止删除大地图
        if target_layer.is_base_map:
            return False, "不能删除大地图（基础层）"

        # 如果是区域母层级，清除所有引用
        if target_layer.is_region_owner():
            sharing_layers = map_config.get_layers_sharing_region(layer_id)
            for layer in sharing_layers:
                layer.region_owner_layer_id = None
                print(f"已清除 Layer {layer.layer_id}: {layer.name} 对 Layer {layer_id} 的区域引用")

        # 删除层级
        if map_config.remove_layer(layer_id):
            self.save_config()
            return True, None
        else:
            return False, "删除失败（未知错误）"

    def get_base_map(self, map_id: str) -> Optional[MapLayer]:
        """获取指定地图的大地图层级"""
        map_config = self.get_map_config(map_id)
        if not map_config:
            return None
        return map_config.get_base_map()

    def count_base_maps(self, map_id: str) -> int:
        """统计指定地图的大地图数量（应始终为1）"""
        map_config = self.get_map_config(map_id)
        if not map_config:
            return 0
        return sum(1 for layer in map_config.layers if layer.is_base_map)

    def validate_base_map_constraint(self, map_id: str) -> tuple[bool, Optional[str]]:
        """验证大地图约束：每个地图必须有且仅有一个大地图"""
        count = self.count_base_maps(map_id)
        if count == 0:
            return False, "未找到大地图。每个地图必须有且仅有一个大地图。"
        elif count > 1:
            return False, f"找到 {count} 个大地图。每个地图必须有且仅有一个大地图。"
        return True, None

    def swap_base_map(self, map_id: str, new_base_layer_id: int) -> tuple[bool, Optional[str]]:
        """
        交换大地图：旧大地图→楼层图，新楼层图→大地图
        删除所有区域标记（大地图更改后区域坐标失效）
        """
        map_config = self.get_map_config(map_id)
        if not map_config:
            return False, f"地图 ID '{map_id}' 未找到"

        new_base_layer = map_config.get_layer_by_id(new_base_layer_id)
        if not new_base_layer:
            return False, f"层级 ID '{new_base_layer_id}' 未找到"

        if new_base_layer.is_base_map:
            return False, "该层级已经是大地图"

        old_base_map = map_config.get_base_map()
        if not old_base_map:
            return False, "未找到现有的大地图"

        # 交换大地图标记
        old_base_map.is_base_map = False
        new_base_layer.is_base_map = True

        # 清除所有楼层图的区域标记（大地图更改后区域坐标失效）
        for layer in map_config.layers:
            if not layer.is_base_map:
                layer.region = None
                layer.region_owner_layer_id = None

        self.save_config()
        return True, None

    def delete_all_regions(self, map_id: str):
        """删除所有楼层图的区域标记（当大地图更改时使用）"""
        map_config = self.get_map_config(map_id)
        if not map_config:
            return

        for layer in map_config.get_floor_maps():
            layer.region = None
            layer.region_owner_layer_id = None

        self.save_config()
