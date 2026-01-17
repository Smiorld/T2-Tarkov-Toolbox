"""
Local Map Module - Data Models

数据结构设计用于支持多层地图系统和坐标映射
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum


class MapName(Enum):
    """塔科夫地图名称枚举"""
    CUSTOMS = "bigmap"
    FACTORY_DAY = "factory4_day"
    FACTORY_NIGHT = "factory4_night"
    INTERCHANGE = "Interchange"
    LABORATORY = "laboratory"
    LABYRINTH = "Labyrinth"
    LIGHTHOUSE = "Lighthouse"
    RESERVE = "RezervBase"
    SANDBOX = "Sandbox"
    SANDBOX_HIGH = "Sandbox_high"
    SHORELINE = "Shoreline"
    STREETS = "TarkovStreets"
    TERMINAL = "Terminal"
    WOODS = "Woods"


@dataclass
class Position3D:
    """
    3D坐标位置

    塔科夫游戏内的世界坐标系统
    """
    x: float
    y: float  # Y轴是高度
    z: float

    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

    def distance_to(self, other: 'Position3D') -> float:
        """计算到另一个点的欧氏距离"""
        return ((self.x - other.x) ** 2 +
                (self.y - other.y) ** 2 +
                (self.z - other.z) ** 2) ** 0.5


@dataclass
class Rotation:
    """
    旋转信息（四元数）

    从塔科夫截图文件名解析得到
    """
    x: float
    y: float
    z: float
    w: float

    def to_yaw(self) -> float:
        """
        转换四元数到Yaw角度（度数）

        完全按照TarkovMonitor的实现
        TarkovMonitor源码: GameWatcher.cs Line 257-282

        关键：参数交换
        - 文件名的 (rx, ry, rz, rw)
        - 映射到 (x, z, y, w) 用于计算
        """
        import math

        # TarkovMonitor的参数交换：ry和rz互换
        # private float QuarternionsToYaw(float x, float z, float y, float w)
        # 调用时传入 (rx, ry, rz, rw)，但参数是 (x, z, y, w)
        qx = self.x  # rx → x
        qz = self.y  # ry → z (交换!)
        qy = self.z  # rz → y (交换!)
        qw = self.w  # rw → w

        # TarkovMonitor的公式
        siny_cosp = 2.0 * (qw * qz + qx * qy)
        cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        # 转换为度数
        return yaw * (180.0 / math.pi)


@dataclass
class CalibrationPoint:
    """
    校准点

    用于将游戏世界坐标映射到地图图片坐标
    """
    game_pos: Position3D  # 游戏世界坐标
    map_x: float  # 地图图片上的像素X坐标
    map_y: float  # 地图图片上的像素Y坐标
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"Game{self.game_pos} -> Map({self.map_x:.1f}, {self.map_y:.1f})"


@dataclass
class Region:
    """
    楼层图的激活区域定义

    在大地图上定义的多边形区域（通过多个点连线形成闭环）
    用于判断玩家是否进入特定建筑/区域，从而激活对应的楼层图
    """
    points: List[Tuple[float, float]] = field(default_factory=list)  # 区域边界点列表 [(map_x1, map_y1), ...]

    def contains_point(self, map_x: float, map_y: float) -> bool:
        """
        判断地图坐标是否在区域内（多边形点包含判断）

        使用射线法（Ray Casting Algorithm）：
        从点发出水平射线，计算与多边形边界的交点数
        - 奇数：点在内部
        - 偶数：点在外部

        Args:
            map_x: 地图坐标X
            map_y: 地图坐标Y

        Returns:
            bool: 是否在区域内
        """
        if len(self.points) < 3:
            return False

        n = len(self.points)
        inside = False

        p1x, p1y = self.points[0]
        for i in range(1, n + 1):
            p2x, p2y = self.points[i % n]
            if map_y > min(p1y, p2y):
                if map_y <= max(p1y, p2y):
                    if map_x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (map_y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or map_x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def intersects_with(self, other: 'Region') -> bool:
        """
        检查两个区域是否重合（多边形相交检测）

        使用简化算法：
        1. 检查任一区域的顶点是否在另一区域内
        2. 检查边界是否相交

        Args:
            other: 另一个区域

        Returns:
            bool: True表示两个区域重合，False表示不重合
        """
        # 方法1：检查 self 的任一顶点是否在 other 内
        for point in self.points:
            if other.contains_point(point[0], point[1]):
                return True

        # 方法2：检查 other 的任一顶点是否在 self 内
        for point in other.points:
            if self.contains_point(point[0], point[1]):
                return True

        # 方法3：检查边界是否相交（Segment-Segment Intersection）
        for i in range(len(self.points)):
            seg1_start = self.points[i]
            seg1_end = self.points[(i + 1) % len(self.points)]

            for j in range(len(other.points)):
                seg2_start = other.points[j]
                seg2_end = other.points[(j + 1) % len(other.points)]

                if self._segments_intersect(seg1_start, seg1_end, seg2_start, seg2_end):
                    return True

        return False

    @staticmethod
    def _segments_intersect(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        p4: Tuple[float, float]
    ) -> bool:
        """
        判断两条线段是否相交

        使用跨立实验（Straddle Test）：
        线段AB与CD相交 ⟺ A和B在CD两侧 且 C和D在AB两侧
        """
        def cross_product(o, a, b):
            """计算向量OA和OB的叉积"""
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        d1 = cross_product(p3, p4, p1)
        d2 = cross_product(p3, p4, p2)
        d3 = cross_product(p1, p2, p3)
        d4 = cross_product(p1, p2, p4)

        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
           ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
            return True

        # 边界情况：三点共线且其中一点在线段上
        if d1 == 0 and self._on_segment(p3, p1, p4):
            return True
        if d2 == 0 and self._on_segment(p3, p2, p4):
            return True
        if d3 == 0 and self._on_segment(p1, p3, p2):
            return True
        if d4 == 0 and self._on_segment(p1, p4, p2):
            return True

        return False

    @staticmethod
    def _on_segment(
        p: Tuple[float, float],
        q: Tuple[float, float],
        r: Tuple[float, float]
    ) -> bool:
        """判断点Q是否在线段PR上（假设三点共线）"""
        return (q[0] <= max(p[0], r[0]) and q[0] >= min(p[0], r[0]) and
                q[1] <= max(p[1], r[1]) and q[1] >= min(p[1], r[1]))


@dataclass
class MapLayer:
    """
    地图层级

    支持两种类型：
    1. 大地图（is_base_map=True）：全景地图，作为默认显示，无需region
    2. 楼层图（is_base_map=False）：特定建筑的楼层，需要region定义激活区域

    区域共享机制：
    - region_owner_layer_id为None：当前layer拥有region（母layer）
    - region_owner_layer_id不为None：当前layer引用其他layer的region
    """
    layer_id: int  # 层级ID（0=地面层，正数=楼上，负数=地下）
    name: str  # 层级名称（例如："1F"、"2F"、"B1"）
    image_path: str  # 地图图片路径
    height_min: float  # 该层的最小高度（Y坐标）
    height_max: float  # 该层的最大高度（Y坐标）
    calibration_points: List[CalibrationPoint] = field(default_factory=list)
    rotation_offset: float = 0.0  # 地图旋转偏移（度数），用于修正地图方向
    is_base_map: bool = False  # 是否为大地图（基础层）
    region: Optional[Region] = None  # 激活区域（仅楼层图需要，大地图为None）
    region_owner_layer_id: Optional[int] = None  # 区域所属的母layer ID（None表示自己拥有区域）

    def contains_height(self, y: float) -> bool:
        """判断某个高度是否属于这一层"""
        return self.height_min <= y <= self.height_max

    def is_calibrated(self) -> bool:
        """判断该层是否已校准（至少需要3个点）"""
        return len(self.calibration_points) >= 3

    def get_effective_region(self, map_config: 'MapConfig') -> Optional[Region]:
        """
        获取有效的区域（自己的或引用的）

        Args:
            map_config: 地图配置对象（用于查找引用的layer）

        Returns:
            Region: 有效的区域，如果没有则返回None
        """
        if self.region is not None:
            # 当前layer拥有区域
            return self.region

        if self.region_owner_layer_id is not None:
            # 引用其他layer的区域
            owner_layer = map_config.get_layer_by_id(self.region_owner_layer_id)
            if owner_layer and owner_layer.region:
                return owner_layer.region

        return None

    def is_region_owner(self) -> bool:
        """
        判断当前layer是否拥有区域（非引用）

        Returns:
            bool: True表示拥有区域，False表示引用或无区域
        """
        return self.region is not None and self.region_owner_layer_id is None

    def is_activated(
        self,
        player_pos: Position3D,
        player_map_pos: Optional[Tuple[float, float]] = None,
        map_config: Optional['MapConfig'] = None
    ) -> bool:
        """
        判断该层级是否应该被激活

        Args:
            player_pos: 玩家游戏坐标（用于高度判断）
            player_map_pos: 玩家在大地图上的坐标（用于区域判断，可选）
            map_config: 地图配置对象（用于支持区域引用，可选）

        Returns:
            bool: 是否激活
        """
        # 大地图：始终可激活（作为兜底层）
        if self.is_base_map:
            return True

        # 获取有效区域（支持引用）
        effective_region = self.get_effective_region(map_config) if map_config else self.region

        # 楼层图：必须同时满足高度和区域条件
        if effective_region is None:
            # 如果没有定义区域，退化为仅高度判断（兼容旧逻辑）
            return self.contains_height(player_pos.y)

        # 高度条件
        in_height_range = self.contains_height(player_pos.y)
        if not in_height_range:
            return False

        # 区域条件（需要先在大地图上转换玩家坐标）
        if player_map_pos is None:
            return False

        map_x, map_y = player_map_pos
        in_region = effective_region.contains_point(map_x, map_y)

        return in_region


@dataclass
class MapConfig:
    """
    地图配置

    包含单个塔科夫地图的所有层级和校准信息
    """
    map_id: str  # 地图ID（例如："bigmap"、"Interchange"）
    display_name: str  # 显示名称（例如："Customs"、"Interchange"）
    layers: List[MapLayer] = field(default_factory=list)
    default_layer_id: int = 0  # 默认层级

    def get_layer_by_id(self, layer_id: int) -> Optional[MapLayer]:
        """根据层级ID获取层级"""
        for layer in self.layers:
            if layer.layer_id == layer_id:
                return layer
        return None

    def get_layer_by_height(self, y: float) -> Optional[MapLayer]:
        """
        根据高度自动匹配层级（旧逻辑，保留以兼容）

        注意：此方法仅基于高度判断，不考虑区域。
        新代码应使用 get_active_layer() 方法。
        """
        for layer in self.layers:
            if layer.contains_height(y):
                return layer
        return None

    def get_base_map(self) -> Optional[MapLayer]:
        """获取大地图（基础层）"""
        for layer in self.layers:
            if layer.is_base_map:
                return layer
        return None

    def get_floor_maps(self) -> List[MapLayer]:
        """获取所有楼层图（非大地图）"""
        return [layer for layer in self.layers if not layer.is_base_map]

    def get_layers_sharing_region(self, owner_layer_id: int) -> List[MapLayer]:
        """
        获取所有引用指定layer区域的楼层

        Args:
            owner_layer_id: 母layer的ID

        Returns:
            List[MapLayer]: 引用该区域的所有layer列表
        """
        result = []
        for layer in self.layers:
            if layer.region_owner_layer_id == owner_layer_id:
                result.append(layer)
        return result

    def get_active_layer(
        self,
        player_pos: Position3D,
        base_map_transform: Optional['CoordinateTransform'] = None
    ) -> Optional[MapLayer]:
        """
        智能选择激活的层级（新逻辑）

        优先级：
        1. 楼层图（满足区域+高度条件）
        2. 大地图（兜底）

        Args:
            player_pos: 玩家游戏坐标
            base_map_transform: 大地图的坐标变换（用于计算玩家在大地图上的位置）

        Returns:
            MapLayer: 应该激活的层级，如果没有合适的返回None
        """
        # 计算玩家在大地图上的坐标（用于区域判断）
        player_map_pos = None
        if base_map_transform:
            try:
                player_map_pos = base_map_transform.transform(player_pos)
            except:
                pass

        # 优先检查所有楼层图（按高度降序，高楼层优先）
        floor_maps = sorted(self.get_floor_maps(), key=lambda l: l.height_max, reverse=True)
        for layer in floor_maps:
            # 传入map_config以支持区域引用
            if layer.is_activated(player_pos, player_map_pos, self):
                return layer

        # 兜底：返回大地图
        base_map = self.get_base_map()
        if base_map:
            return base_map

        # 终极兜底：返回第一个层级（向后兼容）
        return self.layers[0] if self.layers else None

    def add_layer(self, layer: MapLayer):
        """添加新层级"""
        self.layers.append(layer)
        # 按层级ID排序
        self.layers.sort(key=lambda l: l.layer_id)

    def remove_layer(self, layer_id: int) -> bool:
        """
        删除指定的层级

        Args:
            layer_id: 要删除的层级ID

        Returns:
            bool: 删除成功返回True，层级不存在返回False
        """
        for i, layer in enumerate(self.layers):
            if layer.layer_id == layer_id:
                self.layers.pop(i)
                return True
        return False


@dataclass
class PlayerPosition:
    """
    玩家位置信息

    从截图文件名解析得到
    """
    position: Position3D
    rotation: Rotation
    map_id: str
    timestamp: datetime
    screenshot_filename: str

    # 映射后的地图坐标（通过校准点计算得到）
    map_x: Optional[float] = None
    map_y: Optional[float] = None
    layer_id: Optional[int] = None


@dataclass
class RaidInfo:
    """
    战局信息

    从日志文件解析得到
    """
    raid_id: str  # 战局ID（6位字符）
    map_id: str  # 地图ID
    is_online: bool  # 是否在线模式
    is_pmc: bool  # 是否PMC（False为Scav）
    server_ip: Optional[str] = None  # 服务器IP
    server_location: Optional[str] = None  # 服务器地理位置
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    queue_time: float = 0.0  # 匹配等待时间（秒）


@dataclass
class CoordinateTransform:
    """
    坐标变换矩阵

    用于将游戏世界坐标转换为地图图片坐标
    使用仿射变换（Affine Transform）

    仿射变换公式:
    map_x = a * game_x + b * game_z + c
    map_y = d * game_x + e * game_z + f

    其中系数矩阵已经包含了旋转、缩放和平移信息
    """
    # 仿射变换系数
    # map_x = a * game_x + b * game_z + c
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0

    # map_y = d * game_x + e * game_z + f
    d: float = 0.0
    e: float = 1.0
    f: float = 0.0

    # 几何参数（从系数矩阵提取，仅用于显示）
    scale_x: float = 1.0
    scale_z: float = 1.0
    offset_x: float = 0.0
    offset_z: float = 0.0
    rotation: float = 0.0  # 旋转角度（弧度）

    def transform(self, game_pos: Position3D) -> Tuple[float, float]:
        """
        将游戏坐标转换为地图坐标

        直接应用仿射变换公式，不需要手动应用旋转
        因为系数a,b,d,e已经包含了旋转信息

        Args:
            game_pos: 游戏世界坐标

        Returns:
            (map_x, map_y): 地图图片像素坐标
        """
        # 直接应用仿射变换
        map_x = self.a * game_pos.x + self.b * game_pos.z + self.c
        map_y = self.d * game_pos.x + self.e * game_pos.z + self.f

        return (map_x, map_y)

    @staticmethod
    def calculate_from_points(
        points: List[CalibrationPoint],
        player_pos: Optional['Position3D'] = None,
        use_local_interpolation: bool = True
    ) -> 'CoordinateTransform':
        """
        从校准点计算变换矩阵

        使用最小二乘法拟合仿射变换
        需要至少3个点

        Args:
            points: 校准点列表
            player_pos: 玩家当前位置（可选，用于局部插值）
            use_local_interpolation: 是否启用局部插值（默认True）

        Returns:
            CoordinateTransform: 计算得到的变换矩阵
        """
        if len(points) < 3:
            raise ValueError("至少需要3个校准点来计算变换矩阵")

        # 导入坐标变换模块
        try:
            from .coordinate_transform import calculate_affine_transform
            return calculate_affine_transform(points, player_pos, use_local_interpolation)
        except ImportError:
            # 如果numpy不可用，使用简化变换
            print("警告: numpy不可用，使用简化的坐标变换")
            return CoordinateTransform()


@dataclass
class MapViewState:
    """
    地图视图状态

    用于保存和恢复地图视图的缩放、平移状态
    """
    map_id: str
    layer_id: int
    zoom: float = 1.0  # 缩放比例
    offset_x: float = 0.0  # 平移偏移X
    offset_y: float = 0.0  # 平移偏移Y
    center_on_player: bool = True  # 是否将玩家置于中心
    show_rotation: bool = True  # 是否显示旋转方向


@dataclass
class FloatingMapConfig:
    """
    浮动小地图配置

    保存浮动窗口的位置、大小、透明度等设置
    """
    enabled: bool = False
    width: int = 400
    height: int = 400
    pos_x: int = 100
    pos_y: int = 100
    opacity: float = 0.8  # 透明度 (0.0 - 1.0)
    locked: bool = False  # 是否锁定（鼠标穿透）
    always_on_top: bool = True  # 是否置顶
    hotkey: str = "F5"  # 开关快捷键
    zoom: float = 1.0
    center_on_player: bool = True
