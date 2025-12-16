"""
Local Map Module - Coordinate Transform

坐标变换算法实现，支持：
- 普通最小二乘法（3个点）
- 加权最小二乘法（多点优化）
- RANSAC鲁棒算法（处理异常点）
"""

import numpy as np
from typing import List, Tuple, Optional
from .models import CalibrationPoint, Position3D, CoordinateTransform
import random


def calculate_affine_transform(
    points: List[CalibrationPoint],
    player_pos: Optional[Position3D] = None,
    use_local_interpolation: bool = True
) -> CoordinateTransform:
    """
    从校准点计算仿射变换矩阵（智能选择算法）

    根据点的数量和是否提供玩家位置自动选择最佳算法：
    - 有玩家位置 + 启用局部插值 → 局部插值（最近3-4点）
    - 3个点：普通最小二乘法
    - 4-6个点：加权最小二乘法
    - 7个点以上：RANSAC + 加权最小二乘法（鲁棒）

    Args:
        points: 校准点列表（至少3个）
        player_pos: 玩家当前位置（可选，用于局部插值）
        use_local_interpolation: 是否启用局部插值（默认True）

    Returns:
        CoordinateTransform: 变换矩阵

    Raises:
        ValueError: 如果校准点少于3个
    """
    if len(points) < 3:
        raise ValueError("至少需要3个校准点来计算变换矩阵")

    n = len(points)

    # 优先使用局部插值（如果提供了玩家位置）
    if player_pos is not None and use_local_interpolation and n >= 3:
        print(f"算法选择: 局部插值（总共 {n} 个校准点）")
        return _calculate_local_interpolation(points, player_pos)

    # 回退到原有算法
    print(f"算法选择: 传统方法（{n} 个点）")
    if n <= 3:
        return _calculate_basic_transform(points)
    elif n <= 6:
        return _calculate_weighted_transform(points)
    else:
        return _calculate_ransac_transform(points)


def _calculate_basic_transform(points: List[CalibrationPoint]) -> CoordinateTransform:
    """
    基础最小二乘法（3-6个点）

    使用最小二乘法拟合2D仿射变换：
    map_x = a * game_x + b * game_z + c
    map_y = d * game_x + e * game_z + f
    """
    n = len(points)

    # 提取游戏坐标和地图坐标
    game_x = np.array([p.game_pos.x for p in points])
    game_z = np.array([p.game_pos.z for p in points])
    map_x = np.array([p.map_x for p in points])
    map_y = np.array([p.map_y for p in points])

    # 构建最小二乘法的系数矩阵 A
    # [game_x, game_z, 1]
    A = np.column_stack([game_x, game_z, np.ones(n)])

    # 求解 map_x 方向的变换系数: [a, b, c]
    coeffs_x, residuals_x, rank_x, s_x = np.linalg.lstsq(A, map_x, rcond=None)
    a, b, c = coeffs_x

    # 求解 map_y 方向的变换系数: [d, e, f]
    coeffs_y, residuals_y, rank_y, s_y = np.linalg.lstsq(A, map_y, rcond=None)
    d, e, f = coeffs_y

    # 从仿射矩阵参数提取几何变换参数（仅用于显示）
    scale_x = np.sqrt(a**2 + d**2)
    scale_z = np.sqrt(b**2 + e**2)
    rotation = np.arctan2(d, a)

    # 创建变换对象（包含完整的仿射系数）
    transform = CoordinateTransform(
        a=a, b=b, c=c,
        d=d, e=e, f=f,
        scale_x=scale_x,
        scale_z=scale_z,
        offset_x=c,
        offset_z=f,
        rotation=rotation
    )

    return transform


