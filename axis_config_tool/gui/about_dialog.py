#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
About dialog implementation

This dialog provides information about the application, version,
and developer contact details. It also highlights the unique
problem-solving approach of the application.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSizePolicy, QTabWidget, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QFont
from axis_config_tool import __version__, __author__, __email__, __date__


class AboutDialog(QDialog):
    """
    About dialog for the application
    
    Displays comprehensive information about AxisAutoConfig, including:
    - Version information and release details
    - Developer contact information
    - Key features and benefits
    - Time savings and efficiency improvements
    - Acknowledgments and credits
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About AxisAutoConfig")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        
        # Header with icon and title
        header_layout = QHBoxLayout()
        
        # Application icon
        try:
            icon_label = QLabel()
            icon_pixmap = QIcon("axis_config_tool/resources/app_icon.ico").pixmap(64, 64)
            if not icon_pixmap.isNull():
                icon_label.setPixmap(icon_pixmap)
                header_layout.addWidget(icon_label)
        except Exception:
            # If icon loading fails, just skip it
            pass
        
        # Application title and version
        title_label = QLabel(f"<h2>AxisAutoConfig</h2><p>Version {__version__}</p>")
        title_label.setTextFormat(Qt.RichText)
        header_layout.addWidget(title_label)
        header_layout.setStretch(1, 1)  # Make title take up remaining space
        
        layout.addLayout(header_layout)
        
        # Create tab widget for different information categories
        tabs = QTabWidget()
        
        # Overview tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        
        overview_text = (
            "<p><b>AxisAutoConfig</b> is a comprehensive solution for initializing "
            "and pre-configuring factory-new Axis IP cameras.</p>"
            
            "<p>This application automates the entire setup process, from DHCP assignment "
            "to final static IP configuration, significantly reducing deployment time.</p>"
            
            f"<p><b>Developed by:</b> {__author__}<br>"
            f"<b>Contact:</b> {__email__}<br>"
            f"<b>Release Date:</b> {__date__}</p>"
            
            "<p><b>Time Savings:</b> Compared to manual configuration, AxisAutoConfig "
            "reduces setup time by approximately:</p>"
            "<ul>"
            "<li>5 minutes per camera for basic setup</li>"
            "<li>80% reduction in total configuration time</li>"
            "<li>Near-elimination of configuration errors</li>"
            "</ul>"
        )
        
        overview_label = QLabel(overview_text)
        overview_label.setTextFormat(Qt.RichText)
        overview_label.setWordWrap(True)
        overview_label.setOpenExternalLinks(True)
        overview_layout.addWidget(overview_label)
        overview_layout.addStretch(1)
        
        # Features tab
        features_tab = QWidget()
        features_layout = QVBoxLayout(features_tab)
        
        features_text = (
            "<p><b>Key Features:</b></p>"
            "<ul>"
            "<li><b>Custom DHCP Server</b> - Handles identical factory-default IPs</li>"
            "<li><b>Three-User Workflow</b> - Root admin, secondary admin, and ONVIF user</li>"
            "<li><b>Automated Configuration</b> - WDR, Replay Protection, and Static IP</li>"
            "<li><b>Flexible IP Assignment</b> - Sequential or MAC-specific modes</li>"
            "<li><b>Comprehensive Reporting</b> - CSV export with configuration status</li>"
            "<li><b>User-Friendly Interface</b> - Interactive help and guided workflow</li>"
            "</ul>"
            
            "<p><b>Innovative Approach:</b></p>"
            "<p>AxisAutoConfig was developed after extensive research into Axis APIs and DHCP mechanisms "
            "to solve the challenges of configuring multiple factory-new cameras efficiently.</p>"
            
            "<p>The custom DHCP implementation and multi-step configuration workflow represent "
            "a novel approach to automation in this domain.</p>"
            
            "<p><b>Acknowledgements:</b></p>"
            "<p>Special thanks to <a href='https://github.com/Cacsjep'>Cacsjep</a> from the Axis developer community "
            "for assistance in finding the correct API endpoint for setting static IP addresses.</p>"
        )
        
        features_label = QLabel(features_text)
        features_label.setTextFormat(Qt.RichText)
        features_label.setWordWrap(True)
        features_layout.addWidget(features_label)
        features_layout.addStretch(1)
        
        # Add tabs to tab widget
        tabs.addTab(overview_tab, "Overview")
        tabs.addTab(features_tab, "Features")
        
        layout.addWidget(tabs)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setMaximumWidth(100)
        layout.addWidget(close_button, 0, Qt.AlignCenter)
