#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
DHCP Server Dialog for network interface and DHCP server configuration

This dialog provides a dedicated interface for configuring and managing
the custom DHCP server needed for camera discovery and initial setup.
"""

import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
                             QMessageBox, QGroupBox, QFrame, QSizePolicy, QDialogButtonBox,
                             QSpacerItem)
from PySide6.QtCore import Qt, Signal, Slot, QSettings


class DHCPServerDialog(QDialog):
    """Dialog for DHCP server configuration"""
    
    # Custom signals
    configuration_updated = Signal(dict)  # Emits configuration settings
    log_message = Signal(str)  # Emits log message
    
    def __init__(self, dhcp_manager, parent=None):
        """Initialize the DHCP server dialog"""
        super().__init__(parent)
        
        self.dhcp_manager = dhcp_manager
        
        self.setWindowTitle("DHCP Server Settings Configuration")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setModal(True)  # Make it a modal dialog
        
        # Apply parent's theme/palette if available
        if parent:
            self.setPalette(parent.palette())
        
        # Initialize UI
        self.init_ui()
        
        # Refresh network interfaces on startup
        self.refresh_network_interfaces()
        
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Instructions and header
        instructions = QGroupBox("DHCP Server Setup Instructions")
        instructions_layout = QVBoxLayout(instructions)
        
        instruction_text = QLabel(
            "The DHCP server is crucial for assigning temporary IP addresses to factory-new Axis cameras. "
            "Follow these steps to set up the DHCP server correctly:"
        )
        instruction_text.setWordWrap(True)
        instructions_layout.addWidget(instruction_text)
        
        instruction_steps = [
            "<b>Step 1:</b> Manually set your PC's IP address to a static IP on the camera network",
            "<b>Step 2:</b> Connect your PC directly to the camera(s) with an Ethernet switch",
            "<b>Step 3:</b> Select the network interface connected to the cameras",
            "<b>Step 4:</b> Configure the DHCP server settings or use the recommended defaults",
            "<b>Step 5:</b> Start the DHCP server before powering on your cameras"
        ]
        
        for instruction in instruction_steps:
            step_label = QLabel(instruction)
            step_label.setTextFormat(Qt.RichText)
            instructions_layout.addWidget(step_label)
        
        main_layout.addWidget(instructions)
        
        # Network Interface Selection
        interface_group = QGroupBox("Network Interface Selection")
        interface_layout = QGridLayout(interface_group)
        
        interface_layout.addWidget(QLabel("Available Network Interfaces:"), 0, 0)
        self.network_interfaces_combo = QComboBox()
        interface_layout.addWidget(self.network_interfaces_combo, 0, 1)
        
        refresh_btn = QPushButton("Refresh Network Interfaces")
        refresh_btn.clicked.connect(self.refresh_network_interfaces)
        interface_layout.addWidget(refresh_btn, 0, 2)
        
        interface_layout.addWidget(QLabel("DHCP Server IP (This PC's Static IP):"), 1, 0)
        self.dhcp_server_ip = QLineEdit()
        self.dhcp_server_ip.setReadOnly(True)  # Auto-detected from selected interface
        interface_layout.addWidget(self.dhcp_server_ip, 1, 1, 1, 2)
        
        main_layout.addWidget(interface_group)
        
        # DHCP Configuration
        dhcp_group = QGroupBox("DHCP Server Configuration")
        dhcp_layout = QGridLayout(dhcp_group)
        
        self.use_default_dhcp = QCheckBox("Use Default DHCP Settings (Recommended)")
        self.use_default_dhcp.setChecked(True)
        self.use_default_dhcp.stateChanged.connect(self.toggle_dhcp_inputs)
        dhcp_layout.addWidget(self.use_default_dhcp, 0, 0, 1, 2)
        
        dhcp_layout.addWidget(QLabel("DHCP IP Range Start:"), 1, 0)
        self.dhcp_start_ip = QLineEdit("192.168.0.50")
        dhcp_layout.addWidget(self.dhcp_start_ip, 1, 1)
        
        dhcp_layout.addWidget(QLabel("DHCP IP Range End:"), 2, 0)
        self.dhcp_end_ip = QLineEdit("192.168.0.97")
        dhcp_layout.addWidget(self.dhcp_end_ip, 2, 1)
        
        dhcp_layout.addWidget(QLabel("DHCP Lease Time (seconds):"), 3, 0)
        self.dhcp_lease_time = QLineEdit("3600")
        dhcp_layout.addWidget(self.dhcp_lease_time, 3, 1)
        
        main_layout.addWidget(dhcp_group)
        
        # Add information about moving controls to main window
        info_label = QLabel("DHCP server control buttons (Start/Stop) are available on the main window.")
        info_label.setStyleSheet("color: #0066cc; font-style: italic;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # Add spacer before the buttons to push everything up
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Standard dialog buttons with Apply/Save
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_configuration)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        # Initialize with default settings
        self.toggle_dhcp_inputs(Qt.Checked)
    
    def refresh_network_interfaces(self):
        """Refresh the list of available network interfaces"""
        self.network_interfaces_combo.clear()
        
        try:
            interfaces = self.dhcp_manager.get_network_interfaces()
            for interface_name, interface_details in interfaces.items():
                if interface_details.get("ipv4"):
                    display_text = f"{interface_name} - {interface_details['ipv4']}"
                    self.network_interfaces_combo.addItem(display_text, 
                                                        {"name": interface_name, "ip": interface_details['ipv4']})
            
            if self.network_interfaces_combo.count() > 0:
                self.log_message.emit("Network interfaces refreshed successfully")
                # Update the server IP field with the selected interface's IP
                self.update_server_ip()
                self.network_interfaces_combo.currentIndexChanged.connect(self.update_server_ip)
            else:
                self.log_message.emit("No network interfaces with IPv4 addresses found")
        except Exception as e:
            self.log_message.emit(f"Error refreshing network interfaces: {str(e)}")
    
    def update_server_ip(self):
        """Update the server IP field with the currently selected interface's IP"""
        current_data = self.network_interfaces_combo.currentData()
        if current_data:
            self.dhcp_server_ip.setText(current_data["ip"])
    
    @Slot(int)
    def toggle_dhcp_inputs(self, state):
        """Toggle DHCP configuration input fields based on checkbox state"""
        enabled = state != Qt.Checked
        self.dhcp_start_ip.setEnabled(enabled)
        self.dhcp_end_ip.setEnabled(enabled)
        self.dhcp_lease_time.setEnabled(enabled)
    
    @Slot()
    def save_configuration(self):
        """Save DHCP server configuration"""
        if not self.network_interfaces_combo.currentData():
            QMessageBox.warning(self, "Configuration Error", "No network interface selected")
            self.log_message.emit("Error: No network interface selected")
            return
            
        if not self.dhcp_server_ip.text():
            QMessageBox.warning(self, "Configuration Error", "DHCP Server IP is required")
            self.log_message.emit("Error: DHCP Server IP (This PC's Static IP) is required")
            return
            
        # Get configuration values
        interface_data = self.network_interfaces_combo.currentData()
        interface = interface_data["name"]
        server_ip = self.dhcp_server_ip.text()
        start_ip = self.dhcp_start_ip.text()
        end_ip = self.dhcp_end_ip.text()
        
        try:
            lease_time = int(self.dhcp_lease_time.text())
            if lease_time <= 0:
                raise ValueError("Lease time must be a positive integer")
        except ValueError:
            QMessageBox.warning(self, "Configuration Error", "Lease time must be a valid number")
            self.log_message.emit("Error: Invalid lease time value")
            return
        
        # Create configuration dictionary to emit
        config = {
            'interface': interface,
            'server_ip': server_ip,
            'start_ip': start_ip,
            'end_ip': end_ip,
            'lease_time': lease_time
        }
        
        # Configure DHCP server in manager (but don't start it)
        try:
            self.dhcp_manager.configure(
                interface=interface, 
                server_ip=server_ip,
                start_ip=start_ip,
                end_ip=end_ip,
                lease_time=lease_time
            )
            
            self.log_message.emit(f"DHCP server configured: interface={interface}, IP range={start_ip} to {end_ip}")
            
            # Emit configuration updated signal
            self.configuration_updated.emit(config)
            
            # Close dialog
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "DHCP Configuration Error", f"Failed to configure DHCP server: {str(e)}")
            self.log_message.emit(f"Error configuring DHCP server: {str(e)}")
    
    def get_current_configuration(self):
        """Get the current DHCP configuration settings"""
        if not self.network_interfaces_combo.currentData():
            return None
            
        interface_data = self.network_interfaces_combo.currentData()
        
        config = {
            'interface': interface_data["name"],
            'server_ip': self.dhcp_server_ip.text(),
            'start_ip': self.dhcp_start_ip.text(),
            'end_ip': self.dhcp_end_ip.text(),
            'lease_time': int(self.dhcp_lease_time.text()) if self.dhcp_lease_time.text().isdigit() else 3600
        }
        
        return config
    
    def forward_log_message(self, message):
        """Forward log messages from workers to the main window"""
        self.log_message.emit(message)
