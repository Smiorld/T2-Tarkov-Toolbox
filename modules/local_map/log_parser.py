"""
Local Map Module - Log Parser

解析塔科夫日志文件，提取战局信息和服务器IP
"""

import re
from datetime import datetime
from typing import Optional, List
from .models import RaidInfo


class LogParser:
    """
    日志解析器

    参考TarkovMonitor的实现，解析塔科夫日志文件中的关键事件：
    1. 地图加载（LocationLoaded）
    2. 匹配完成（MatchingCompleted）
    3. 战局开始（GameStarted）
    4. 战局结束（UserMatchOver）
    5. 服务器IP信息
    """

    # 地图Bundle名称到游戏内地图ID的映射（参考TarkovMonitor）
    MAP_BUNDLES = {
        "city_preset": "TarkovStreets",
        "customs_preset": "bigmap",
        "factory_day_preset": "factory4_day",
        "factory_night_preset": "factory4_night",
        "laboratory_preset": "laboratory",
        "labyrinth_preset": "Labyrinth",
        "lighthouse_preset": "Lighthouse",
        "rezerv_base_preset": "RezervBase",
        "sandbox_preset": "Sandbox",
        "sandbox_high_preset": "Sandbox_high",
        "shopping_mall": "Interchange",
        "shoreline_preset": "Shoreline",
        "woods_preset": "Woods",
    }

    def __init__(self):
        self.current_raid: Optional[RaidInfo] = None

    def parse_line(self, line: str) -> Optional[RaidInfo]:
        """
        解析日志行

        Args:
            line: 日志文件的一行

        Returns:
            RaidInfo or None: 如果检测到战局开始，返回战局信息
        """
        # 检测地图加载
        if "scene preset path:maps/" in line:
            map_bundle_match = re.search(
                r'scene preset path:maps/(?P<mapBundleName>[a-zA-Z0-9_]+)\.bundle',
                line
            )
            if map_bundle_match:
                map_bundle = map_bundle_match.group('mapBundleName')
                print(f"[LogParser] 检测到地图Bundle: {map_bundle}")
                if map_bundle in self.MAP_BUNDLES:
                    map_id = self.MAP_BUNDLES[map_bundle]
                    print(f"[LogParser] 地图ID: {map_id}")
                    self.current_raid = RaidInfo(
                        raid_id="",  # 在后续的TRACE-NetworkGameCreate中获取
                        map_id=map_id,
                        is_online=False,
                        is_pmc=True
                    )

        # 检测匹配完成（获取队列时间）
        if "MatchingCompleted" in line and self.current_raid:
            queue_time_match = re.search(
                r'MatchingCompleted:[0-9.,]+ real:(?P<queueTime>[0-9.,]+)',
                line
            )
            if queue_time_match:
                queue_time_str = queue_time_match.group('queueTime').replace(',', '.')
                self.current_raid.queue_time = float(queue_time_str)

        # 检测网络游戏创建（获取战局ID、地图名称、模式）
        if "TRACE-NetworkGameCreate profileStatus" in line and self.current_raid:
            # 获取地图名称
            map_match = re.search(r'Location: (?P<map>[^,]+)', line)
            if map_match:
                self.current_raid.map_id = map_match.group('map')

            # 获取战局ID
            raid_id_match = re.search(r'shortId: (?P<raidId>[A-Z0-9]{6})', line)
            if raid_id_match:
                self.current_raid.raid_id = raid_id_match.group('raidId')
                print(f"[LogParser] 检测到RaidID: {self.current_raid.raid_id}")

            # 判断是否在线模式
            self.current_raid.is_online = "RaidMode: Online" in line

            # 判断是否PMC
            if "Pmc" in line:
                self.current_raid.is_pmc = True
            elif "Savage" in line:
                self.current_raid.is_pmc = False

        # 检测战局开始
        if "GameStarted" in line and self.current_raid:
            self.current_raid.start_time = datetime.now()
            print(f"[LogParser] ========== 战局开始 ==========")
            print(f"[LogParser]   地图: {self.current_raid.map_id}")
            print(f"[LogParser]   RaidID: {self.current_raid.raid_id}")
            print(f"[LogParser]   模式: {'在线' if self.current_raid.is_online else '离线'} / {'PMC' if self.current_raid.is_pmc else 'Scav'}")
            print(f"[LogParser] ==============================")
            # 返回战局信息，表示新战局开始
            raid_info = self.current_raid
            return raid_info

        # 检测战局结束
        if "UserMatchOver" in line and self.current_raid:
            self.current_raid.end_time = datetime.now()
            self.current_raid = None  # 重置当前战局

        # 检测服务器IP（可能在不同的日志格式中）
        # 注意：需要根据实际的日志格式调整正则表达式
        if self.current_raid and not self.current_raid.server_ip:
            # 尝试多种可能的IP格式
            ip_patterns = [
                r'(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',  # 标准IPv4格式
                r'Server: (?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
                r'Connect to (?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
                r'EndPoint: (?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
            ]

            for pattern in ip_patterns:
                ip_match = re.search(pattern, line)
                if ip_match:
                    ip = ip_match.group('ip')
                    # 排除本地IP
                    if not ip.startswith('127.') and not ip.startswith('192.168.'):
                        self.current_raid.server_ip = ip
                        break

        return None

    def get_current_raid(self) -> Optional[RaidInfo]:
        """获取当前正在进行的战局信息"""
        return self.current_raid


