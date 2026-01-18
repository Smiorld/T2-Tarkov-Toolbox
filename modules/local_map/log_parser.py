"""
Local Map Module - Log Parser

解析塔科夫日志文件，提取战局信息和服务器IP
"""

import re
from datetime import datetime
from typing import Optional, List
from .models import RaidInfo
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class LogDirectoryWatcher(FileSystemEventHandler):
    """
    监控日志目录，检测新的 application.log 文件创建

    当游戏重启时，会创建新的 log_YYYY.MM.DD_H-mm-ss/ 目录，
    并在其中生成新的 application.log 文件。

    此类监听这些文件创建事件，立即通知 LogMonitor 切换。
    """

    def __init__(self, on_new_log_file):
        """
        Args:
            on_new_log_file: 回调函数 (new_log_path: str) -> None
        """
        super().__init__()
        self.on_new_log_file = on_new_log_file

    def on_created(self, event):
        """文件创建事件处理"""
        import os
        if event.is_directory:
            return

        # 检测 application.log 或 application_000.log 等
        filename = os.path.basename(event.src_path)
        if "application" in filename and filename.endswith(".log"):
            print(f"[LogDirectoryWatcher] 检测到新日志文件: {event.src_path}")
            self.on_new_log_file(event.src_path)


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
        "terminal_preset": "Terminal",
        "woods_preset": "Woods",
    }

    def __init__(self):
        self.current_raid: Optional[RaidInfo] = None

    def parse_line(self, line: str) -> tuple[Optional[str], Optional[RaidInfo]]:
        """
        解析日志行

        Args:
            line: 日志文件的一行

        Returns:
            tuple: (event_type, raid_info)
                event_type: "map_loading" | "raid_started" | None
                raid_info: RaidInfo 对象或 None
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
                    # 触发地图加载事件
                    return ("map_loading", self.current_raid)

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
            # 触发战局开始事件
            raid_info = self.current_raid
            return ("raid_started", raid_info)

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

        return (None, None)

    def get_current_raid(self) -> Optional[RaidInfo]:
        """获取当前正在进行的战局信息"""
        return self.current_raid


class LogMonitor:
    """
    日志文件监控器

    持续监控塔科夫日志文件，实时解析新增内容
    """

    def __init__(self, log_file_path: str, on_raid_start=None, on_raid_end=None,
                 on_map_loading=None, start_from_end=True, on_log_switch=None):
        """
        初始化日志监控器

        Args:
            log_file_path: 日志文件路径
            on_raid_start: 战局开始回调函数 (raid_info: RaidInfo) -> None
            on_raid_end: 战局结束回调函数 (raid_info: RaidInfo) -> None
            on_map_loading: 地图加载回调函数 (raid_info: RaidInfo) -> None
            start_from_end: 是否从文件末尾开始监控（跳过现有内容），默认True
            on_log_switch: 日志文件切换回调函数 (new_log_path: str) -> None
        """
        self.log_file_path = log_file_path
        self.parser = LogParser()
        self.on_raid_start = on_raid_start
        self.on_raid_end = on_raid_end
        self.on_map_loading = on_map_loading
        self.on_log_switch = on_log_switch
        self.start_from_end = start_from_end
        self.last_position = 0
        self.is_running = False
        self.logs_base_dir = None  # Will be set to the parent Logs directory
        self.current_log_dir = None  # Current log subdirectory being monitored
        self.last_dir_check_time = 0  # 移到实例属性，用于轮询备用检查
        self.fs_observer = None  # FileSystemWatcher observer
        self.dir_watcher = None  # Event handler

    def _get_latest_log_dir(self, logs_base_dir):
        """
        获取最新的日志目录（按文件夹名称中的时间戳）

        Returns:
            最新日志目录的完整路径，如果没有找到则返回None
        """
        import os
        import re
        from datetime import datetime

        if not os.path.exists(logs_base_dir):
            return None

        log_folders = [
            f for f in os.listdir(logs_base_dir)
            if os.path.isdir(os.path.join(logs_base_dir, f)) and f.startswith("log_")
        ]

        if not log_folders:
            return None

        # Parse timestamps and find the latest
        latest_folder = None
        latest_date = None

        for folder in log_folders:
            # Format: log_YYYY.MM.DD_H-mm-ss (H can be 1 or 2 digits)
            match = re.match(r'log_(\d{4})\.(\d{2})\.(\d{2})_(\d{1,2})-(\d{2})-(\d{2})', folder)
            if match:
                try:
                    year, month, day, hour, minute, second = map(int, match.groups())
                    folder_date = datetime(year, month, day, hour, minute, second)
                    if latest_date is None or folder_date > latest_date:
                        latest_date = folder_date
                        latest_folder = folder
                except ValueError:
                    continue

        # 备选方案：如果时间戳解析全部失败，返回最后一个目录
        if latest_folder is None and log_folders:
            latest_folder = sorted(log_folders)[-1]  # 按字母排序取最后一个
            print(f"[LogMonitor] 警告：时间戳解析失败，使用备选方案选择目录: {latest_folder}")

        if latest_folder:
            return os.path.join(logs_base_dir, latest_folder)
        return None

    def _on_new_log_file_detected(self, new_log_path: str):
        """
        当 FileSystemWatcher 检测到新的日志文件创建时调用

        这是事件驱动的切换机制，延迟 < 100ms
        """
        import os
        new_log_dir = os.path.dirname(new_log_path)

        # 检查是否真的是新目录
        if new_log_dir == self.current_log_dir:
            print(f"[LogMonitor] 忽略同目录内的文件: {new_log_path}")
            return

        print(f"[LogMonitor] 游戏重启！新日志目录: {new_log_dir}")

        # 立即切换
        self.log_file_path = new_log_path
        self.current_log_dir = new_log_dir

        # 根据 start_from_end 设置决定起始位置
        if self.start_from_end:
            try:
                with open(new_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0, 2)  # 跳到末尾
                    self.last_position = f.tell()
                    print(f"[LogMonitor] 跳过现有内容，从位置 {self.last_position} 开始")
            except Exception as e:
                print(f"[LogMonitor] 定位文件末尾失败: {e}，从头读取")
                self.last_position = 0
        else:
            self.last_position = 0

        # 触发回调通知 UI
        if self.on_log_switch:
            self.on_log_switch(new_log_path)

    def start(self):
        """开始监控日志文件"""
        import threading
        import time
        import os

        # Initialize directory tracking
        if os.path.exists(self.log_file_path):
            self.current_log_dir = os.path.dirname(self.log_file_path)
            # Get the Logs base directory (parent of log_YYYY.MM.DD_H-mm-ss)
            self.logs_base_dir = os.path.dirname(self.current_log_dir)
            print(f"[LogMonitor] 基础日志目录: {self.logs_base_dir}")
            print(f"[LogMonitor] 当前日志子目录: {self.current_log_dir}")

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

        # 启动文件系统监控（事件驱动的日志切换）
        if self.logs_base_dir:
            try:
                self.dir_watcher = LogDirectoryWatcher(
                    on_new_log_file=self._on_new_log_file_detected
                )
                self.fs_observer = Observer()
                # 递归监控 Logs/ 目录及其子目录
                self.fs_observer.schedule(self.dir_watcher, self.logs_base_dir, recursive=True)
                self.fs_observer.start()
                print(f"[LogMonitor] 启动文件系统监控: {self.logs_base_dir}")
            except Exception as e:
                print(f"[LogMonitor] 启动文件系统监控失败: {e}，将使用轮询备用方案")
                self.fs_observer = None

        self.is_running = True

        def monitor_loop():

            while self.is_running:
                try:
                    # Fallback: Periodically check for new log directories (every 60 seconds)
                    # 主要依赖 FileSystemWatcher，这只是备用方案
                    current_time = time.time()
                    if self.logs_base_dir and (current_time - self.last_dir_check_time) >= 60:
                        latest_log_dir = self._get_latest_log_dir(self.logs_base_dir)
                        if latest_log_dir and latest_log_dir != self.current_log_dir:
                            print(f"[LogMonitor] 备用检查：检测到新的日志目录: {latest_log_dir}")
                            # Switch to new log directory
                            new_log_file = os.path.join(latest_log_dir, os.path.basename(self.log_file_path))
                            if os.path.exists(new_log_file):
                                print(f"[LogMonitor] 切换到新日志文件: {new_log_file}")
                                self.log_file_path = new_log_file
                                self.current_log_dir = latest_log_dir
                                self.last_position = 0  # Start from beginning of new file

                                # Notify callback if registered
                                if self.on_log_switch:
                                    self.on_log_switch(new_log_file)

                        self.last_dir_check_time = current_time

                    # Read new log lines
                    with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # 跳转到上次读取的位置
                        f.seek(self.last_position)

                        # 读取新增的行
                        new_lines = f.readlines()
                        if new_lines:
                            for line in new_lines:
                                event_type, raid_info = self.parser.parse_line(line.strip())

                                # 处理地图加载事件
                                if event_type == "map_loading" and raid_info and self.on_map_loading:
                                    self.on_map_loading(raid_info)
                                # 处理战局开始事件
                                elif event_type == "raid_started" and raid_info and self.on_raid_start:
                                    self.on_raid_start(raid_info)

                        # 更新位置
                        self.last_position = f.tell()

                except FileNotFoundError:
                    print(f"[LogMonitor] 日志文件不存在: {self.log_file_path}")

                    # 立即尝试恢复：查找最新日志目录
                    if self.logs_base_dir:
                        latest_log_dir = self._get_latest_log_dir(self.logs_base_dir)
                        if latest_log_dir and latest_log_dir != self.current_log_dir:
                            # 查找新目录中的 application.log
                            import glob
                            log_files = glob.glob(os.path.join(latest_log_dir, "*application*.log"))
                            if log_files:
                                new_log_file = max(log_files, key=os.path.getmtime)  # 最新的
                                print(f"[LogMonitor] 恢复：切换到新日志文件 {new_log_file}")
                                self.log_file_path = new_log_file
                                self.current_log_dir = latest_log_dir
                                self.last_position = 0
                                if self.on_log_switch:
                                    self.on_log_switch(new_log_file)
                                continue  # 立即重试，不睡眠

                except Exception as e:
                    print(f"[LogMonitor] 监控日志文件时发生错误: {e}")
                    import traceback
                    traceback.print_exc()  # 打印详细堆栈，便于调试

                # 等待5秒后再次检查
                time.sleep(5)

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def stop(self):
        """停止监控"""
        self.is_running = False

        # 停止文件系统监控
        if hasattr(self, 'fs_observer') and self.fs_observer:
            try:
                self.fs_observer.stop()
                self.fs_observer.join(timeout=5)
                print("[LogMonitor] 文件系统监控已停止")
            except Exception as e:
                print(f"[LogMonitor] 停止文件系统监控时发生错误: {e}")


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
