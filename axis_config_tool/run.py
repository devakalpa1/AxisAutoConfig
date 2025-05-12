#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
Package entry point for installed package
"""

import sys
from axis_config_tool.gui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import logging
import os


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
    """Main application entry point for installed package"""
    # Set up logging
    setup_logging()
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Axis Camera Unified Setup & Configuration Tool")
    
    # Enable high DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Create and show main window
    main_window = MainWindow()
    main_window.show()
    
    # Start the application event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
