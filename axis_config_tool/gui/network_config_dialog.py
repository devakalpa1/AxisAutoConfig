#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
Network Configuration Dialog

This dialog provides a dedicated interface for configuring network settings
for camera static IP assignment including subnet mask, default gateway,
VAPIX protocol selection, and IP assignment mode.
"""

import logging
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QRadioButton,
                             QMessageBox, QGroupBox, QFrame, QSizePolicy, QDialogButtonBox,
                             QSpacerItem, QTabWidget, QWidget, QTextEdit, QFileDialog)
from PySide6.QtCore import Qt, Signal, Slot, QSettings


class NetworkConfigDialog(QDialog):
    """Dialog for network configuration settings"""
    
    # Custom signals
    settings_updated = Signal(dict)  # Emits settings when updated/confirmed
    log_message = Signal(str)  # Emits log message
    
    def __init__(self, csv_handler, parent=None):
        """Initialize the network configuration dialog"""
        super().__init__(parent)
        
        self.csv_handler = csv_handler
        self.csv_path = ""
        self.csv_entries = []
        
        self.setWindowTitle("Network Configuration Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)
        self.setModal(True)  # Make it a modal dialog
        
        # Apply parent's theme/palette if available
        if parent:
            self.setPalette(parent.palette())
        
        # Initialize UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Create tabs for better organization
        self.tab_widget = QTabWidget()
        
        # Tab 1: Basic Network Settings
        self.create_basic_settings_tab()
        
        # Tab 2: IP Assignment Settings
        self.create_ip_assignment_tab()
        
        # Tab 3: CSV Format Help
        self.create_csv_help_tab()
        
        main_layout.addWidget(self.tab_widget)
          # Standard dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        
        # Add Save Settings button to button box
        self.save_btn = button_box.addButton("Save Settings", QDialogButtonBox.ActionRole)
        self.save_btn.setToolTip("Save current network configuration settings")
        self.save_btn.clicked.connect(self.save_settings_as_default)
        
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        # Load default settings if available
        self.load_default_settings()
        
    def load_default_settings(self):
        """Load previously saved default settings if available"""
        try:
            settings = QSettings("AxisAutoConfig", "SetupTool")
            
            # Load basic network settings
            subnet_mask = settings.value("DefaultSubnetMask", "255.255.255.0")
            gateway = settings.value("DefaultGateway", "")
            protocol = settings.value("DefaultProtocol", "HTTP")
            
            # Apply settings to UI elements
            self.subnet_mask.setText(subnet_mask)
            self.default_gateway.setText(gateway)
            protocol_index = self.vapix_protocol.findText(protocol) 
            if protocol_index >= 0:
                self.vapix_protocol.setCurrentIndex(protocol_index)
            
            # Load IP assignment mode
            mode = settings.value("DefaultIPMode", "sequential")
            if mode == "mac_specific":
                self.mac_specific_radio.setChecked(True)
            else:
                self.sequential_radio.setChecked(True)
            
            # Update mode description
            self.update_mode_description()
            
            # Log that settings were loaded
            self.log_message.emit("Loaded default network settings")
            
        except Exception as e:
            self.log_message.emit(f"Error loading default settings: {str(e)}")
    
    def create_basic_settings_tab(self):
        """Create the basic network settings tab"""
        basic_tab = QWidget()
        layout = QVBoxLayout(basic_tab)
        
        # Network Configuration Group Box
        net_group = QGroupBox("Static IP Configuration")
        net_layout = QGridLayout(net_group)
        net_row = 0
        
        net_layout.addWidget(QLabel("Final Static Subnet Mask:"), net_row, 0)
        self.subnet_mask = QLineEdit("255.255.255.0")
        self.subnet_mask.setToolTip("The subnet mask for the final static IP addresses (e.g., 255.255.255.0)")
        net_layout.addWidget(self.subnet_mask, net_row, 1)
        net_row += 1
        
        net_layout.addWidget(QLabel("Final Static Default Gateway:"), net_row, 0)
        self.default_gateway = QLineEdit()
        self.default_gateway.setToolTip("The default gateway for the camera network")
        net_layout.addWidget(self.default_gateway, net_row, 1)
        net_row += 1
        
        # VAPIX Protocol Configuration
        net_layout.addWidget(QLabel("VAPIX Protocol for Config:"), net_row, 0)
        self.vapix_protocol = QComboBox()
        self.vapix_protocol.addItems(["HTTP", "HTTPS"])
        self.vapix_protocol.setToolTip("Protocol to use for camera configuration (HTTP recommended)")
        net_layout.addWidget(self.vapix_protocol, net_row, 1)
        net_row += 1
        
        # Save Settings Button
        self.save_settings_btn = QPushButton("Save as Default Settings")
        self.save_settings_btn.setToolTip("Save these network settings as defaults for future use")
        self.save_settings_btn.clicked.connect(self.save_settings_as_default)
        net_layout.addWidget(self.save_settings_btn, net_row, 1)
        
        # Add some explanatory text
        help_text = QLabel(
            "These settings will be applied to all cameras during the configuration process. "
            "The subnet mask and default gateway should match your target network environment."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666; font-style: italic;")
        
        layout.addWidget(net_group)
        layout.addWidget(help_text)
        layout.addStretch(1)  # Add space at the bottom
        
        self.tab_widget.addTab(basic_tab, "Basic Settings")
    
    def create_ip_assignment_tab(self):
        """Create the IP assignment tab"""
        ip_tab = QWidget()
        layout = QVBoxLayout(ip_tab)
        
        # IP Assignment Mode Group
        mode_group = QGroupBox("IP Assignment Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        # Sequential mode
        self.sequential_radio = QRadioButton("Sequential Assignment")
        self.sequential_radio.setToolTip("Assign IPs to cameras in the order they are discovered")
        self.sequential_radio.setChecked(True)  # Default option
        self.sequential_radio.toggled.connect(self.update_mode_description)
        mode_layout.addWidget(self.sequential_radio)
        
        # MAC-specific mode
        self.mac_specific_radio = QRadioButton("MAC-Specific Assignment")
        self.mac_specific_radio.setToolTip("Assign specific IPs to cameras based on their MAC addresses")
        self.mac_specific_radio.toggled.connect(self.update_mode_description)
        mode_layout.addWidget(self.mac_specific_radio)
        
        # Mode description text
        self.mode_description = QLabel()
        self.mode_description.setWordWrap(True)
        self.mode_description.setStyleSheet("color: #666; font-style: italic;")
        mode_layout.addWidget(self.mode_description)
        
        # Initialize mode description
        self.update_mode_description()
        
        layout.addWidget(mode_group)
        
        # CSV File Group
        csv_group = QGroupBox("CSV File Selection")
        csv_layout = QVBoxLayout(csv_group)
        
        # CSV file path and selection
        csv_file_layout = QHBoxLayout()
        
        self.load_csv_btn = QPushButton("Load IP List (CSV)...")
        self.load_csv_btn.clicked.connect(self.load_csv)
        csv_file_layout.addWidget(self.load_csv_btn)
        
        self.csv_path_label = QLabel("No CSV file loaded")
        self.csv_path_label.setStyleSheet("font-style: italic;")
        csv_file_layout.addWidget(self.csv_path_label, 1)
        
        csv_layout.addLayout(csv_file_layout)
        
        # CSV entry count and validation status
        self.csv_status_label = QLabel()
        csv_layout.addWidget(self.csv_status_label)
        
        layout.addWidget(csv_group)
        layout.addStretch(1)  # Add space at the bottom
        
        self.tab_widget.addTab(ip_tab, "IP Assignment")
    
    def create_csv_help_tab(self):
        """Create the CSV format help tab"""
        help_tab = QWidget()
        layout = QVBoxLayout(help_tab)
        
        # Sequential format section
        seq_group = QGroupBox("Sequential Assignment Format")
        seq_layout = QVBoxLayout(seq_group)
        
        seq_text = QLabel(
            "<b>CSV Format:</b><br>"
            "Requires a single column CSV with header:<br>"
            "<code>FinalIPAddress</code><br><br>"
            "Example:<br>"
            "<code>FinalIPAddress<br>"
            "192.168.1.101<br>"
            "192.168.1.102<br>"
            "192.168.1.103</code>"
        )
        seq_text.setTextFormat(Qt.RichText)
        seq_text.setWordWrap(True)
        seq_layout.addWidget(seq_text)
        
        # Download button for sequential template
        seq_download_btn = QPushButton("Download Sequential Template")
        seq_download_btn.clicked.connect(lambda: self.save_csv_template("sequential"))
        seq_layout.addWidget(seq_download_btn)
        
        layout.addWidget(seq_group)
        
        # MAC-specific format section
        mac_group = QGroupBox("MAC-Specific Assignment Format")
        mac_layout = QVBoxLayout(mac_group)
        
        mac_text = QLabel(
            "<b>CSV Format:</b><br>"
            "Requires two columns CSV with headers:<br>"
            "<code>FinalIPAddress,MACAddress</code><br><br>"
            "MAC addresses must be in serial format with no delimiters (e.g., 00408C123456)<br><br>"
            "Example:<br>"
            "<code>FinalIPAddress,MACAddress<br>"
            "192.168.1.101,00408C123456<br>"
            "192.168.1.102,00408CAABBCC</code>"
        )
        mac_text.setTextFormat(Qt.RichText)
        mac_text.setWordWrap(True)
        mac_layout.addWidget(mac_text)
        
        # Download button for MAC-specific template
        mac_download_btn = QPushButton("Download MAC-Specific Template")
        mac_download_btn.clicked.connect(lambda: self.save_csv_template("mac_specific"))
        mac_layout.addWidget(mac_download_btn)
        
        layout.addWidget(mac_group)
        
        # Note about validation
        note_label = QLabel(
            "<b>Important Notes:</b><br>"
            "• The CSV must have the exact header shown above<br>"
            "• All IP addresses must be valid and in the same subnet<br>"
            "• For MAC-specific mode, each MAC address must correspond to a camera you're configuring<br>"
            "• The CSV file is validated when loaded to prevent issues during configuration"
        )
        note_label.setTextFormat(Qt.RichText)
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666;")
        layout.addWidget(note_label)
        
        layout.addStretch(1)  # Add space at the bottom
        
        self.tab_widget.addTab(help_tab, "CSV Help")
    
    @Slot()
    def update_mode_description(self):
        """Update the description text based on selected mode"""
        if self.sequential_radio.isChecked():
            self.mode_description.setText(
                "Sequential Assignment: Cameras will be assigned IPs in the order they are discovered, "
                "using the sequence of IP addresses from your CSV file."
            )
        else:
            self.mode_description.setText(
                "MAC-Specific Assignment: Each camera will be assigned an IP based on matching its MAC address "
                "to the corresponding entry in your CSV file."
            )
    
    @Slot()
    def load_csv(self):
        """Load and validate a CSV file"""
        # Determine which mode we're using
        is_mac_specific = self.mac_specific_radio.isChecked()
        mode = "mac_specific" if is_mac_specific else "sequential"
        
        # Ask user for file
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Load and validate the CSV
            if is_mac_specific:
                result = self.csv_handler.read_mac_specific_ip_list(file_path)
                # Result will be a dictionary mapping MAC addresses to IPs
                entry_count = len(result)
                
                # Update the CSV info
                self.csv_path = file_path
                self.csv_entries = result
                
                # Update UI with success message
                self.csv_path_label.setText(os.path.basename(file_path))
                self.csv_status_label.setText(
                    f"✓ Valid CSV loaded: Contains {entry_count} MAC-to-IP mappings"
                )
                self.csv_status_label.setStyleSheet("color: green;")
                
            else:  # Sequential mode
                result = self.csv_handler.read_sequential_ip_list(file_path)
                # Result will be a list of IP addresses
                entry_count = len(result)
                
                # Update the CSV info
                self.csv_path = file_path
                self.csv_entries = result
                
                # Update UI with success message
                self.csv_path_label.setText(os.path.basename(file_path))
                self.csv_status_label.setText(
                    f"✓ Valid CSV loaded: Contains {entry_count} sequential IP addresses"
                )
                self.csv_status_label.setStyleSheet("color: green;")
            
            self.log_message.emit(f"Loaded CSV file: {file_path}")
            self.log_message.emit(f"CSV contains {entry_count} entries")
            
        except Exception as e:
            # Show error message
            QMessageBox.warning(self, "CSV Error", str(e))
            self.log_message.emit(f"Error loading CSV file: {str(e)}")
            
            # Update UI with failure message
            self.csv_status_label.setText(f"✗ CSV validation failed: {str(e)}")
            self.csv_status_label.setStyleSheet("color: red;")
    
    @Slot()
    def save_csv_template(self, template_type):
        """Save a CSV template based on the template type"""
        if template_type == "sequential":
            template_content = "FinalIPAddress\n192.168.1.101\n192.168.1.102\n192.168.1.103"
            default_filename = "sequential_ip_template.csv"
        else:  # MAC-specific
            template_content = "FinalIPAddress,MACAddress\n192.168.1.101,00408C123456\n192.168.1.102,00408CAABBCC"
            default_filename = "mac_specific_ip_template.csv"
        
        # Let user choose where to save the template
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV Template", default_filename, "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(template_content)
                self.log_message.emit(f"CSV template saved to: {file_path}")
                QMessageBox.information(self, "Template Saved", f"CSV template saved to: {file_path}")
            except Exception as e:
                self.log_message.emit(f"Error saving CSV template: {str(e)}")
                QMessageBox.warning(self, "Error", f"Could not save CSV template: {str(e)}")
    
    def validate_and_accept(self):
        """Validate inputs before accepting dialog"""
        # Check subnet mask
        subnet = self.subnet_mask.text().strip()
        if not subnet:
            QMessageBox.warning(self, "Missing Information", "Subnet mask is required.")
            return
            
        # Default gateway is optional, but if provided should be a valid IP
        gateway = self.default_gateway.text().strip()
        
        # Check if a CSV file has been loaded
        if not self.csv_path or not self.csv_entries:
            result = QMessageBox.question(
                self, 
                "No CSV Loaded", 
                "No CSV file with IP assignments has been loaded. Would you like to load one now?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                self.load_csv()
                return  # Don't close dialog yet
            # If No, they might want to continue without a CSV, which could be handled elsewhere
        
        # Collect settings to return
        settings = {
            'subnet_mask': subnet,
            'default_gateway': gateway,
            'protocol': self.vapix_protocol.currentText(),
            'ip_mode': 'mac_specific' if self.mac_specific_radio.isChecked() else 'sequential',
            'csv_path': self.csv_path,
            'csv_entries': self.csv_entries
        }
        
        # Emit signal with settings
        self.settings_updated.emit(settings)
        
        # Close dialog
        self.accept()
    
    def save_settings_as_default(self):
        """Save the current network settings as default values"""
        try:
            settings = QSettings("AxisAutoConfig", "SetupTool")
            
            # Save basic network settings
            settings.setValue("DefaultSubnetMask", self.subnet_mask.text().strip())
            settings.setValue("DefaultGateway", self.default_gateway.text().strip())
            settings.setValue("DefaultProtocol", self.vapix_protocol.currentText())
            
            # Save IP assignment mode
            mode = "mac_specific" if self.mac_specific_radio.isChecked() else "sequential"
            settings.setValue("DefaultIPMode", mode)
            
            # Show confirmation message
            QMessageBox.information(
                self,
                "Settings Saved",
                "Current network settings have been saved as defaults for future use."
            )
            
            # Emit log message
            self.log_message.emit("Network settings saved as defaults")
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not save settings: {str(e)}"
            )
            self.log_message.emit(f"Error saving network settings: {str(e)}")
