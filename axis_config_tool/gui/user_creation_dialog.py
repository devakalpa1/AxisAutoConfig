#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
Dialog for user creation workflow
"""

import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox,
                             QSpacerItem, QSizePolicy, QDialogButtonBox,
                             QMessageBox)
from PySide6.QtCore import Qt


class UserCreationDialog(QDialog):
    """Dialog for the three-user creation workflow"""
    
    def __init__(self, parent=None):
        """Initialize the user creation dialog"""
        super().__init__(parent)
        self.setWindowTitle("User Creation Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        # Apply parent's theme/palette if available
        if parent:
            self.setPalette(parent.palette())
        
        # Initialize UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Explanation text
        explanation = QLabel(
            "Configure the three-user workflow for camera setup. "
            "Root admin is created first, followed by an optional secondary admin, "
            "and finally an ONVIF user for client access."
        )
        explanation.setWordWrap(True)
        main_layout.addWidget(explanation)
        
        # Step 1: Root Admin
        root_group = QGroupBox("Step 1: Root Admin (First Admin)")
        root_layout = QGridLayout(root_group)
        
        # Root Admin Username (fixed as 'root')
        root_layout.addWidget(QLabel("Root Administrator Username:"), 0, 0)
        root_layout.addWidget(QLabel("root (required by Axis OS v10)"), 0, 1)
        
        # Root Admin Password
        root_layout.addWidget(QLabel("Root Administrator Password:"), 1, 0)
        self.root_password = QLineEdit()
        self.root_password.setEchoMode(QLineEdit.Password)
        self.root_password.setPlaceholderText("Required")
        root_layout.addWidget(self.root_password, 1, 1)
        
        main_layout.addWidget(root_group)
        
        # Step 2: Secondary Admin
        secondary_group = QGroupBox("Step 2: Secondary Administrator (Optional)")
        secondary_layout = QGridLayout(secondary_group)
        
        secondary_layout.addWidget(QLabel("Secondary Administrator Username:"), 0, 0)
        self.secondary_username = QLineEdit()
        self.secondary_username.setPlaceholderText("Optional - custom admin name")
        secondary_layout.addWidget(self.secondary_username, 0, 1)
        
        # Note about shared password
        note = QLabel("Note: Secondary admin will use the same password as root admin")
        note.setStyleSheet("color: #666; font-style: italic;")
        secondary_layout.addWidget(note, 1, 0, 1, 2)
        
        main_layout.addWidget(secondary_group)
        
        # Step 3: ONVIF User
        onvif_group = QGroupBox("Step 3: ONVIF User")
        onvif_layout = QGridLayout(onvif_group)
        
        onvif_layout.addWidget(QLabel("ONVIF Username to Create:"), 0, 0)
        self.onvif_username = QLineEdit()
        self.onvif_username.setPlaceholderText("For ONVIF client access")
        onvif_layout.addWidget(self.onvif_username, 0, 1)
        
        onvif_layout.addWidget(QLabel("ONVIF Password to Set:"), 1, 0)
        self.onvif_password = QLineEdit()
        self.onvif_password.setEchoMode(QLineEdit.Password)
        onvif_layout.addWidget(self.onvif_password, 1, 1)
        
        main_layout.addWidget(onvif_group)
        
        # Help text
        help_text = QLabel(
            "<b>Important:</b> All cameras will be configured using this user creation workflow. "
            "Root admin is required and will always be created first. Secondary admin and ONVIF "
            "users will be created if usernames are provided."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("font-size: 11px; color: #888;")
        main_layout.addWidget(help_text)
        
        # Standard dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def validate_and_accept(self):
        """Validate inputs before accepting dialog"""
        # Check that root password is provided
        if not self.root_password.text():
            QMessageBox.warning(self, "Missing Required Field",
                              "Root Administrator Password is required.")
            return
            
        # Check if ONVIF credentials are complete
        onvif_user = self.onvif_username.text()
        onvif_pass = self.onvif_password.text()
        if (onvif_user and not onvif_pass) or (not onvif_user and onvif_pass):
            QMessageBox.warning(self, "Incomplete ONVIF Credentials",
                              "Please provide both ONVIF username and password, or leave both empty.")
            return
        
        self.accept()
    
    def get_user_credentials(self):
        """Return the configured user credentials"""
        return {
            "root_password": self.root_password.text(),
            "secondary_username": self.secondary_username.text(),
            "onvif_username": self.onvif_username.text(),
            "onvif_password": self.onvif_password.text()
        }