def _calculate_weighted_transform(points: List[CalibrationPoint]) -> CoordinateTransform:
    """
    加权最小二乘法（7-15个点）

    对离中心较远的点给予较低权重，减少边缘点误差的影响
    """
    n = len(points)

    # 提取坐标
    game_x = np.array([p.game_pos.x for p in points])
    game_z = np.array([p.game_pos.z for p in points])
    map_x = np.array([p.map_x for p in points])
    map_y = np.array([p.map_y for p in points])

    # 计算点的中心
    center_game_x = np.mean(game_x)
    center_game_z = np.mean(game_z)

    # 计算每个点到中心的距离
    distances = np.sqrt((game_x - center_game_x)**2 + (game_z - center_game_z)**2)
    max_distance = np.max(distances) if np.max(distances) > 0 else 1.0

    # 计算权重：距离越近权重越大（使用高斯衰减）
    # 中心点权重=1.0，最远点权重≈0.5
    weights = np.exp(-0.5 * (distances / max_distance)**2)

    # 构建加权矩阵 W
    W = np.diag(weights)

    # 构建系数矩阵 A
    A = np.column_stack([game_x, game_z, np.ones(n)])

    # 加权最小二乘: (A^T * W * A) * x = A^T * W * b
    # 求解 map_x 方向
    AWA_x = A.T @ W @ A
    AWb_x = A.T @ W @ map_x
    coeffs_x = np.linalg.solve(AWA_x, AWb_x)
    a, b, c = coeffs_x

    # 求解 map_y 方向
    AWb_y = A.T @ W @ map_y
    coeffs_y = np.linalg.solve(AWA_x, AWb_y)
    d, e, f = coeffs_y

    # 提取几何参数（仅用于显示）
    scale_x = np.sqrt(a**2 + d**2)
    scale_z = np.sqrt(b**2 + e**2)
    rotation = np.arctan2(d, a)

    transform = CoordinateTransform(
        a=a, b=b, c=c,
        d=d, e=e, f=f,
        scale_x=scale_x,
        scale_z=scale_z,
        offset_x=c,
        offset_z=f,
        rotation=rotation
    )

    return transform


def _calculate_ransac_transform(points: List[CalibrationPoint],
                                 max_iterations: int = 500,
                                 inlier_threshold: float = 10.0) -> CoordinateTransform:
    """
    RANSAC鲁棒算法（16个点以上）

    随机抽样一致性算法，能够自动识别和排除异常点（outliers）

    Args:
        points: 校准点列表
        max_iterations: 最大迭代次数
        inlier_threshold: 内点阈值（像素），小于此值认为是好点

    Returns:
        CoordinateTransform: 最佳变换矩阵
    """
    n = len(points)
    best_transform = None
    best_inliers = []
    best_score = 0

    print(f"  RANSAC参数: 最大迭代={max_iterations}, 内点阈值={inlier_threshold}px")

    # RANSAC主循环
    for iteration in range(max_iterations):
        # 随机选择3个点（最少需要3个点来计算仿射变换）
        sample_indices = random.sample(range(n), 3)
        sample_points = [points[i] for i in sample_indices]

        try:
            # 用这3个点计算变换
            candidate_transform = _calculate_basic_transform(sample_points)

            # 计算所有点的误差
            inliers = []
            for i, point in enumerate(points):
                predicted_x, predicted_y = candidate_transform.transform(point.game_pos)
                error = np.sqrt((predicted_x - point.map_x)**2 +
                              (predicted_y - point.map_y)**2)

                if error < inlier_threshold:
                    inliers.append(i)

            # 评估这个模型的质量（内点数量）
            score = len(inliers)

            # 更新最佳模型
            if score > best_score:
                best_score = score
                best_inliers = inliers
                best_transform = candidate_transform

        except Exception as e:
            continue

    # 使用所有内点重新计算变换（提高精度）
    if best_inliers and len(best_inliers) >= 3:
        inlier_points = [points[i] for i in best_inliers]

        print(f"  RANSAC结果: {len(best_inliers)}/{n} 个内点")

        # 根据内点数量选择算法
        if len(inlier_points) <= 6:
            final_transform = _calculate_basic_transform(inlier_points)
        else:
            final_transform = _calculate_weighted_transform(inlier_points)

        return final_transform
    else:
        # RANSAC失败，回退到加权最小二乘
        return _calculate_weighted_transform(points)