class LogMonitor:
    """
    日志文件监控器

    持续监控塔科夫日志文件，实时解析新增内容
    """

    def __init__(self, log_file_path: str, on_raid_start=None, on_raid_end=None, start_from_end=True):
        """
        初始化日志监控器

        Args:
            log_file_path: 日志文件路径
            on_raid_start: 战局开始回调函数 (raid_info: RaidInfo) -> None
            on_raid_end: 战局结束回调函数 (raid_info: RaidInfo) -> None
            start_from_end: 是否从文件末尾开始监控（跳过现有内容），默认True
        """
        self.log_file_path = log_file_path
        self.parser = LogParser()
        self.on_raid_start = on_raid_start
        self.on_raid_end = on_raid_end
        self.start_from_end = start_from_end
        self.last_position = 0
        self.is_running = False

    def start(self):
        """开始监控日志文件"""
        import threading
        import time

        # 如果设置了从末尾开始，则跳过现有内容
        if self.start_from_end:
            try:
                with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0, 2)  # 跳转到文件末尾 (0 offset from SEEK_END)
                    self.last_position = f.tell()
                    print(f"[LogMonitor] 跳过现有日志内容，从位置 {self.last_position} 开始监控")
            except FileNotFoundError:
                print(f"[LogMonitor] 日志文件不存在: {self.log_file_path}，将在文件创建后开始监控")
                self.last_position = 0
            except Exception as e:
                print(f"[LogMonitor] 初始化文件位置时发生错误: {e}，从头开始监控")
                self.last_position = 0

        self.is_running = True

        def monitor_loop():
            while self.is_running:
                try:
                    with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # 跳转到上次读取的位置
                        f.seek(self.last_position)

                        # 读取新增的行
                        new_lines = f.readlines()
                        if new_lines:
                            for line in new_lines:
                                raid_info = self.parser.parse_line(line.strip())
                                if raid_info and self.on_raid_start:
                                    self.on_raid_start(raid_info)

                        # 更新位置
                        self.last_position = f.tell()

                except FileNotFoundError:
                    print(f"日志文件不存在: {self.log_file_path}")
                except Exception as e:
                    print(f"监控日志文件时发生错误: {e}")

                # 等待5秒后再次检查
                time.sleep(5)

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def stop(self):
        """停止监控"""
        self.is_running = False


# 测试代码
if __name__ == "__main__":
    # 测试日志解析
    parser = LogParser()

    test_lines = [
        "2024-12-05 14:30:00|  application|scene preset path:maps/customs_preset.bundle",
        "2024-12-05 14:30:15|  application|LocationLoaded:12.5 real:10.3",
        "2024-12-05 14:30:30|  application|MatchingCompleted:5.2 real:5.1",
        "2024-12-05 14:30:35|  application|TRACE-NetworkGameCreate profileStatus Location: bigmap, RaidMode: Online, shortId: ABC123",
        "2024-12-05 14:30:40|  application|GameStarted",
    ]

    for line in test_lines:
        raid_info = parser.parse_line(line)
        if raid_info:
            print(f"检测到战局开始:")
            print(f"  战局ID: {raid_info.raid_id}")
            print(f"  地图: {raid_info.map_id}")
            print(f"  在线模式: {raid_info.is_online}")
            print(f"  队列时间: {raid_info.queue_time}秒")
