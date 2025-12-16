"""
Local Map Module - Screenshot Parser

解析塔科夫截图文件名，提取位置和旋转信息
"""

import re
from datetime import datetime
from typing import Optional
from .models import Position3D, Rotation, PlayerPosition


class ScreenshotParser:
    """
    截图解析器

    塔科夫截图文件名格式示例：
    2024-12-05[14-32]_123.45, 67.89, -10.23_0.1234, 0.5678, 0.9012, 0.3456 (0).png

    格式说明：
    日期时间[HH-MM]_X, Y, Z_RX, RY, RZ, RW (序号).png

    其中：
    - 日期时间：YYYY-MM-DD[HH-MM]
    - X, Y, Z：游戏世界坐标（Y是高度）
    - RX, RY, RZ, RW：旋转四元数
    - 序号：如果同一秒内有多张截图，序号递增
    """

    # 正则表达式模式（参考TarkovMonitor）
    # 支持可变长度的小数位数和额外的时间戳字段
    PATTERN = re.compile(
        r'(?P<date>\d{4}-\d{2}-\d{2})\[(?P<time>\d{2}-\d{2})\]_?'
        r'(?P<x>-?\d+\.\d+), '
        r'(?P<y>-?\d+\.\d+), '
        r'(?P<z>-?\d+\.\d+)_?'
        r'(?P<rx>-?\d+\.\d+), '
        r'(?P<ry>-?\d+\.\d+), '
        r'(?P<rz>-?\d+\.\d+), '
        r'(?P<rw>-?\d+\.\d+)'
        r'(?:_(?P<extra>\d+\.\d+))? '  # Optional extra field
        r'\((?P<index>\d+)\)\.png'
    )

    @staticmethod
    def parse(filename: str, map_id: str) -> Optional[PlayerPosition]:
        """
        解析截图文件名

        Args:
            filename: 截图文件名（包含路径或仅文件名）
            map_id: 当前地图ID

        Returns:
            PlayerPosition or None: 解析成功返回玩家位置信息，失败返回None
        """
        # 提取文件名（去除路径）
        import os
        filename_only = os.path.basename(filename)

        match = ScreenshotParser.PATTERN.match(filename_only)
        if not match:
            print(f"截图文件名格式不匹配: {filename_only}")
            return None

        try:
            # 解析坐标
            position = Position3D(
                x=float(match.group('x')),
                y=float(match.group('y')),
                z=float(match.group('z'))
            )

            # 解析旋转四元数
            rotation = Rotation(
                x=float(match.group('rx')),
                y=float(match.group('ry')),
                z=float(match.group('rz')),
                w=float(match.group('rw'))
            )

            # 解析时间戳
            date_str = match.group('date')
            time_str = match.group('time').replace('-', ':')
            timestamp = datetime.strptime(
                f"{date_str} {time_str}",
                "%Y-%m-%d %H:%M"
            )

            return PlayerPosition(
                position=position,
                rotation=rotation,
                map_id=map_id,
                timestamp=timestamp,
                screenshot_filename=filename_only
            )

        except Exception as e:
            print(f"解析截图文件名失败: {filename_only}, 错误: {e}")
            return None

    @staticmethod
    def is_screenshot(filename: str) -> bool:
        """
        判断文件名是否为塔科夫截图

        Args:
            filename: 文件名

        Returns:
            bool: 是否为截图文件
        """
        import os
        filename_only = os.path.basename(filename)
        return bool(ScreenshotParser.PATTERN.match(filename_only))


# 测试代码
if __name__ == "__main__":
    # 测试截图解析
    test_filename = "2024-12-05[14-32]_123.45, 67.89, -10.23_0.1234, 0.5678, 0.9012, 0.3456 (0).png"

    result = ScreenshotParser.parse(test_filename, "bigmap")
    if result:
        print(f"解析成功:")
        print(f"  位置: {result.position}")
        print(f"  高度: {result.position.y}")
        print(f"  旋转Yaw: {result.rotation.to_yaw():.2f}°")
        print(f"  时间: {result.timestamp}")
        print(f"  地图: {result.map_id}")
    else:
        print("解析失败")