def calculate_simple_transform(points: List[CalibrationPoint]) -> CoordinateTransform:
    """
    计算简化的坐标变换（仅缩放和平移，不考虑旋转）

    适用于地图方向已经对齐的情况

    Args:
        points: 校准点列表（至少2个）

    Returns:
        CoordinateTransform: 变换矩阵
    """
    if len(points) < 2:
        raise ValueError("至少需要2个校准点")

    # 计算游戏坐标和地图坐标的范围
    game_x_vals = [p.game_pos.x for p in points]
    game_z_vals = [p.game_pos.z for p in points]
    map_x_vals = [p.map_x for p in points]
    map_y_vals = [p.map_y for p in points]

    game_x_range = max(game_x_vals) - min(game_x_vals)
    game_z_range = max(game_z_vals) - min(game_z_vals)
    map_x_range = max(map_x_vals) - min(map_x_vals)
    map_y_range = max(map_y_vals) - min(map_y_vals)

    # 计算缩放比例
    if game_x_range > 0:
        scale_x = map_x_range / game_x_range
    else:
        scale_x = 1.0

    if game_z_range > 0:
        scale_z = map_y_range / game_z_range
    else:
        scale_z = 1.0

    # 计算偏移（使用第一个点）
    first_point = points[0]
    offset_x = first_point.map_x - first_point.game_pos.x * scale_x
    offset_z = first_point.map_y - first_point.game_pos.z * scale_z

    # 简化变换：无旋转
    # map_x = scale_x * game_x + offset_x
    # map_y = scale_z * game_z + offset_z
    return CoordinateTransform(
        a=scale_x, b=0.0, c=offset_x,
        d=0.0, e=scale_z, f=offset_z,
        scale_x=scale_x,
        scale_z=scale_z,
        offset_x=offset_x,
        offset_z=offset_z,
        rotation=0.0
    )


def validate_transform(transform: CoordinateTransform, points: List[CalibrationPoint]) -> Tuple[float, List[Tuple[float, float]]]:
    """
    验证变换矩阵的准确性

    Args:
        transform: 要验证的变换矩阵
        points: 校准点列表

    Returns:
        (avg_error, errors): 平均误差和每个点的误差列表
    """
    errors = []

    for point in points:
        # 使用变换矩阵计算预测的地图坐标
        predicted_x, predicted_y = transform.transform(point.game_pos)

        # 计算与实际标注点的误差
        error_x = predicted_x - point.map_x
        error_y = predicted_y - point.map_y
        error = np.sqrt(error_x**2 + error_y**2)

        errors.append((error_x, error_y))

    # 计算平均误差
    avg_error = np.mean([np.sqrt(ex**2 + ey**2) for ex, ey in errors])

    return avg_error, errors


# 更新models.py中的calculate_from_points方法
def update_coordinate_transform_model():
    """
    这个函数用于更新models.py中CoordinateTransform.calculate_from_points()方法的实现

    实际使用时，应该直接修改models.py文件
    """
    implementation = '''
    @staticmethod
    def calculate_from_points(points: List[CalibrationPoint]) -> 'CoordinateTransform':
        """
        从校准点计算变换矩阵

        使用最小二乘法拟合仿射变换
        需要至少3个点

        Args:
            points: 校准点列表

        Returns:
            CoordinateTransform: 计算得到的变换矩阵
        """
        from .coordinate_transform import calculate_affine_transform
        return calculate_affine_transform(points)
    '''
    return implementation


# 测试代码
if __name__ == "__main__":
    # 测试仿射变换计算
    from datetime import datetime

    # 创建测试校准点
    test_points = [
        CalibrationPoint(
            game_pos=Position3D(x=100.0, y=0.0, z=200.0),
            map_x=500.0,
            map_y=300.0,
            timestamp=datetime.now()
        ),
        CalibrationPoint(
            game_pos=Position3D(x=150.0, y=0.0, z=250.0),
            map_x=600.0,
            map_y=400.0,
            timestamp=datetime.now()
        ),
        CalibrationPoint(
            game_pos=Position3D(x=200.0, y=0.0, z=200.0),
            map_x=700.0,
            map_y=300.0,
            timestamp=datetime.now()
        ),
    ]

    print("测试校准点:")
    for i, point in enumerate(test_points, 1):
        print(f"  点{i}: 游戏{point.game_pos} -> 地图({point.map_x}, {point.map_y})")

    # 计算变换矩阵
    print("\n计算仿射变换矩阵...")
    transform = calculate_affine_transform(test_points)

    # 验证变换
    print("\n验证变换准确性...")
    avg_error, errors = validate_transform(transform, test_points)
    print(f"平均误差: {avg_error:.2f} 像素")

    for i, (ex, ey) in enumerate(errors, 1):
        print(f"  点{i} 误差: X={ex:.2f}, Y={ey:.2f} 像素")

    # 测试变换
    print("\n测试新位置变换:")
    test_pos = Position3D(x=125.0, y=0.0, z=225.0)
    map_x, map_y = transform.transform(test_pos)
    print(f"  游戏坐标 {test_pos} -> 地图坐标 ({map_x:.1f}, {map_y:.1f})")


# ==================== 局部插值定位算法 ====================

