"""
T2 Tarkov Toolbox - Main Entry Point

A multi-module integrated toolbox for Escape from Tarkov players.

Modules:
- Screen Filter: Real-time screen color/brightness adjustment
- Local Map: Display player position from game screenshots
- Quest Tracker: Track and sync quest progress
"""

import sys
import customtkinter as ctk
from ui.main_window import MainWindow
from utils.global_config import get_global_config


def main():
    # 1. Load global configuration
    global_config = get_global_config()

    # 2. i18n system will auto-initialize on first t() call (lazy loading)

    # 3. Set CustomTkinter appearance
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    # 4. Create and run application
    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
