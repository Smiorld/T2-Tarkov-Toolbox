"""
Version checker for T2 Tarkov Toolbox
Checks GitHub releases for new versions with caching and rate limiting
"""

import requests
import threading
import time
from typing import Optional, Callable, Tuple
from packaging import version
from utils.global_config import get_global_config
from version import __version__


class VersionChecker:
    """Version checker singleton - manages GitHub release checks with caching"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.current_version = __version__  # Unified version from version.py
        self.github_api_url = "https://api.github.com/repos/Smiorld/T2-Tarkov-Toolbox/releases/latest"
        self.github_releases_url = "https://github.com/Smiorld/T2-Tarkov-Toolbox/releases"

        self.global_config = get_global_config()

        # Cache settings - check at most once per day
        self.cache_duration = 24 * 60 * 60  # 24 hours in seconds

        # Thread management
        self._check_thread: Optional[threading.Thread] = None
        self._is_checking = False

        self._initialized = True
        print("[VersionChecker] Initialized")

    def _get_last_check_time(self) -> int:
        """Get timestamp of last version check from config"""
        return self.global_config.get('version_check_last_time', 0)

    def _set_last_check_time(self, timestamp: int):
        """Save timestamp of version check to config"""
        self.global_config.set('version_check_last_time', timestamp)

    def _get_cached_latest_version(self) -> Optional[str]:
        """Get cached latest version from config"""
        return self.global_config.get('version_check_cached_version', None)

    def _set_cached_latest_version(self, ver: str):
        """Save latest version to config cache"""
        self.global_config.set('version_check_cached_version', ver)

    def should_check(self) -> bool:
        """Check if enough time has passed since last check (rate limiting)"""
        last_check = self._get_last_check_time()
        current_time = int(time.time())
        return (current_time - last_check) >= self.cache_duration

    def compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings using semantic versioning

        Args:
            v1: First version (e.g., "v1.0.2" or "1.0.2")
            v2: Second version

        Returns:
            1 if v1 > v2, -1 if v1 < v2, 0 if equal
        """
        try:
            # Strip 'v' prefix if present
            v1_clean = v1.lstrip('v')
            v2_clean = v2.lstrip('v')

            ver1 = version.parse(v1_clean)
            ver2 = version.parse(v2_clean)

            if ver1 > ver2:
                return 1
            elif ver1 < ver2:
                return -1
            else:
                return 0
        except Exception as e:
            print(f"[VersionChecker] Error comparing versions: {e}")
            # Fallback to string comparison
            if v1_clean > v2_clean:
                return 1
            elif v1_clean < v2_clean:
                return -1
            return 0

    def fetch_latest_version(self, timeout: int = 5) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Fetch latest version from GitHub API

        Args:
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success: bool, version: Optional[str], error_msg: Optional[str])
        """
        try:
            print(f"[VersionChecker] Fetching latest version from GitHub...")
            response = requests.get(
                self.github_api_url,
                timeout=timeout,
                headers={'Accept': 'application/vnd.github.v3+json'}
            )

            if response.status_code == 200:
                data = response.json()
                latest_version = data.get('tag_name', '').lstrip('v')

                if not latest_version:
                    return False, None, "Invalid response format"

                print(f"[VersionChecker] Latest version: {latest_version}")

                # Update cache
                self._set_cached_latest_version(latest_version)
                self._set_last_check_time(int(time.time()))

                return True, latest_version, None
            else:
                error_msg = f"HTTP {response.status_code}"
                print(f"[VersionChecker] Error: {error_msg}")
                return False, None, error_msg

        except requests.exceptions.Timeout:
            print("[VersionChecker] Request timeout")
            return False, None, "Request timeout"
        except requests.exceptions.ConnectionError:
            print("[VersionChecker] Network connection error")
            return False, None, "Network connection error"
        except requests.exceptions.RequestException as e:
            print(f"[VersionChecker] Request error: {e}")
            return False, None, f"Request error: {str(e)}"
        except Exception as e:
            print(f"[VersionChecker] Unexpected error: {e}")
            return False, None, f"Unexpected error: {str(e)}"

    def check_for_updates_async(self,
                                callback: Callable[[bool, Optional[str], Optional[str]], None],
                                force: bool = False):
        """
        Check for updates asynchronously in a background thread

        Args:
            callback: Function called with (success, latest_version, error_msg)
                     Will be called from background thread - use .after() for UI updates
            force: If True, bypass cache and force check
        """
        if self._is_checking:
            print("[VersionChecker] Check already in progress")
            return

        def check_thread():
            self._is_checking = True

            try:
                # Check cache first (unless forced)
                if not force and not self.should_check():
                    cached_version = self._get_cached_latest_version()
                    if cached_version:
                        print(f"[VersionChecker] Using cached version: {cached_version}")
                        callback(True, cached_version, None)
                        return

                # Fetch from GitHub
                success, latest_version, error_msg = self.fetch_latest_version()
                callback(success, latest_version, error_msg)

            except Exception as e:
                print(f"[VersionChecker] Exception in check thread: {e}")
                callback(False, None, f"Unexpected error: {str(e)}")
            finally:
                self._is_checking = False

        self._check_thread = threading.Thread(target=check_thread, daemon=True, name="VersionChecker")
        self._check_thread.start()
        print("[VersionChecker] Started background version check")

    def has_update_available(self, latest_version: str) -> bool:
        """Check if the latest version is newer than current"""
        if not latest_version:
            return False
        return self.compare_versions(latest_version, self.current_version) > 0

    def get_releases_url(self) -> str:
        """Get the GitHub releases page URL"""
        return self.github_releases_url


# Global singleton getter
_version_checker = None

def get_version_checker() -> VersionChecker:
    """Get version checker singleton instance"""
    global _version_checker
    if _version_checker is None:
        _version_checker = VersionChecker()
    return _version_checker
