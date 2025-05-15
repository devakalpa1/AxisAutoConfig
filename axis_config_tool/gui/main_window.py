#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
Main window implementation
"""

import sys
import os
import logging
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QLabel, QCheckBox, 
                             QLineEdit, QPushButton, QComboBox, QTextEdit, 
                             QSplitter, QFileDialog, QGroupBox, QTabWidget,
                             QFrame, QSpacerItem, QSizePolicy, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox, 
                             QApplication, QToolTip)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QThread, QSettings, QPoint, QTimer
from PySide6.QtGui import QFont, QPalette, QIcon, QColor, QCursor

# Import package modules
from axis_config_tool.core.dhcp_manager import DHCPManager
from axis_config_tool.core.camera_discovery import CameraDiscovery
from axis_config_tool.core.camera_operations import CameraOperations
from axis_config_tool.core.csv_handler import CSVHandler
from axis_config_tool.workers.unified_worker import DiscoveryWorker
from axis_config_tool.gui.about_dialog import AboutDialog
from axis_config_tool.gui.gui_tour import GUITour
from axis_config_tool.gui.user_creation_dialog import UserCreationDialog
from axis_config_tool.gui.dhcp_server_dialog import DHCPServerDialog
from axis_config_tool.gui.network_config_dialog import NetworkConfigDialog


class MainWindow(QMainWindow):
    """Main application window for the Axis Camera Unified Setup & Configuration Tool"""
    
    def __init__(self):
        super().__init__()
        
        self.dhcp_manager = DHCPManager()
        self.camera_discovery = CameraDiscovery()
        self.camera_operations = CameraOperations()
        self.csv_handler = CSVHandler()
        
        self.discovered_cameras = []
        self.dhcp_worker = None
        self.discovery_worker = None
        self.is_dhcp_running = False
        self.gui_tour = None
        
        self.init_ui()
        
        # Check if this is the first run to show the tour
        self.check_first_run()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("AxisAutoConfig v1.0.0")
        self.setMinimumSize(900, 700)
        
        # Set application icon if available
        icon_path = os.path.join("axis_config_tool", "resources", "app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create a horizontal splitter for the top two sections
        top_splitter = QSplitter(Qt.Horizontal)
        
        # Create a vertical splitter for the bottom sections and to hold the top splitter
        main_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(main_splitter)
        
        # Create the four main sections
        self.network_setup_section = self.create_network_setup_section()
        self.config_inputs_section = self.create_config_inputs_section()
        self.log_section = self.create_log_section()
        self.completion_section = self.create_completion_section()
        
        # Add the first two sections to the horizontal splitter
        top_splitter.addWidget(self.network_setup_section)
        top_splitter.addWidget(self.config_inputs_section)
        
        # Set equal initial sizes for the top sections
        top_splitter.setSizes([450, 450])
        
        # Add the horizontal splitter and other sections to the main vertical splitter
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.log_section)
        main_splitter.addWidget(self.completion_section)
        
        # Set initial sizes for the main splitter
        main_splitter.setSizes([450, 200, 50])
        
        # Create menu bar
        self.create_menu_bar()
        
        # Adapt to system theme
        self.adapt_to_system_theme()

    def check_first_run(self):
        """Check if this is the first application run and show tour if needed"""
        settings = QSettings("AxisAutoConfig", "SetupTool")
        first_run = settings.value("FirstRun", True, type=bool)
        show_tour = settings.value("ShowGUITour", True, type=bool)
        
        if first_run or show_tour:
            # Initialize the GUI tour if this is first run
            if not self.gui_tour:
                self.gui_tour = GUITour(self)
            
            # Show the tour after a short delay to ensure all widgets are properly rendered
            if first_run:
                settings.setValue("FirstRun", False)
                # Start the tour after the window appears
                QTimer.singleShot(500, self.start_gui_tour)
                
    def start_gui_tour(self):
        """Start the GUI tour"""
        if not self.gui_tour:
            self.gui_tour = GUITour(self)
        self.gui_tour.start_tour()
    
    def create_network_setup_section(self):
        """Create Section 1: Host PC Network Setup & DHCP Server Configuration"""
        section = QGroupBox("Network Setup & Camera Discovery")
        layout = QVBoxLayout(section)
        
        # Instructions panel at the top
        instructions = QGroupBox("Setup Instructions")
        instructions_layout = QVBoxLayout(instructions)
        instruction_steps = [
            "<b>Step 1:</b> Manually set your PC's IP address to a static IP on the camera network",
            "<b>Step 2:</b> Connect your PC directly to the camera(s) with an Ethernet switch",
            "<b>Step 3:</b> Configure and start the DHCP server using the button below",
            "<b>Step 4:</b> Power on your cameras and discover them on the network"
        ]
        
        for i, instruction in enumerate(instruction_steps):
            step_layout = QHBoxLayout()
            
            # Instruction text
            label = QLabel(instruction)
            label.setTextFormat(Qt.RichText)
            step_layout.addWidget(label, 1)
            
            # Help button with question mark
            help_btn = QPushButton("?")
            help_btn.setFixedSize(20, 20)
            help_btn.setToolTip("Click for more information")
            help_btn.clicked.connect(lambda checked, step=i: self.show_step_help(step))
            step_layout.addWidget(help_btn, 0)
            
            instructions_layout.addLayout(step_layout)
        
        layout.addWidget(instructions)
        
        # DHCP Server Button and Status
        dhcp_frame = QFrame()
        dhcp_layout = QHBoxLayout(dhcp_frame)
        
        self.dhcp_server_btn = QPushButton("Configure & Start DHCP Server")
        self.dhcp_server_btn.setMinimumHeight(40)  # Make button larger
        self.dhcp_server_btn.setStyleSheet("font-weight: bold;")
        self.dhcp_server_btn.clicked.connect(self.open_dhcp_server_dialog)
        dhcp_layout.addWidget(self.dhcp_server_btn)
        
        dhcp_layout.addWidget(QLabel("Status:"))
        self.dhcp_status_label = QLabel("Stopped")
        self.dhcp_status_label.setStyleSheet("color: red; font-weight: bold;")
        dhcp_layout.addWidget(self.dhcp_status_label)
        
        # Add stretch to push everything to the left
        dhcp_layout.addStretch(1)
        
        layout.addWidget(dhcp_frame)
        
        # Camera Discovery Section
        discovery_group = QGroupBox("Camera Discovery")
        discovery_layout = QVBoxLayout(discovery_group)
        
        discovery_button_layout = QHBoxLayout()
        self.discover_cameras_btn = QPushButton("Discover Cameras on DHCP Network")
        self.discover_cameras_btn.setEnabled(False)
        self.discover_cameras_btn.clicked.connect(self.discover_cameras)
        discovery_button_layout.addWidget(self.discover_cameras_btn)
        
        # Add refresh button
        refresh_discovery_btn = QPushButton("Refresh")
        refresh_discovery_btn.setToolTip("Refresh camera discovery")
        refresh_discovery_btn.clicked.connect(self.discover_cameras)
        refresh_discovery_btn.setEnabled(False)
        self.refresh_discovery_btn = refresh_discovery_btn
        discovery_button_layout.addWidget(refresh_discovery_btn)
        
        discovery_layout.addLayout(discovery_button_layout)
        
        # Discovered Cameras Table
        self.cameras_table = QTableWidget(0, 2)
        self.cameras_table.setHorizontalHeaderLabels(["Temporary DHCP IP", "MAC Address"])
        self.cameras_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        discovery_layout.addWidget(self.cameras_table)
        
        layout.addWidget(discovery_group)
        
        return section
    
    def create_config_inputs_section(self):
        """Create Section 2: Configuration Inputs"""
        section = QGroupBox("Camera Configuration Settings")
        layout = QVBoxLayout(section)
        
        # Configuration Inputs
        config_frame = QFrame()
        config_layout = QGridLayout(config_frame)
        
        row = 0
        
        # User Creation Settings 
        user_group = QGroupBox("User Creation Settings")
        user_layout = QVBoxLayout(user_group)
        
        user_summary = QLabel(
            "Configure the three-user workflow:\n"
            "• Root Admin (required)\n"
            "• Secondary Admin (optional)\n"
            "• ONVIF User (for client access)"
        )
        user_summary.setWordWrap(True)
        user_layout.addWidget(user_summary)
        
        # User credentials storage
        self.user_credentials = {
            "root_password": "",
            "secondary_username": "",
            "secondary_password": "",
            "onvif_username": "",
            "onvif_password": ""
        }
        
        # Button to open the user creation dialog
        user_dialog_btn = QPushButton("Configure User Creation Settings")
        user_dialog_btn.clicked.connect(self.configure_user_settings)
        user_layout.addWidget(user_dialog_btn)
        
        # Status label to show configuration status
        self.user_config_status = QLabel("Not configured yet")
        self.user_config_status.setStyleSheet("color: #888; font-style: italic;")
        user_layout.addWidget(self.user_config_status)
        
        # Add completed user group to main config layout
        config_layout.addWidget(user_group, row, 0, 1, 2)
        row += 1
        
        # Network Configuration Button and Status
        net_group = QGroupBox("Network Configuration Settings")
        net_layout = QVBoxLayout(net_group)
        
        # Button to launch network configuration dialog
        network_btn_layout = QHBoxLayout()
        configure_network_btn = QPushButton("Configure Network Settings...")
        configure_network_btn.clicked.connect(self.open_network_config_dialog)
        configure_network_btn.setMinimumHeight(36)  # Make button taller
        network_btn_layout.addWidget(configure_network_btn)
        
        # Status indicator
        self.network_config_status = QLabel("Not configured")
        self.network_config_status.setStyleSheet("color: #888; font-style: italic;")
        network_btn_layout.addWidget(self.network_config_status, 1)
        
        net_layout.addLayout(network_btn_layout)
        
        # Initialize network settings storage
        self.network_settings = {
            'subnet_mask': '255.255.255.0',
            'default_gateway': '',
            'protocol': 'HTTP',
            'ip_mode': 'sequential',
            'csv_path': '',
            'csv_entries': []
        }
        
        # Add the network group to the main config layout
        config_layout.addWidget(net_group, row, 0, 1, 2)
        row += 1
        
        layout.addWidget(config_frame)
        
        # Start Configuration Button
        config_button_frame = QFrame()
        config_button_layout = QHBoxLayout(config_button_frame)
        
        self.start_config_btn = QPushButton("Start Camera Pre-Configuration Process")
        self.start_config_btn.setEnabled(False)
        self.start_config_btn.clicked.connect(self.start_camera_configuration)
        self.start_config_btn.setMinimumHeight(40)  # Make button larger
        self.start_config_btn.setStyleSheet("font-weight: bold;")
        config_button_layout.addWidget(self.start_config_btn)
        
        # Progress indicator
        self.config_progress_label = QLabel("")
        config_button_layout.addWidget(self.config_progress_label)
        
        layout.addWidget(config_button_frame)
        
        return section
    
    def create_log_section(self):
        """Create Section 3: Pre-Configuration Process & Real-time Log"""
        section = QGroupBox("Pre-Configuration Process & Real-time Log")
        layout = QVBoxLayout(section)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        return section
    
    def create_completion_section(self):
        """Create Section 4: Completion & Next Steps / Save Report"""
        section = QGroupBox("Completion & Next Steps / Save Report")
        layout = QHBoxLayout(section)
        
        self.save_report_btn = QPushButton("Save Inventory Report...")
        self.save_report_btn.setEnabled(False)
        self.save_report_btn.clicked.connect(self.save_configuration_report)
        layout.addWidget(self.save_report_btn)
        
        # Result summary
        self.result_summary_label = QLabel("")
        layout.addWidget(self.result_summary_label)
        
        layout.addStretch()
        
        return section
    
    def create_menu_bar(self):
        """Create the application menu bar"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        # View documentation action
        view_docs_action = help_menu.addAction("View Documentation (README)")
        view_docs_action.triggered.connect(self.view_documentation)
        
        # Take GUI tour action
        tour_action = help_menu.addAction("Take GUI Tour")
        tour_action.triggered.connect(self.start_gui_tour)
        
        # About action
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
    
    def adapt_to_system_theme(self):
        """Adapt the application to the system theme (light/dark)"""
        app = QApplication.instance()
        if app.palette().color(QPalette.Window).lightness() < 128:
            # Dark mode detected
            self.log("System dark theme detected and applied")
        else:
            # Light mode detected
            self.log("System light theme detected and applied")
    
    @Slot()
    def open_dhcp_server_dialog(self):
        """Open the DHCP server configuration dialog"""
        
        # If dialog doesn't exist yet, create it
        if not hasattr(self, 'dhcp_dialog') or self.dhcp_dialog is None:
            self.dhcp_dialog = DHCPServerDialog(self.dhcp_manager, self)
            
            # Connect signals from the dialog
            self.dhcp_dialog.dhcp_started.connect(self.on_dhcp_started)
            self.dhcp_dialog.dhcp_stopped.connect(self.on_dhcp_stopped)
            self.dhcp_dialog.dhcp_status_update.connect(self.update_dhcp_status)
            self.dhcp_dialog.log_message.connect(self.log)
        
        # Show the dialog
        self.dhcp_dialog.show()
        self.dhcp_dialog.raise_()
        self.dhcp_dialog.activateWindow()
    
    def on_dhcp_started(self, server_ip):
        """Handle DHCP server started signal from dialog"""
        self.is_dhcp_running = True
        self.discover_cameras_btn.setEnabled(True)
        self.refresh_discovery_btn.setEnabled(True)
        self.dhcp_server_btn.setText("DHCP Server Configuration...")
        
        self.log(f"DHCP server started successfully on {server_ip}")
    
    def on_dhcp_stopped(self):
        """Handle DHCP server stopped signal from dialog"""
        self.is_dhcp_running = False
        self.discover_cameras_btn.setEnabled(False)
        self.refresh_discovery_btn.setEnabled(False)
        self.dhcp_server_btn.setText("Configure & Start DHCP Server")
        
        self.log("DHCP server stopped")
    
    @Slot(str)
    def update_dhcp_status(self, status):
        """Update the DHCP server status label"""
        self.dhcp_status_label.setText(status)
        if status == "Running":
            self.dhcp_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.dhcp_status_label.setStyleSheet("color: red; font-weight: bold;")
    
    @Slot()
    def discover_cameras(self):
        """Discover cameras on the DHCP network"""
        if not self.is_dhcp_running:
            self.log("DHCP server must be running to discover cameras")
            return
            
        # Clear previous results
        self.cameras_table.setRowCount(0)
        self.discovered_cameras = []
        
        # Start discovery in worker thread
        try:
            # Get leases from DHCP manager via the dialog
            if hasattr(self, 'dhcp_dialog') and self.dhcp_dialog is not None:
                leases = self.dhcp_manager.get_active_leases()
                
                self.discovery_worker = DiscoveryWorker(
                    self.camera_discovery, 
                    leases
                )
                self.discovery_worker.camera_found.connect(self.add_discovered_camera)
                self.discovery_worker.log_message.connect(self.log)
                self.discovery_worker.finished.connect(self.discovery_completed)
                
                # Update UI
                self.discover_cameras_btn.setEnabled(False)
                self.refresh_discovery_btn.setEnabled(False)
                
                self.discovery_worker.start()
                self.log("Starting camera discovery...")
            else:
                self.log("Error: DHCP server must be configured and running to discover cameras")
        except Exception as e:
            self.log(f"Error during camera discovery: {str(e)}")
            self.discover_cameras_btn.setEnabled(True)
    
    @Slot(str, str)
    def add_discovered_camera(self, ip, mac):
        """Add a discovered camera to the table"""
        row = self.cameras_table.rowCount()
        self.cameras_table.insertRow(row)
        self.cameras_table.setItem(row, 0, QTableWidgetItem(ip))
        self.cameras_table.setItem(row, 1, QTableWidgetItem(mac))
        
        self.discovered_cameras.append({"ip": ip, "mac": mac})
        self.log(f"Discovered camera: IP {ip}, MAC {mac}")
    
    @Slot()
    def discovery_completed(self):
        """Called when camera discovery is complete"""
        self.discover_cameras_btn.setEnabled(True)
        self.log(f"Camera discovery completed. Found {len(self.discovered_cameras)} potential Axis camera(s).")
        
        # Enable start config button if we have cameras and a CSV
        if len(self.discovered_cameras) > 0 and hasattr(self, 'csv_path_label') and os.path.exists(self.csv_path_label.text()):
            self.start_config_btn.setEnabled(True)
            
        # Re-enable discovery buttons
        self.discover_cameras_btn.setEnabled(True)
        self.refresh_discovery_btn.setEnabled(True)
    
    @Slot()
    def open_network_config_dialog(self):
        """Open the network configuration dialog"""
        
        # If dialog doesn't exist yet, create it
        dialog = NetworkConfigDialog(self.csv_handler, self)
            
        # Connect signals from the dialog
        dialog.settings_updated.connect(self.update_network_settings)
        dialog.log_message.connect(self.log)
        
        # Initialize dialog with current settings
        if self.network_settings.get('csv_path'):
            dialog.csv_path = self.network_settings.get('csv_path')
            dialog.csv_path_label.setText(os.path.basename(dialog.csv_path))
        
        dialog.subnet_mask.setText(self.network_settings.get('subnet_mask', '255.255.255.0'))
        dialog.default_gateway.setText(self.network_settings.get('default_gateway', ''))
        
        # Set the protocol
        protocol_idx = 0  # Default to HTTP
        if self.network_settings.get('protocol') == 'HTTPS':
            protocol_idx = 1
        dialog.vapix_protocol.setCurrentIndex(protocol_idx)
        
        # Set the IP assignment mode
        if self.network_settings.get('ip_mode') == 'mac_specific':
            dialog.mac_specific_radio.setChecked(True)
        else:
            dialog.sequential_radio.setChecked(True)
        
        # Show the dialog
        if dialog.exec():
            self.log("Network configuration updated")
        else:
            self.log("Network configuration cancelled")
    
    @Slot(dict)
    def update_network_settings(self, settings):
        """Update network settings from the dialog"""
        self.network_settings = settings
        
        # Update status label
        if settings.get('csv_path'):
            csv_filename = os.path.basename(settings.get('csv_path', ''))
            entries_count = len(settings.get('csv_entries', []))
            
            # Update the status label
            self.network_config_status.setText(
                f"✓ {entries_count} IPs loaded from {csv_filename} | " 
                f"Mode: {settings.get('ip_mode', 'sequential').title()}"
            )
            self.network_config_status.setStyleSheet("color: green; font-weight: normal;")
            
            # Enable start config button if we have cameras
            if len(self.discovered_cameras) > 0:
                self.start_config_btn.setEnabled(True)
        else:
            self.network_config_status.setText("⚠ No CSV file loaded")
            self.network_config_status.setStyleSheet("color: orange; font-weight: normal;")
    
    def show_step_help(self, step):
        """Show detailed help for a specific setup step as a tooltip"""
        help_texts = [
            "To set a static IP on Windows:\n1. Open Network Connections\n2. Right-click your network adapter\n" 
            "3. Select Properties\n4. Select IPv4\n5. Enter a static IP in the same subnet as your cameras",
            
            "Use a standard Ethernet switch to connect your PC and all cameras.\n"
            "Do not connect to your production network during initial setup.",
            
            "Open the DHCP server configuration dialog to set up and start a DHCP server.\n"
            "The DHCP server will provide temporary IP addresses to factory-new cameras.",
            
            "Once the DHCP server is running, power on your cameras one at a time.\n"
            "Wait approximately 30 seconds between powering on each camera.\n"
            "Then click 'Discover Cameras' to detect them on the network."
        ]
        
        # Get the global position of the button that was clicked
        btn = self.sender()
        if btn:
            global_pos = btn.mapToGlobal(btn.rect().topRight())
            # Show the tooltip slightly offset from the button
            QToolTip.showText(global_pos, help_texts[step], btn)
        else:
            # Fallback to cursor position if sender not found
            QToolTip.showText(QCursor.pos(), help_texts[step], self)
        
    
    @Slot()
    def show_about(self):
        """Show the about dialog"""
        dialog = AboutDialog(self)
        dialog.exec()
        
    @Slot()
    def configure_user_settings(self):
        """Open the user creation settings dialog"""
        dialog = UserCreationDialog(self)
        
        # Pre-populate dialog with any existing values
        if self.user_credentials["root_password"]:
            dialog.root_password.setText(self.user_credentials["root_password"])
        if self.user_credentials["secondary_username"]:
            dialog.secondary_username.setText(self.user_credentials["secondary_username"])
        if self.user_credentials["onvif_username"]:
            dialog.onvif_username.setText(self.user_credentials["onvif_username"])
        if self.user_credentials["onvif_password"]:
            dialog.onvif_password.setText(self.user_credentials["onvif_password"])
            
        # Show dialog and wait for user response
        if dialog.exec():
            # User clicked OK, get the credentials
            credentials = dialog.get_user_credentials()
            self.user_credentials = credentials
            
            # Update status label
            status_text = "Configured: Root admin"
            if credentials["secondary_username"]:
                status_text += f", Secondary admin ({credentials['secondary_username']})"
            if credentials["onvif_username"]:
                status_text += f", ONVIF user ({credentials['onvif_username']})"
            
            self.user_config_status.setText(status_text)
            self.user_config_status.setStyleSheet("color: green; font-weight: bold;")
            
            self.log("User creation settings configured successfully")
        else:
            # User cancelled the dialog
            self.log("User creation settings configuration cancelled")
    
    @Slot()
    def show_user_creation_help(self):
        """Show help about the three-user creation workflow"""
        help_text = (
            "<h3>Three-User Creation Workflow</h3>"
            "<p><b>Step 1: Root Administrator Creation</b><br>"
            "On factory-new cameras, the first admin user <b>must be named 'root'</b>.<br>"
            "This is a requirement of Axis OS v10 and will be created without authentication.</p>"
            
            "<p><b>Step 2: Secondary Administrator (Optional)</b><br>"
            "After the root admin is created, you can optionally create a secondary<br>"
            "administrator with a custom username of your choice.<br>"
            "This user will have the same password as the root admin.</p>"
            
            "<p><b>Step 3: ONVIF User Creation</b><br>"
            "This user will be specifically for ONVIF client access to the camera.<br>"
            "It will be created with appropriate ONVIF group permissions.</p>"
            
            "<p>The configuration process will then:<br>"
            "- Turn off WDR (Wide Dynamic Range)<br>"
            "- Turn off Replay Protection<br>"
            "- Set the final static IP address<br>"
            "All these operations will authenticate as the root user.</p>"
        )
        
        QMessageBox.information(self, "User Creation Workflow Help", help_text)
    
    
    @Slot()
    def view_documentation(self):
        """Open the README.md file in the default text editor or browser"""
        readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "README.md")
        
        # Handle both development and PyInstaller environments
        if not os.path.exists(readme_path):
            # If bundled with PyInstaller
            base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
            readme_path = os.path.join(base_path, "README.md")
        
        if os.path.exists(readme_path):
            # Open README with default application
            if sys.platform == 'win32':
                os.startfile(readme_path)
            else:
                import subprocess
                subprocess.call(('xdg-open', readme_path))
        else:
            QMessageBox.warning(self, "Documentation Not Found",
                             "README.md file could not be located.")
    
    def log(self, message):
        """Add a message to the log area"""
        self.log_text.append(f"{message}")
    
    @Slot()
    def start_camera_configuration(self):
        """Start the camera configuration process"""
        # Check if we have cameras and network settings with CSV
        if not self.discovered_cameras:
            QMessageBox.warning(self, "Configuration Error", "No cameras discovered. Please discover cameras first.")
            return
            
        if not self.network_settings or not self.network_settings.get('csv_entries'):
            QMessageBox.warning(self, "Configuration Error", 
                "Network configuration is incomplete. Please configure network settings and load a CSV file.")
            return
            
        # Check if user credentials are configured
        if not self.user_credentials["root_password"]:
            result = QMessageBox.question(
                self,
                "User Credentials Required",
                "No user credentials configured. Would you like to configure them now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.Yes:
                self.configure_user_settings()
            return
        
        # Collect configuration parameters
        config_params = {}
        
        # User credentials
        config_params['admin_user'] = 'root'  # Force to 'root' for Axis OS v10
        config_params['admin_pass'] = self.user_credentials["root_password"]
        
        # Secondary admin and ONVIF user
        config_params['secondary_username'] = self.user_credentials["secondary_username"]
        config_params['secondary_pass'] = self.user_credentials["secondary_password"]
        config_params['onvif_user'] = self.user_credentials["onvif_username"]
        config_params['onvif_pass'] = self.user_credentials["onvif_password"]
        
        # Network configuration from dialog
        config_params['subnet_mask'] = self.network_settings.get('subnet_mask', '255.255.255.0')
        config_params['gateway'] = self.network_settings.get('default_gateway', '')
        config_params['protocol'] = self.network_settings.get('protocol', 'HTTP')
        config_params['ip_mode'] = self.network_settings.get('ip_mode', 'sequential')
        
        # IP list from network settings
        if config_params['ip_mode'] == 'sequential':
            # For sequential mode, entries should be a list of IPs
            config_params['ip_list'] = self.network_settings.get('csv_entries', [])
        else:
            # For MAC-specific mode, entries should already be a dictionary
            config_params['ip_list'] = self.network_settings.get('csv_entries', {})
        
        # Confirm with the user
        camera_count = len(self.discovered_cameras)
        ip_count = len(config_params['ip_list'])
        
        confirm_msg = (
            f"Ready to configure {camera_count} camera(s) with the following settings:\n\n"
            f"- Root Administrator Password: {'*'*len(config_params['admin_pass'])}\n"
        )
        
        if config_params['secondary_username']:
            confirm_msg += f"- Secondary Administrator: {config_params['secondary_username']}\n"
        
        if config_params['onvif_user']:
            confirm_msg += f"- ONVIF User: {config_params['onvif_user']}\n"
            
        confirm_msg += (
            f"- Subnet Mask: {config_params['subnet_mask']}\n"
            f"- Default Gateway: {config_params['gateway'] or 'None'}\n"
            f"- Protocol: {config_params['protocol']}\n"
            f"- IP Assignment Mode: {config_params['ip_mode'].title()}\n"
            f"- Available IPs in CSV: {ip_count}\n\n"
            "The following operations will be performed on each camera:\n"
            "1. Set root administrator password\n"
        )
        
        if config_params['secondary_username']:
            confirm_msg += "2. Create secondary administrator account\n"
            
        if config_params['onvif_user']:
            confirm_msg += "3. Create ONVIF user account\n"
            
        confirm_msg += (
            "4. Turn off WDR (Wide Dynamic Range)\n"
            "5. Turn off Replay Attack Protection\n"
            "6. Assign final static IP address\n\n"
            "This process may take several minutes. Proceed?"
        )
        
        reply = QMessageBox.question(
            self, 
            "Confirm Camera Configuration",
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
            
        # Disable configuration button during the process
        self.start_config_btn.setEnabled(False)
        self.config_progress_label.setText("0 / 0 cameras")
        self.result_summary_label.setText("")
        self.save_report_btn.setEnabled(False)
        
        # Create and start the configuration worker
        from axis_config_tool.workers.unified_worker import ConfigurationWorker
        
        self.config_worker = ConfigurationWorker(
            self.camera_operations,
            self.discovered_cameras,
            config_params
        )
        
        # Connect signals
        self.config_worker.log_message.connect(self.log)
        self.config_worker.progress_update.connect(self.update_config_progress)
        self.config_worker.camera_configured.connect(self.on_camera_configured)
        self.config_worker.configuration_complete.connect(self.on_configuration_complete)
        
        # Start the worker
        self.log("Starting camera configuration process...")
        self.config_worker.start()
    
    @Slot(int, int)
    def update_config_progress(self, current, total):
        """Update the configuration progress label"""
        self.config_progress_label.setText(f"{current} / {total} cameras")
    
    @Slot(str, bool, dict)
    def on_camera_configured(self, ip, success, details):
        """Handle completion of configuration for a single camera"""
        if success:
            self.log(f"Camera at {ip} successfully configured")
        else:
            temp_ip = details.get('temp_ip', ip)
            status = details.get('status', 'Unknown Error')
            self.log(f"Camera at {temp_ip} failed: {status}")
    
    @Slot(list)
    def on_configuration_complete(self, results):
        """Handle completion of all camera configurations"""
        # Re-enable the configuration button
        self.start_config_btn.setEnabled(True)
        
        # Calculate success/failure statistics
        success_count = len([r for r in results if r.get('status') == 'Success'])
        total_count = len(results)
        
        # Update result summary
        self.result_summary_label.setText(
            f"Results: {success_count} of {total_count} cameras successfully configured"
        )
        
        # Store results for reporting
        self.config_results = results
        
        # Enable the save report button
        self.save_report_btn.setEnabled(True)
        
        # Show completion message
        if success_count == total_count:
            QMessageBox.information(
                self,
                "Configuration Complete",
                f"All {total_count} camera(s) were successfully configured."
            )
        else:
            QMessageBox.warning(
                self,
                "Configuration Partial",
                f"{success_count} of {total_count} camera(s) were successfully configured. "
                f"Check the log for details on failures."
            )
    
    @Slot()
    def save_configuration_report(self):
        """Save a CSV report of the configuration results"""
        if not hasattr(self, 'config_results') or not self.config_results:
            QMessageBox.warning(self, "No Data", "No configuration results to save.")
            return
            
        # Ask user for file location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration Report",
            "camera_configuration_report.csv",
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
            
        try:
            # Generate CSV content
            csv_content = "Original IP,MAC Address,Final IP,Status,Root Admin,Secondary Admin,ONVIF User,WDR Off,Replay Protection Off\n"
            
            for result in self.config_results:
                temp_ip = result.get('temp_ip', 'N/A')
                mac = result.get('mac', 'N/A')
                final_ip = result.get('final_ip', 'N/A')
                status = result.get('status', 'N/A')
                
                operations = result.get('operations', {})
                root_admin = "Success" if operations.get('root_admin', {}).get('success', False) else "Failed"
                secondary_admin = "Success" if operations.get('secondary_admin', {}).get('success', False) else "N/A"
                onvif_user = "Success" if operations.get('onvif_user', {}).get('success', False) else "N/A"
                wdr_off = "Success" if operations.get('wdr_off', {}).get('success', False) else "Failed"
                replay_off = "Success" if operations.get('replay_protection_off', {}).get('success', False) else "Failed"
                
                csv_content += f"{temp_ip},{mac},{final_ip},{status},{root_admin},{secondary_admin},{onvif_user},{wdr_off},{replay_off}\n"
                
            # Write to file
            with open(file_path, 'w') as f:
                f.write(csv_content)
                
            self.log(f"Configuration report saved to {file_path}")
            
            # Ask if user wants to open the file
            reply = QMessageBox.question(
                self,
                "Report Saved",
                f"Report saved to {file_path}. Do you want to open it now?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if sys.platform == 'win32':
                    os.startfile(file_path)
                else:
                    import subprocess
                    subprocess.call(('xdg-open', file_path))
                    
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Error saving report: {str(e)}")
            self.log(f"Error saving configuration report: {str(e)}")

    def closeEvent(self, event):
        """Handle application close event"""
        if self.is_dhcp_running:
            # If we have a DHCP dialog with running server, stop it
            if hasattr(self, 'dhcp_dialog') and self.dhcp_dialog is not None:
                self.dhcp_dialog.stop_dhcp_server()
        
        # If configuration is in progress, ask before closing
        if hasattr(self, 'config_worker') and self.config_worker and self.config_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Configuration In Progress",
                "Camera configuration is still in progress. Closing now will interrupt the process. "
                "Are you sure you want to close?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Stop the worker gracefully
                self.config_worker.stop()
                self.config_worker.wait()
            else:
                event.ignore()
                return
            
        event.accept()
