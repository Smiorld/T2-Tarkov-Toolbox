"""
T2 Tarkov Toolbox - Main Entry Point

A multi-module integrated toolbox for Escape from Tarkov players.

Modules:
- Screen Filter: Real-time screen color/brightness adjustment
- Local Map: Display player position from game screenshots
- Quest Tracker: Track and sync quest progress
"""

import customtkinter as ctk
from ui.main_window import MainWindow


def main():
    # Set CustomTkinter appearance
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    # Create and run application
    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