def _calculate_2d_distance(pos1: Position3D, pos2: Position3D) -> float:
    """
    计算两点的 2D 水平距离（忽略 Y 轴高度）

    使用 X, Z 坐标计算欧氏距离

    Args:
        pos1: 第一个位置
        pos2: 第二个位置

    Returns:
        float: 2D 距离（游戏单位）
    """
    dx = pos1.x - pos2.x
    dz = pos1.z - pos2.z
    return np.sqrt(dx**2 + dz**2)


def _is_inside_triangle_2d(point: Position3D, triangle: List[Position3D]) -> bool:
    """
    判断点是否在三角形内（2D，使用重心坐标法）

    重心坐标法: 点P在三角形ABC内 ⟺ 重心坐标 (u,v,w) 都 >= 0

    Args:
        point: 待检测点
        triangle: 三角形的3个顶点

    Returns:
        bool: 是否在三角形内
    """
    if len(triangle) != 3:
        return False

    # 提取 2D 坐标 (x, z)
    p = np.array([point.x, point.z])
    a = np.array([triangle[0].x, triangle[0].z])
    b = np.array([triangle[1].x, triangle[1].z])
    c = np.array([triangle[2].x, triangle[2].z])

    # 计算向量
    v0 = c - a
    v1 = b - a
    v2 = p - a

    # 计算点积
    dot00 = np.dot(v0, v0)
    dot01 = np.dot(v0, v1)
    dot02 = np.dot(v0, v2)
    dot11 = np.dot(v1, v1)
    dot12 = np.dot(v1, v2)

    # 计算重心坐标
    denom = dot00 * dot11 - dot01 * dot01
    if abs(denom) < 1e-10:  # 退化三角形
        return False

    inv_denom = 1.0 / denom
    u = (dot11 * dot02 - dot01 * dot12) * inv_denom
    v = (dot00 * dot12 - dot01 * dot02) * inv_denom

    # 检查点是否在三角形内
    return (u >= 0) and (v >= 0) and (u + v <= 1)


def _calculate_local_interpolation(
    points: List[CalibrationPoint],
    player_pos: Position3D,
    k: int = 4,
    max_distance_threshold: float = 1000.0
) -> CoordinateTransform:
    """
    局部插值算法 - 基于最近的 k 个校准点计算变换

    选择距离玩家最近的几个校准点进行插值,比全局拟合更适合局部地图。

    Args:
        points: 所有校准点（至少3个）
        player_pos: 玩家当前游戏坐标
        k: 选择最近的 k 个点（默认4）
        max_distance_threshold: 距离阈值（游戏单位），超出警告

    Returns:
        CoordinateTransform: 基于局部点的变换矩阵

    算法流程:
    1. 计算玩家到每个校准点的 2D 距离（忽略 Y 轴）
    2. 选择距离最近的 min(k, len(points)) 个点
    3. 检查最近点的距离，如果过远则警告
    4. （可选）检测是否在凸包内
    5. 使用这些点调用 _calculate_basic_transform()
    """
    n = len(points)
    if n < 3:
        raise ValueError("局部插值至少需要3个校准点")

    # 1. 计算 2D 距离（使用 x, z 坐标）
    distances = []
    for point in points:
        dist = _calculate_2d_distance(player_pos, point.game_pos)
        distances.append((dist, point))

    # 2. 按距离排序，选择最近的 k 个点
    distances.sort(key=lambda x: x[0])
    k_actual = min(k, n)
    nearest_points = [point for _, point in distances[:k_actual]]
    nearest_distances = [dist for dist, _ in distances[:k_actual]]

    # 3. 距离检查（警告但不阻止）
    max_dist = nearest_distances[-1]
    if max_dist > max_distance_threshold:
        print(f"  警告: 最远的校准点距离 {max_dist:.1f} 游戏单位，超出阈值 {max_distance_threshold}")

    # 4. 日志输出
    print(f"  局部插值: 使用最近 {k_actual}/{n} 个校准点")
    print(f"    距离范围: {nearest_distances[0]:.1f} ~ {max_dist:.1f} 游戏单位")

    # 5. 包围检测（简化版：只检测3个点的三角形）
    if k_actual >= 3:
        is_inside = _is_inside_triangle_2d(
            player_pos,
            [p.game_pos for p in nearest_points[:3]]
        )
        if is_inside:
            print(f"    ✓ 玩家位于校准点凸包内（最优）")
        else:
            print(f"    ⚠ 玩家位于校准点凸包外（次优，但可接受）")

    # 6. 使用基础最小二乘法计算变换
    return _calculate_basic_transform(nearest_points)
