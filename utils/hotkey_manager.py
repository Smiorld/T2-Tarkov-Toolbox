"""
Unified Global Hotkey Manager for T2 Tarkov Toolbox
Centralizes all keyboard monitoring into a single thread to avoid threading conflicts
"""

import keyboard
import threading
import time
from typing import Optional, Callable, Dict
from dataclasses import dataclass, field


@dataclass
class HotkeyBinding:
    """Represents a registered hotkey"""
    hotkey_id: str              # Unique ID (e.g., "screen_filter.preset.1")
    key: str                    # Key name (e.g., "1", "F1", "CTRL+S")
    callback: Callable[[], None]  # Function to call when pressed
    context: str = "global"     # "global" or tab name for context-awareness
    debounce: float = 0.2       # Debounce time in seconds
    last_triggered: float = 0.0  # Timestamp of last trigger


@dataclass
class AssignmentRequest:
    """Represents a hotkey assignment in progress"""
    requester_id: str                           # Module requesting assignment
    callback: Callable[[str], None]             # Callback with captured key
    conflict_check: Optional[Callable[[str], bool]] = None  # Check if key conflicts
    timeout: float = 10.0                       # Assignment timeout in seconds
    start_time: float = field(default_factory=time.time)  # Start timestamp


class HotkeyManager:
    """
    Unified global hotkey manager - Singleton
    Manages all application hotkeys in a single thread
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Registry data structures
        self._hotkey_registry: Dict[str, HotkeyBinding] = {}
        self._assignment_mode: Optional[AssignmentRequest] = None

        # Thread management
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Context management
        self._current_context = "global"

        # Polling configuration
        self.POLL_INTERVAL = 0.1  # 100ms polling
        self.DEBOUNCE_TIME = 0.2  # 200ms debounce

        self._initialized = True
        print("[HotkeyManager] Initialized")

    def start(self):
        """Start the hotkey monitoring thread"""
        if self._running:
            print("[HotkeyManager] Already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._hotkey_loop,
            daemon=True,
            name="HotkeyManager"
        )
        self._thread.start()
        print("[HotkeyManager] Started")

    def stop(self):
        """Stop the hotkey monitoring thread"""
        if not self._running:
            return

        print("[HotkeyManager] Stopping...")
        self._running = False

        # Wait for thread to finish (with timeout)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

            if self._thread.is_alive():
                print("[HotkeyManager] Warning: Thread did not stop cleanly")

        print("[HotkeyManager] Stopped")

    def register_hotkey(
        self,
        hotkey_id: str,
        key: str,
        callback: Callable[[], None],
        context: str = "global",
        debounce: float = 0.2
    ) -> bool:
        """
        Register a hotkey with the manager

        Args:
            hotkey_id: Unique identifier for this hotkey
            key: Key name (e.g., "1", "F1", "CTRL+S")
            callback: Function to call when hotkey is pressed
            context: Context where hotkey is active ("global" or tab name)
            debounce: Debounce time in seconds

        Returns:
            True if registration successful, False if key already registered
        """
        with self._lock:
            # Check if key is already registered (unless it's the same hotkey being updated)
            for existing_id, existing_binding in self._hotkey_registry.items():
                if existing_binding.key.upper() == key.upper() and existing_id != hotkey_id:
                    print(f"[HotkeyManager] Key '{key}' already registered to '{existing_id}'")
                    return False

            # Register the hotkey
            binding = HotkeyBinding(
                hotkey_id=hotkey_id,
                key=key.upper(),  # Normalize to uppercase
                callback=callback,
                context=context,
                debounce=debounce
            )

            self._hotkey_registry[hotkey_id] = binding
            print(f"[HotkeyManager] Registered: {hotkey_id} -> {key} (context: {context})")
            return True

    def unregister_hotkey(self, hotkey_id: str) -> bool:
        """
        Unregister a hotkey

        Args:
            hotkey_id: ID of the hotkey to unregister

        Returns:
            True if unregistered, False if not found
        """
        with self._lock:
            if hotkey_id in self._hotkey_registry:
                binding = self._hotkey_registry.pop(hotkey_id)
                print(f"[HotkeyManager] Unregistered: {hotkey_id} ({binding.key})")
                return True
            else:
                print(f"[HotkeyManager] Hotkey not found: {hotkey_id}")
                return False

    def update_hotkey_key(self, hotkey_id: str, new_key: str) -> bool:
        """
        Update the key for an existing hotkey

        Args:
            hotkey_id: ID of the hotkey to update
            new_key: New key name

        Returns:
            True if updated successfully
        """
        with self._lock:
            if hotkey_id not in self._hotkey_registry:
                print(f"[HotkeyManager] Hotkey not found: {hotkey_id}")
                return False

            binding = self._hotkey_registry[hotkey_id]
            old_key = binding.key
            binding.key = new_key.upper()
            print(f"[HotkeyManager] Updated: {hotkey_id} from {old_key} to {new_key}")
            return True

    def enter_assignment_mode(
        self,
        requester_id: str,
        callback: Callable[[str], None],
        conflict_check: Optional[Callable[[str], bool]] = None,
        timeout: float = 10.0
    ) -> bool:
        """
        Enter hotkey assignment mode to capture a new key

        Args:
            requester_id: ID of the module requesting assignment
            callback: Function to call with captured key name
            conflict_check: Optional function to check if key causes conflict
            timeout: Assignment timeout in seconds

        Returns:
            True if assignment mode entered, False if already in assignment mode
        """
        with self._lock:
            if self._assignment_mode is not None:
                print(f"[HotkeyManager] Already in assignment mode for {self._assignment_mode.requester_id}")
                return False

            self._assignment_mode = AssignmentRequest(
                requester_id=requester_id,
                callback=callback,
                conflict_check=conflict_check,
                timeout=timeout
            )

            print(f"[HotkeyManager] Entered assignment mode for {requester_id}")
            return True

    def cancel_assignment_mode(self) -> bool:
        """Cancel current assignment mode"""
        with self._lock:
            if self._assignment_mode is None:
                return False

            print(f"[HotkeyManager] Cancelled assignment mode for {self._assignment_mode.requester_id}")
            self._assignment_mode = None
            return True

    def set_active_context(self, context: str):
        """
        Set the active context for hotkeys

        Args:
            context: Context name ("global", "screen_filter", "local_map", etc.)
        """
        with self._lock:
            old_context = self._current_context
            self._current_context = context
            print(f"[HotkeyManager] Context changed: {old_context} -> {context}")

    def is_hotkey_registered(self, key: str) -> bool:
        """Check if a key is already registered"""
        with self._lock:
            key_upper = key.upper()
            return any(binding.key == key_upper for binding in self._hotkey_registry.values())

    def get_hotkey_by_id(self, hotkey_id: str) -> Optional[HotkeyBinding]:
        """Get hotkey binding by ID"""
        with self._lock:
            return self._hotkey_registry.get(hotkey_id)

    def _hotkey_loop(self):
        """Main polling loop - runs in dedicated thread"""
        print("[HotkeyManager] Hotkey loop started")

        while self._running:
            try:
                # Assignment mode takes priority
                if self._assignment_mode:
                    self._handle_assignment_mode()
                    continue

                # Normal detection mode
                active_hotkeys = self._get_active_hotkeys()

                current_time = time.time()

                for binding in active_hotkeys:
                    # Skip if still in debounce period
                    if current_time - binding.last_triggered < binding.debounce:
                        continue

                    # Check if key is pressed
                    try:
                        if keyboard.is_pressed(binding.key):
                            binding.last_triggered = current_time

                            # Call callback in separate thread to avoid blocking
                            threading.Thread(
                                target=self._safe_callback,
                                args=(binding.callback,),
                                daemon=True
                            ).start()

                            print(f"[HotkeyManager] Hotkey triggered: {binding.hotkey_id} ({binding.key})")

                    except Exception as e:
                        print(f"[HotkeyManager] Error checking key {binding.key}: {e}")
                        continue

                time.sleep(self.POLL_INTERVAL)

            except Exception as e:
                print(f"[HotkeyManager] Error in hotkey loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.5)

        print("[HotkeyManager] Hotkey loop stopped")

    def _handle_assignment_mode(self):
        """Handle key capture during assignment mode"""
        request = self._assignment_mode

        # Check timeout
        if time.time() - request.start_time > request.timeout:
            print(f"[HotkeyManager] Assignment mode timeout for {request.requester_id}")
            with self._lock:
                self._assignment_mode = None
            return

        try:
            # Read key event (blocking, but with short timeout via loop)
            event = keyboard.read_event(suppress=False)

            if event.event_type == keyboard.KEY_DOWN:
                key_name = event.name.upper()

                print(f"[HotkeyManager] Captured key: {key_name}")

                # Check for conflicts
                has_conflict = False
                if request.conflict_check:
                    has_conflict = request.conflict_check(key_name)

                if not has_conflict:
                    # Success - call callback with captured key
                    print(f"[HotkeyManager] Key '{key_name}' accepted for {request.requester_id}")

                    # Clear assignment mode first
                    with self._lock:
                        self._assignment_mode = None

                    # Call callback in separate thread
                    threading.Thread(
                        target=request.callback,
                        args=(key_name,),
                        daemon=True
                    ).start()

                    time.sleep(0.5)  # Debounce
                else:
                    print(f"[HotkeyManager] Key '{key_name}' conflicts for {request.requester_id}")
                    time.sleep(0.5)  # Debounce

        except Exception as e:
            print(f"[HotkeyManager] Error in assignment mode: {e}")
            time.sleep(0.1)

    def _get_active_hotkeys(self):
        """Get hotkeys active in current context"""
        with self._lock:
            active = []
            for binding in self._hotkey_registry.values():
                # Include global hotkeys and context-specific hotkeys
                if binding.context == "global" or binding.context == self._current_context:
                    active.append(binding)
            return active

    def _safe_callback(self, callback: Callable[[], None]):
        """Safely execute callback with exception handling"""
        try:
            callback()
        except Exception as e:
            print(f"[HotkeyManager] Callback error: {e}")
            import traceback
            traceback.print_exc()


# Global singleton getter
_hotkey_manager = None


def get_hotkey_manager() -> HotkeyManager:
    """Get hotkey manager singleton instance"""
    global _hotkey_manager
    if _hotkey_manager is None:
        _hotkey_manager = HotkeyManager()
    return _hotkey_manager
