import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import keyboard
import threading
import time
from typing import List

from models import FilterConfig, FilterPreset
from gamma_controller import GammaController
from preset_manager import PresetManager

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("T2 Tarkov Toolbox - Screen Filter")
        self.geometry("1100x700")

        # Managers
        self.gamma_controller = GammaController()
        self.preset_manager = PresetManager()
        
        # State
        self.current_preset: FilterPreset = None
        self.selected_monitors: List[str] = []
        self.monitor_vars = {} # device_name -> BooleanVar

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_main_area()

        # Initialize
        self.refresh_monitors()
        self.load_presets_ui()
        
        # Select first preset if available
        presets = self.preset_manager.get_all_presets()
        if presets:
            self.select_preset(presets[0])

        # Start Hotkey Listener
        self.running = True
        self.hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self.hotkey_thread.start()

    def _create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(2, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="T2 Toolbox", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.new_preset_btn = ctk.CTkButton(self.sidebar_frame, text="+ 新建预设", command=self.create_new_preset)
        self.new_preset_btn.grid(row=1, column=0, padx=20, pady=10)

        self.preset_list_frame = ctk.CTkScrollableFrame(self.sidebar_frame, label_text="预设列表")
        self.preset_list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        self.reset_defaults_btn = ctk.CTkButton(self.sidebar_frame, text="恢复默认预设", fg_color="transparent", border_width=1, command=self.reset_to_defaults)
        self.reset_defaults_btn.grid(row=3, column=0, padx=20, pady=10)

    def _create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Header
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 20))
        
        self.preset_title = ctk.CTkLabel(self.header_frame, text="选择预设...", font=ctk.CTkFont(size=24, weight="bold"))
        self.preset_title.pack(side="left")

        self.save_btn = ctk.CTkButton(self.header_frame, text="保存修改", command=self.save_current_preset, fg_color="green")
        self.save_btn.pack(side="right", padx=10)
        
        self.reset_filter_btn = ctk.CTkButton(self.header_frame, text="重置所有滤镜", command=self.reset_filters, fg_color="red")
        self.reset_filter_btn.pack(side="right")

        # Monitor Selection
        self.monitor_frame = ctk.CTkFrame(self.main_frame)
        self.monitor_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(self.monitor_frame, text="目标显示器", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
        self.monitor_checkboxes_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        self.monitor_checkboxes_frame.pack(fill="x", padx=10, pady=5)

        # Sliders Area
        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.pack(fill="both", expand=True)

        # Brightness
        self._create_slider(self.controls_frame, "亮度 (Brightness)", "brightness", -100, 100, 0)
        # Contrast
        self._create_slider(self.controls_frame, "对比度 (Contrast)", "contrast", -50, 50, 0)
        # Gamma
        self._create_slider(self.controls_frame, "伽马 (Gamma)", "gamma", 0.5, 3.5, 1.0, step=0.01)
        
        # RGB
        ctk.CTkLabel(self.controls_frame, text="色彩通道 (RGB)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        self._create_slider(self.controls_frame, "红色 (Red)", "red_scale", 0, 255, 255, step=1, scale_factor=1/255)
        self._create_slider(self.controls_frame, "绿色 (Green)", "green_scale", 0, 255, 255, step=1, scale_factor=1/255)
        self._create_slider(self.controls_frame, "蓝色 (Blue)", "blue_scale", 0, 255, 255, step=1, scale_factor=1/255)

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
                # Handle special conversions
                final_val = val
                if attr_name == "brightness" or attr_name == "contrast":
                    final_val = val / 100.0
                elif attr_name.endswith("_scale"):
                    final_val = val / 255.0
                
                setattr(self.current_preset.config, attr_name, final_val)
                self.apply_current_config()

        slider = ctk.CTkSlider(frame, from_=min_val, to=max_val, number_of_steps=(max_val-min_val)/step, command=on_change)
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
        
        for m in monitors:
            var = ctk.BooleanVar(value=True) # Default select all
            self.monitor_vars[m["device_name"]] = var
            cb = ctk.CTkCheckBox(self.monitor_checkboxes_frame, text=m["name"], variable=var, command=self.on_monitor_selection_change)
            cb.pack(side="left", padx=10)
        
        self.update_selected_monitors()

    def on_monitor_selection_change(self):
        self.update_selected_monitors()
        self.apply_current_config()

    def update_selected_monitors(self):
        self.selected_monitors = [dev for dev, var in self.monitor_vars.items() if var.get()]

    def load_presets_ui(self):
        # Clear list
        for widget in self.preset_list_frame.winfo_children():
            widget.destroy()
            
        presets = self.preset_manager.get_all_presets()
        for p in presets:
            btn = ctk.CTkButton(self.preset_list_frame, text=f"{p.name} [{p.hotkey or ''}]", 
                                command=lambda p=p: self.select_preset(p),
                                fg_color="transparent" if self.current_preset != p else "gray",
                                border_width=1, anchor="w")
            btn.pack(fill="x", pady=2)
            
            # Context menu (Right click) - Simplified as buttons for now
            if not p.is_default:
                del_btn = ctk.CTkButton(self.preset_list_frame, text="x", width=20, fg_color="red", 
                                      command=lambda pid=p.id: self.delete_preset(pid))
                del_btn.pack(pady=2) # Layout needs improvement for delete button, keeping simple for now

    def select_preset(self, preset: FilterPreset):
        self.current_preset = preset
        self.preset_title.configure(text=preset.name)
        
        # Update sliders
        c = preset.config
        self._update_slider("brightness", c.brightness * 100)
        self._update_slider("contrast", c.contrast * 100)
        self._update_slider("gamma", c.gamma)
        self._update_slider("red_scale", c.red_scale * 255)
        self._update_slider("green_scale", c.green_scale * 255)
        self._update_slider("blue_scale", c.blue_scale * 255)
        
        self.apply_current_config()

    def _update_slider(self, attr_name, value):
        slider = getattr(self, f"slider_{attr_name}")
        label = getattr(self, f"label_{attr_name}")
        slider.set(value)
        # Trigger label update
        if isinstance(value, float):
             label.configure(text=f"{value:.2f}")
        else:
             label.configure(text=f"{int(value)}")

    def apply_current_config(self):
        if self.current_preset and self.selected_monitors:
            self.gamma_controller.apply_config(self.current_preset.config, self.selected_monitors)

    def save_current_preset(self):
        if self.current_preset:
            self.preset_manager.update_preset(self.current_preset.id, config=self.current_preset.config)
            messagebox.showinfo("Success", "预设已保存")

    def create_new_preset(self):
        dialog = ctk.CTkInputDialog(text="输入新预设名称:", title="新建预设")
        name = dialog.get_input()
        if name:
            # Clone current config or default
            config = self.current_preset.config if self.current_preset else FilterConfig()
            new_preset = self.preset_manager.create_preset(name, config)
            self.load_presets_ui()
            self.select_preset(new_preset)

    def delete_preset(self, preset_id):
        if messagebox.askyesno("Confirm", "确定删除此预设吗?"):
            self.preset_manager.delete_preset(preset_id)
            self.load_presets_ui()
            # Select default if current deleted
            if self.current_preset.id == preset_id:
                self.select_preset(self.preset_manager.get_all_presets()[0])

    def reset_filters(self):
        self.gamma_controller.reset_monitors(self.selected_monitors)
        # Also select default preset
        defaults = [p for p in self.preset_manager.get_all_presets() if p.id == "default"]
        if defaults:
            self.select_preset(defaults[0])

    def reset_to_defaults(self):
        if messagebox.askyesno("Confirm", "恢复所有系统默认预设? (自定义预设将丢失)"):
            self.preset_manager.reset_to_defaults()
            self.load_presets_ui()
            self.select_preset(self.preset_manager.get_all_presets()[0])

    def _hotkey_loop(self):
        while self.running:
            try:
                presets = self.preset_manager.get_all_presets()
                for p in presets:
                    if p.hotkey and keyboard.is_pressed(p.hotkey):
                        # Apply preset
                        # Note: This runs in thread, be careful with UI updates
                        # For gamma application it's fine
                        self.gamma_controller.apply_config(p.config, self.selected_monitors)
                        # Optional: Update UI selection (needs thread safety)
                        time.sleep(0.2) # Debounce
                time.sleep(0.1)
            except Exception as e:
                print(f"Hotkey error: {e}")

    def on_closing(self):
        self.running = False
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
