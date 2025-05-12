#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
About dialog implementation
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap


class AboutDialog(QDialog):
    """About dialog for the application"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        
        # Application icon
        try:
            icon_label = QLabel()
            icon_pixmap = QIcon("axis_config_tool/resources/app_icon.ico").pixmap(64, 64)
            if not icon_pixmap.isNull():
                icon_label.setPixmap(icon_pixmap)
                icon_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(icon_label)
        except Exception:
            # If icon loading fails, just skip it
            pass
        
        # Application info
        info_text = (
            "<h3>AxisAutoConfig</h3>"
            "<p>Version 1.0.0</p>"
            "<p>Developed by: Geoffrey Stephens</p>"
            "<p>Contact: gstephens@storypolish.com</p>"
            "<p>Date: May 11, 2025</p>"
            "<p>An all-in-one solution for initializing and pre-configuring "
            "factory-new Axis cameras.</p>"
        )
        
        info_label = QLabel(info_text)
        info_label.setTextFormat(Qt.RichText)
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setMaximumWidth(100)
        layout.addWidget(close_button, 0, Qt.AlignCenter)
