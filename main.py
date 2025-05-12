#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AxisAutoConfig
Main entry point for running from source
"""

import sys
import os
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

# Add the project root to the Python path if running from source
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import from our package
from axis_config_tool.gui.main_window import MainWindow


def setup_logging():
    """Set up logging configuration for the application"""
    log_file = "axis_config.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info("Logging initialized")


def main():
    """Main application entry point"""
    # Set up logging
    setup_logging()
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("AxisAutoConfig")
    
    # Set application icon
    icon_path = os.path.join("axis_config_tool", "resources", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Enable high DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create and show main window
    main_window = MainWindow()
    main_window.setWindowFlags(main_window.windowFlags() | Qt.WindowMinMaxButtonsHint)
    main_window.show()
    
    # Ensure app exits when window is closed
    main_window.destroyed.connect(app.quit)
    
    # Create resources directory if it doesn't exist
    resources_dir = os.path.join("axis_config_tool", "resources")
    os.makedirs(resources_dir, exist_ok=True)
    
    # Check if app_icon.ico exists in current directory and copy to resources if needed
    icon_source = "app_icon.ico"
    icon_dest = os.path.join(resources_dir, "app_icon.ico")
    
    if os.path.exists(icon_source) and not os.path.exists(icon_dest):
        import shutil
        try:
            shutil.copy2(icon_source, icon_dest)
            logging.info(f"Copied app icon to {icon_dest}")
        except Exception as e:
            logging.warning(f"Failed to copy app icon: {str(e)}")
    
    # Start the application event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
