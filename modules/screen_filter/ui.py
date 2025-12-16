import customtkinter as ctk
from tkinter import messagebox
import keyboard
import threading
import time
from typing import List

from modules.screen_filter.models import FilterConfig, FilterPreset
from modules.screen_filter.gamma_controller import GammaController
from modules.screen_filter.state_manager import ConfigManager
from modules.screen_filter.value_mapper import ValueMapper
from utils.i18n import t


class ScreenFilterUI(ctk.CTkFrame):
    """Screen Filter Tab UI Component"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        # Managers
        self.gamma_controller = GammaController()
        self.config_manager = ConfigManager()  # Unified config manager

        # State
        self.current_preset: FilterPreset = None
        self.selected_monitors: List[str] = []
        self.monitor_vars = {}  # device_name -> BooleanVar
        self.running = True
        self.validation_warning_label = None  # Will be created in main area
        self.waiting_for_hotkey = None  # Preset waiting for hotkey assignment
        self.get_overlay_window = None  # Callback to get overlay window reference

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_main_area()

        # Initialize
        self.refresh_monitors()
        self.load_presets_ui()

        # Select first preset if available
        presets = self.config_manager.get_all_presets()
        if presets:
            self.select_preset(presets[0])

        # Start Hotkey Listener
        self.hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self.hotkey_thread.start()

    def set_overlay_window_callback(self, callback):
        """
        设置获取悬浮窗引用的回调函数

        Args:
            callback: 返回OverlayMapWindow实例的回调函数
        """
        self.get_overlay_window = callback

    def _create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(2, weight=1)

        self.title_label = ctk.CTkLabel(
            self.sidebar_frame,
            text=t("screen_filter.title"),
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.new_preset_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=t("screen_filter.sidebar.new_preset"),
            command=self.create_new_preset
        )
        self.new_preset_btn.grid(row=1, column=0, padx=20, pady=10)

        self.preset_list_frame = ctk.CTkScrollableFrame(
            self.sidebar_frame,
            label_text=t("screen_filter.sidebar.new_preset").replace("+ ", "")
        )
        self.preset_list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        self.reset_defaults_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=t("screen_filter.sidebar.reset_defaults"),
            fg_color="transparent",
            border_width=1,
            command=self.reset_to_defaults
        )
        self.reset_defaults_btn.grid(row=3, column=0, padx=20, pady=10)

    def _create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Header
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 20))

        self.preset_title = ctk.CTkLabel(
            self.header_frame,
            text=t("screen_filter.sidebar.preset_name_prompt").replace(":", "..."),
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.preset_title.pack(side="left")

        self.save_btn = ctk.CTkButton(
            self.header_frame,
            text=t("common.save"),
            command=self.save_current_preset,
            fg_color="green"
        )
        self.save_btn.pack(side="right", padx=10)

        self.reset_filter_btn = ctk.CTkButton(
            self.header_frame,
            text=t("screen_filter.buttons.reset"),
            command=self.reset_filters,
            fg_color="red"
        )
        self.reset_filter_btn.pack(side="right")

        # Reset on Close checkbox (to the left of Reset button)
        self.reset_on_close_var = ctk.BooleanVar(
            value=self.config_manager.get_reset_on_close()
        )
        self.reset_on_close_checkbox = ctk.CTkCheckBox(
            self.header_frame,
            text=t("screen_filter.settings.reset_on_close"),
            variable=self.reset_on_close_var,
            command=self.on_reset_on_close_change
        )
        self.reset_on_close_checkbox.pack(side="right", padx=10)

        # Validation Warning (initially hidden)
        self.validation_warning_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="orange"
        )

        # Monitor Selection
        self.monitor_frame = ctk.CTkFrame(self.main_frame)
        self.monitor_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            self.monitor_frame,
            text=t("screen_filter.monitors.select"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.monitor_checkboxes_frame = ctk.CTkFrame(
            self.monitor_frame,
            fg_color="transparent"
        )
        self.monitor_checkboxes_frame.pack(fill="x", padx=10, pady=5)

        # Sliders Area
        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.pack(fill="both", expand=True)

        # Brightness
        self._create_slider(self.controls_frame, t("screen_filter.controls.brightness"), "brightness", -100, 100, 0)
        # Contrast
        self._create_slider(self.controls_frame, t("screen_filter.controls.contrast"), "contrast", -50, 50, 0)
        # Gamma
        self._create_slider(self.controls_frame, t("screen_filter.controls.gamma"), "gamma", 0.5, 3.0, 1.0, step=0.01)

        # RGB
        ctk.CTkLabel(
            self.controls_frame,
            text="RGB",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))

        self._create_slider(self.controls_frame, t("screen_filter.controls.red"), "red_scale", 0, 255, 255, step=1, scale_factor=1/255)
        self._create_slider(self.controls_frame, t("screen_filter.controls.green"), "green_scale", 0, 255, 255, step=1, scale_factor=1/255)
        self._create_slider(self.controls_frame, t("screen_filter.controls.blue"), "blue_scale", 0, 255, 255, step=1, scale_factor=1/255)

        # Overlay Compensation (Prevent Overexposure)
        ctk.CTkLabel(
            self.controls_frame,
            text=t("screen_filter.overlay_compensation.title"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))

        ctk.CTkLabel(
            self.controls_frame,
            text=t("screen_filter.overlay_compensation.description"),
            font=ctk.CTkFont(size=11),
            text_color="gray60"
        ).pack(anchor="w", padx=20, pady=(0, 5))

        self._create_slider(self.controls_frame, t("screen_filter.overlay_compensation.brightness_offset"), "overlay_brightness_offset", -100, 100, 0)
        self._create_slider(self.controls_frame, t("screen_filter.overlay_compensation.gamma_offset"), "overlay_gamma_offset", -1.0, 1.0, 0, step=0.01)
        self._create_slider(self.controls_frame, t("screen_filter.overlay_compensation.contrast_offset"), "overlay_contrast_offset", -50, 50, 0)

    def _create_slider(self, parent, label, attr_name, min_val, max_val, default_val, step=1, scale_factor=1):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=5)

        lbl = ctk.CTkLabel(frame, text=label, width=150, anchor="w")
        lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(frame, text=str(default_val), width=50)
        val_lbl.pack(side="right")

        def on_change(val):
            # Update label
            if step < 1:
                val_lbl.configure(text=f"{val:.2f}")
            else:
                val_lbl.configure(text=f"{int(val)}")

            # Update config
            if self.current_preset:
                # Convert UI value to algorithm value using ValueMapper
                if attr_name == "brightness":
                    final_val = ValueMapper.ui_to_algo_brightness(val)
                elif attr_name == "contrast":
                    final_val = ValueMapper.ui_to_algo_contrast(val)
                elif attr_name == "gamma":
                    final_val = ValueMapper.ui_to_algo_gamma(val)
                elif attr_name.endswith("_scale"):
                    final_val = ValueMapper.ui_to_algo_rgb(val)
                elif attr_name == "overlay_brightness_offset":
                    final_val = ValueMapper.ui_to_algo_brightness(val)
                elif attr_name == "overlay_contrast_offset":
                    final_val = ValueMapper.ui_to_algo_contrast(val)
                elif attr_name == "overlay_gamma_offset":
                    # 伽马偏移直接使用值，不需要映射
                    final_val = val
                else:
                    final_val = val

                setattr(self.current_preset.config, attr_name, final_val)

                # Validate and apply
                self._validate_and_apply_config()

        slider = ctk.CTkSlider(
            frame,
            from_=min_val,
            to=max_val,
            number_of_steps=int((max_val-min_val)/step),
            command=on_change
        )
        slider.set(default_val)
        slider.pack(side="left", fill="x", expand=True, padx=10)

        # Store reference to update later
        setattr(self, f"slider_{attr_name}", slider)
        setattr(self, f"label_{attr_name}", val_lbl)

    def refresh_monitors(self):
        # Clear existing
        for widget in self.monitor_checkboxes_frame.winfo_children():
            widget.destroy()

        monitors = self.gamma_controller.get_monitors()
        self.monitor_vars = {}

        # Load previously selected monitors from config
        saved_monitors = self.config_manager.get_selected_monitors()

        for m in monitors:
            # If we have saved selection, use it; otherwise default to all selected
            is_selected = m["device_name"] in saved_monitors if saved_monitors else True
            var = ctk.BooleanVar(value=is_selected)
            self.monitor_vars[m["device_name"]] = var
            cb = ctk.CTkCheckBox(
                self.monitor_checkboxes_frame,
                text=m["name"],
                variable=var,
                command=self.on_monitor_selection_change
            )
            cb.pack(side="left", padx=10)

        self.update_selected_monitors()

    def on_monitor_selection_change(self):
        self.update_selected_monitors()
        self.apply_current_config()

    def on_reset_on_close_change(self):
        """Handle reset_on_close checkbox change"""
        self.config_manager.set_reset_on_close(self.reset_on_close_var.get())

    def update_selected_monitors(self):
        self.selected_monitors = [dev for dev, var in self.monitor_vars.items() if var.get()]

    def load_presets_ui(self):
        # Clear list
        for widget in self.preset_list_frame.winfo_children():
            widget.destroy()

        presets = self.config_manager.get_all_presets()
        for p in presets:
            # Container frame for each preset
            preset_container = ctk.CTkFrame(self.preset_list_frame, fg_color="transparent")
            preset_container.pack(fill="x", pady=2)

            # Preset name button
            btn = ctk.CTkButton(
                preset_container,
                text=p.name,
                command=lambda p=p: self.select_preset(p),
                fg_color="transparent" if self.current_preset != p else "gray",
                border_width=1,
                anchor="w"
            )
            btn.pack(side="left", fill="x", expand=True)

            # Hotkey button (clickable to change)
            hotkey_btn = ctk.CTkButton(
                preset_container,
                text=p.hotkey or t("screen_filter.hotkeys.not_set"),
                width=60,
                fg_color="darkblue",
                command=lambda p=p: self.set_preset_hotkey(p)
            )
            hotkey_btn.pack(side="left", padx=2)

            # Delete button for non-default presets
            if not p.is_default:
                del_btn = ctk.CTkButton(
                    preset_container,
                    text="×",
                    width=30,
                    fg_color="red",
                    command=lambda pid=p.id: self.delete_preset(pid)
                )
                del_btn.pack(side="left")

    def select_preset(self, preset: FilterPreset):
        self.current_preset = preset
        self.preset_title.configure(text=preset.name)

        # Update sliders - convert algorithm values to UI values
        c = preset.config
        self._update_slider("brightness", ValueMapper.algo_to_ui_brightness(c.brightness))
        self._update_slider("contrast", ValueMapper.algo_to_ui_contrast(c.contrast))
        self._update_slider("gamma", ValueMapper.algo_to_ui_gamma(c.gamma))
        self._update_slider("red_scale", ValueMapper.algo_to_ui_rgb(c.red_scale))
        self._update_slider("green_scale", ValueMapper.algo_to_ui_rgb(c.green_scale))
        self._update_slider("blue_scale", ValueMapper.algo_to_ui_rgb(c.blue_scale))

        # Update overlay offset sliders (use same mapping as main parameters)
        self._update_slider("overlay_brightness_offset", ValueMapper.algo_to_ui_brightness(c.overlay_brightness_offset))
        self._update_slider("overlay_gamma_offset", c.overlay_gamma_offset)
        self._update_slider("overlay_contrast_offset", ValueMapper.algo_to_ui_contrast(c.overlay_contrast_offset))

        # Validate and apply
        self._validate_and_apply_config()

    def _update_slider(self, attr_name, value):
        slider = getattr(self, f"slider_{attr_name}")
        label = getattr(self, f"label_{attr_name}")
        slider.set(value)
        # Trigger label update
        if isinstance(value, float):
            label.configure(text=f"{value:.2f}")
        else:
            label.configure(text=f"{int(value)}")

    def _validate_and_apply_config(self):
        """Validate config and apply if valid, show warning if not"""
        if not self.current_preset or not self.selected_monitors:
            return

        # Validate configuration
        is_valid, error_msg = ValueMapper.validate_config(self.current_preset.config)

        if is_valid:
            # Apply valid configuration
            self.gamma_controller.apply_config(
                self.current_preset.config,
                self.selected_monitors
            )
            # Hide warning
            if self.validation_warning_label:
                self.validation_warning_label.pack_forget()
        else:
            # Show warning and suggest safe values
            safe_config = ValueMapper.suggest_safe_values(self.current_preset.config)

            # Display warning
            if self.validation_warning_label:
                warning_text = f"⚠ 参数组合可能导致问题，已自动调整"
                self.validation_warning_label.configure(text=warning_text)
                self.validation_warning_label.pack(side="top", pady=5)

            # Apply safe configuration instead
            self.gamma_controller.apply_config(
                safe_config,
                self.selected_monitors
            )

        # Apply overlay compensation if overlay window exists
        self._apply_overlay_compensation()

    def _apply_overlay_compensation(self, config: FilterConfig = None):
        """
        应用悬浮窗对冲参数

        当屏幕滤镜和悬浮窗同时启用时，悬浮窗可能过曝。
        使用预设中的overlay_*_offset参数对冲屏幕滤镜效果。

        Args:
            config: 要应用的FilterConfig，如果为None则使用current_preset的config
        """
        if not self.get_overlay_window:
            return

        # 如果没有指定config，使用当前预设
        if config is None:
            if not self.current_preset:
                return
            config = self.current_preset.config

        overlay_window = self.get_overlay_window()
        if not overlay_window:
            return

        # 应用对冲：使用负值来抵消屏幕滤镜的效果
        # 例如，如果屏幕滤镜增加了亮度，悬浮窗应该减少亮度
        overlay_window.set_compensation(
            brightness=-config.overlay_brightness_offset,
            contrast=-config.overlay_contrast_offset,
            gamma=1.0 / (1.0 + config.overlay_gamma_offset) if config.overlay_gamma_offset != -1.0 else 1.0
        )

    def apply_current_config(self):
        """Legacy method for compatibility"""
        self._validate_and_apply_config()

    def save_current_preset(self):
        """Save current preset configuration, hotkeys, and monitor selection"""
        if self.current_preset:
            # Update current preset
            self.config_manager.update_preset(self.current_preset)

            # Save monitor selection to config
            self.config_manager.set_selected_monitors(self.selected_monitors)

            # Save all to unified config file
            self.config_manager.save_config()

            messagebox.showinfo(t("common.success"), t("screen_filter.messages.save_success"))

    def set_preset_hotkey(self, preset: FilterPreset):
        """Allow user to set a custom hotkey for a preset"""
        self.waiting_for_hotkey = preset
        messagebox.showinfo(
            t("screen_filter.hotkeys.set_title"),
            t("screen_filter.hotkeys.set_prompt", preset_name=preset.name)
        )
        # The hotkey will be captured in the hotkey loop

    def create_new_preset(self):
        dialog = ctk.CTkInputDialog(text=t("screen_filter.sidebar.preset_name_prompt"), title=t("screen_filter.sidebar.new_preset"))
        name = dialog.get_input()
        if name:
            # Clone current config or default
            config = self.current_preset.config if self.current_preset else FilterConfig()

            # Create new preset with unique ID
            import uuid
            new_preset = FilterPreset(
                id=str(uuid.uuid4()),
                name=name,
                config=config,
                hotkey=None,
                is_default=False
            )
            self.config_manager.add_preset(new_preset)
            self.config_manager.save_config()
            self.load_presets_ui()
            self.select_preset(new_preset)

    def delete_preset(self, preset_id):
        if messagebox.askyesno(t("common.confirm"), t("screen_filter.sidebar.delete_confirm")):
            self.config_manager.delete_preset(preset_id)
            self.config_manager.save_config()
            self.load_presets_ui()
            # Select default if current deleted
            if self.current_preset and self.current_preset.id == preset_id:
                self.select_preset(self.config_manager.get_all_presets()[0])

    def reset_filters(self):
        self.gamma_controller.reset_monitors(self.selected_monitors)
        # Also select default preset
        defaults = [p for p in self.config_manager.get_all_presets() if p.id == "default"]
        if defaults:
            self.select_preset(defaults[0])

    def reset_to_defaults(self):
        if messagebox.askyesno(t("common.confirm"), t("screen_filter.messages.reset_defaults_confirm")):
            # Reset to default configuration
            self.config_manager.config = self.config_manager._create_default_config()
            self.config_manager.save_config()
            self.load_presets_ui()
            self.select_preset(self.config_manager.get_all_presets()[0])

    def _hotkey_loop(self):
        while self.running:
            try:
                # If waiting for hotkey binding, capture any key press
                if self.waiting_for_hotkey:
                    event = keyboard.read_event(suppress=False)
                    if event.event_type == keyboard.KEY_DOWN:
                        # Get the key name and normalize to uppercase
                        key_name = event.name.upper()

                        # Check if this hotkey is already in use by another preset
                        presets = self.config_manager.get_all_presets()
                        conflict = None
                        for p in presets:
                            if p.id != self.waiting_for_hotkey.id and p.hotkey and p.hotkey.upper() == key_name:
                                conflict = p
                                break

                        if conflict:
                            # Hotkey conflict detected - show in main thread
                            conflict_name = conflict.name
                            def show_warning():
                                messagebox.showwarning(
                                    t("screen_filter.hotkeys.set_title"),
                                    t("screen_filter.messages.hotkey_conflict_detail", key_name=key_name, conflict_name=conflict_name)
                                )
                            self.after(0, show_warning)
                            # Don't clear waiting state, allow user to try again
                            time.sleep(0.5)
                        else:
                            # No conflict, update preset hotkey
                            self.waiting_for_hotkey.hotkey = key_name
                            preset_name = self.waiting_for_hotkey.name
                            self.waiting_for_hotkey = None

                            # Refresh UI to show new hotkey - must be done in main thread
                            self.after(0, self.load_presets_ui)

                            # Show success message in main thread
                            def show_success():
                                messagebox.showinfo(t("common.success"), t("screen_filter.messages.hotkey_set_success", key_name=key_name))
                            self.after(100, show_success)

                            time.sleep(0.5)  # Prevent double trigger
                else:
                    # Normal hotkey detection for preset switching
                    presets = self.config_manager.get_all_presets()
                    for p in presets:
                        if p.hotkey and keyboard.is_pressed(p.hotkey):
                            # Apply screen filter
                            self.gamma_controller.apply_config(
                                p.config,
                                self.selected_monitors
                            )

                            # Apply overlay compensation
                            self._apply_overlay_compensation(p.config)

                            time.sleep(0.2)  # Debounce
                    time.sleep(0.1)
            except Exception as e:
                print(f"Hotkey error: {e}")

    def cleanup(self):
        """Clean up resources when tab is closed"""
        self.running = False

        # Reset filters if reset_on_close is enabled
        if self.config_manager.get_reset_on_close():
            print("[屏幕滤镜] 应用关闭，正在重置滤镜...")
            self.gamma_controller.reset_monitors(self.selected_monitors)
            print("[屏幕滤镜] 滤镜已重置")
