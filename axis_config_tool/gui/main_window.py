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
from axis_config_tool.workers.unified_worker import DHCPWorker, DiscoveryWorker
from axis_config_tool.gui.about_dialog import AboutDialog
from axis_config_tool.gui.gui_tour import GUITour
from axis_config_tool.gui.user_creation_dialog import UserCreationDialog


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
        self.setWindowTitle("Axis Camera Unified Setup & Configuration Tool")
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
        section = QGroupBox("Host PC Network Setup & DHCP Server Configuration")
        layout = QVBoxLayout(section)
        
        # Instructions panel at the top
        instructions = QGroupBox("Setup Instructions")
        instructions_layout = QVBoxLayout(instructions)
        instruction_steps = [
            "<b>Step 1:</b> Manually set your PC's IP address to a static IP on the camera network",
            "<b>Step 2:</b> Connect your PC directly to the camera(s) with an Ethernet switch",
            "<b>Step 3:</b> Select a network interface and configure DHCP server settings below",
            "<b>Step 4:</b> Start the DHCP server and power on your cameras"
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
        
        # Network Interface Detection
        network_frame = QFrame()
        network_layout = QGridLayout(network_frame)
        
        network_layout.addWidget(QLabel("Available Network Interfaces:"), 0, 0)
        self.network_interfaces_combo = QComboBox()
        network_layout.addWidget(self.network_interfaces_combo, 0, 1)
        
        refresh_btn = QPushButton("Refresh Network Interfaces")
        refresh_btn.clicked.connect(self.refresh_network_interfaces)
        network_layout.addWidget(refresh_btn, 0, 2)
        
        network_layout.addWidget(QLabel("DHCP Server IP (This PC's Static IP):"), 1, 0)
        self.dhcp_server_ip = QLineEdit()
        network_layout.addWidget(self.dhcp_server_ip, 1, 1)
        
        layout.addWidget(network_frame)
        
        # DHCP Configuration
        dhcp_frame = QFrame()
        dhcp_layout = QGridLayout(dhcp_frame)
        
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
        
        layout.addWidget(dhcp_frame)
        
        # DHCP Server Controls
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        
        self.start_dhcp_btn = QPushButton("Start DHCP Server")
        self.start_dhcp_btn.clicked.connect(self.start_dhcp_server)
        controls_layout.addWidget(self.start_dhcp_btn)
        
        self.stop_dhcp_btn = QPushButton("Stop DHCP Server")
        self.stop_dhcp_btn.clicked.connect(self.stop_dhcp_server)
        self.stop_dhcp_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_dhcp_btn)
        
        layout.addWidget(controls_frame)
        
        # DHCP Status
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        
        status_layout.addWidget(QLabel("DHCP Server Status:"))
        self.dhcp_status_label = QLabel("Stopped")
        self.dhcp_status_label.setStyleSheet("color: red;")
        status_layout.addWidget(self.dhcp_status_label)
        
        layout.addWidget(status_frame)
        
        # Initialize with default settings
        self.toggle_dhcp_inputs(Qt.Checked)
        
        return section
    
    def create_config_inputs_section(self):
        """Create Section 2: Camera Discovery & Configuration Inputs"""
        section = QGroupBox("Camera Discovery & Configuration Inputs")
        layout = QVBoxLayout(section)
        
        # Camera Discovery
        discovery_frame = QFrame()
        discovery_layout = QHBoxLayout(discovery_frame)
        
        self.discover_cameras_btn = QPushButton("Discover Cameras on DHCP Network")
        self.discover_cameras_btn.clicked.connect(self.discover_cameras)
        self.discover_cameras_btn.setEnabled(False)
        discovery_layout.addWidget(self.discover_cameras_btn)
        
        layout.addWidget(discovery_frame)
        
        # Discovered Cameras Table
        self.cameras_table = QTableWidget(0, 2)
        self.cameras_table.setHorizontalHeaderLabels(["Temporary DHCP IP", "MAC Address"])
        self.cameras_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.cameras_table)
        
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
        
        # Network Configuration Group Box
        net_group = QGroupBox("Network Configuration Settings")
        net_layout = QGridLayout(net_group)
        net_row = 0
        
        net_layout.addWidget(QLabel("Final Static Subnet Mask:"), net_row, 0)
        self.subnet_mask = QLineEdit("255.255.255.0")
        net_layout.addWidget(self.subnet_mask, net_row, 1)
        net_row += 1
        
        net_layout.addWidget(QLabel("Final Static Default Gateway:"), net_row, 0)
        self.default_gateway = QLineEdit()
        net_layout.addWidget(self.default_gateway, net_row, 1)
        net_row += 1
        
        net_layout.addWidget(QLabel("VAPIX Protocol for Config:"), net_row, 0)
        self.vapix_protocol = QComboBox()
        self.vapix_protocol.addItems(["HTTP", "HTTPS"])
        net_layout.addWidget(self.vapix_protocol, net_row, 1)
        net_row += 1
        
        # IP Assignment Mode section
        net_layout.addWidget(QLabel("Final IP Assignment Mode:"), net_row, 0)
        
        mode_layout = QHBoxLayout()
        self.ip_mode_combo = QComboBox()
        self.ip_mode_combo.addItems(["Sequential Assignment", "MAC-Specific Assignment"])
        
        mode_help_btn = QPushButton("?")
        mode_help_btn.setFixedSize(24, 24)
        mode_help_btn.setToolTip("Click for help about assignment modes")
        mode_help_btn.clicked.connect(self.show_ip_mode_help)
        
        mode_layout.addWidget(self.ip_mode_combo)
        mode_layout.addWidget(mode_help_btn)
        mode_layout.addStretch(1)
        
        net_layout.addLayout(mode_layout, net_row, 1)
        
        # Add the network group to the main config layout
        config_layout.addWidget(net_group, row, 0, 1, 2)
        row += 1
        
        layout.addWidget(config_frame)
        
        # CSV Format Help Box
        csv_format_group = QGroupBox("CSV Format Information")
        csv_format_layout = QVBoxLayout(csv_format_group)
        
        self.csv_format_label = QLabel()
        self.csv_format_label.setTextFormat(Qt.RichText)
        self.csv_format_label.setWordWrap(True)
        
        # Add download template link
        template_layout = QHBoxLayout()
        template_layout.addWidget(self.csv_format_label)
        
        download_template_btn = QPushButton("Download CSV Template")
        download_template_btn.setFixedWidth(150)
        download_template_btn.clicked.connect(self.save_csv_template)
        template_layout.addWidget(download_template_btn, 0, Qt.AlignTop | Qt.AlignRight)
        
        csv_format_layout.addLayout(template_layout)
        
        layout.addWidget(csv_format_group)
        
        # CSV Input
        csv_frame = QFrame()
        csv_layout = QHBoxLayout(csv_frame)
        
        self.load_csv_btn = QPushButton("Load Final Static IP List (CSV)...")
        self.load_csv_btn.clicked.connect(self.load_csv)
        csv_layout.addWidget(self.load_csv_btn)
        
        self.csv_path_label = QLabel("No CSV file loaded")
        csv_layout.addWidget(self.csv_path_label)
        
        layout.addWidget(csv_frame)
        
        # Start Configuration Button
        config_button_frame = QFrame()
        config_button_layout = QHBoxLayout(config_button_frame)
        
        self.start_config_btn = QPushButton("Start Camera Pre-Configuration Process")
        self.start_config_btn.setEnabled(False)
        config_button_layout.addWidget(self.start_config_btn)
        
        layout.addWidget(config_button_frame)
        
        # Connect signals for CSV format explanation
        self.ip_mode_combo.currentIndexChanged.connect(self.update_csv_format_text)
        
        # Initialize CSV format text
        self.update_csv_format_text(self.ip_mode_combo.currentIndex())
        
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
        
        # Phase 3 implementation
        save_report_btn = QPushButton("Save Inventory Report...")
        save_report_btn.setEnabled(False)
        layout.addWidget(save_report_btn)
        
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
    def refresh_network_interfaces(self):
        """Refresh the list of available network interfaces"""
        self.network_interfaces_combo.clear()
        
        try:
            interfaces = self.dhcp_manager.get_network_interfaces()
            for interface_name, interface_details in interfaces.items():
                if interface_details.get("ipv4"):
                    display_text = f"{interface_name} - {interface_details['ipv4']}"
                    self.network_interfaces_combo.addItem(display_text, interface_name)
            
            if self.network_interfaces_combo.count() > 0:
                self.log("Network interfaces refreshed successfully")
            else:
                self.log("No network interfaces with IPv4 addresses found")
        except Exception as e:
            self.log(f"Error refreshing network interfaces: {str(e)}")
    
    @Slot(int)
    def toggle_dhcp_inputs(self, state):
        """Toggle DHCP configuration input fields based on checkbox state"""
        enabled = state != Qt.Checked
        self.dhcp_start_ip.setEnabled(enabled)
        self.dhcp_end_ip.setEnabled(enabled)
        self.dhcp_lease_time.setEnabled(enabled)
    
    @Slot()
    def start_dhcp_server(self):
        """Start the DHCP server"""
        if not self.network_interfaces_combo.currentData():
            self.log("Error: No network interface selected")
            return
            
        if not self.dhcp_server_ip.text():
            self.log("Error: DHCP Server IP (This PC's Static IP) is required")
            return
            
        # Get configuration values
        interface = self.network_interfaces_combo.currentData()
        server_ip = self.dhcp_server_ip.text()
        start_ip = self.dhcp_start_ip.text()
        end_ip = self.dhcp_end_ip.text()
        lease_time = int(self.dhcp_lease_time.text())
        
        # Configure DHCP server
        try:
            self.dhcp_manager.configure(
                interface=interface, 
                server_ip=server_ip,
                start_ip=start_ip,
                end_ip=end_ip,
                lease_time=lease_time
            )
            
            # Start DHCP server in worker thread
            self.dhcp_worker = DHCPWorker(self.dhcp_manager)
            self.dhcp_worker.status_update.connect(self.update_dhcp_status)
            self.dhcp_worker.log_message.connect(self.log)
            self.dhcp_worker.start()
            
            # Update UI
            self.start_dhcp_btn.setEnabled(False)
            self.stop_dhcp_btn.setEnabled(True)
            self.discover_cameras_btn.setEnabled(True)
            self.is_dhcp_running = True
            
            self.log(f"DHCP server starting on {interface} with IP range {start_ip} to {end_ip}")
        except Exception as e:
            self.log(f"Error starting DHCP server: {str(e)}")
    
    @Slot()
    def stop_dhcp_server(self):
        """Stop the DHCP server"""
        if self.dhcp_worker and self.is_dhcp_running:
            try:
                # Signal worker to stop
                self.dhcp_worker.stop()
                self.dhcp_worker = None
                
                # Update UI
                self.start_dhcp_btn.setEnabled(True)
                self.stop_dhcp_btn.setEnabled(False)
                self.discover_cameras_btn.setEnabled(False)
                self.is_dhcp_running = False
                self.update_dhcp_status("Stopped")
                
                self.log("DHCP server stopped")
            except Exception as e:
                self.log(f"Error stopping DHCP server: {str(e)}")
    
    @Slot(str)
    def update_dhcp_status(self, status):
        """Update the DHCP server status label"""
        self.dhcp_status_label.setText(status)
        if status == "Running":
            self.dhcp_status_label.setStyleSheet("color: green;")
        else:
            self.dhcp_status_label.setStyleSheet("color: red;")
    
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
            
            self.discovery_worker.start()
            self.log("Starting camera discovery...")
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
        if len(self.discovered_cameras) > 0 and os.path.exists(self.csv_path_label.text()):
            self.start_config_btn.setEnabled(True)
    
    @Slot()
    def load_csv(self):
        """Load CSV file with final static IP assignments"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
        
        if file_path:
            try:
                result = self.csv_handler.read_ip_list(file_path)
                self.csv_path_label.setText(file_path)  # Store full path
                self.log(f"Loaded CSV file: {file_path}")
                self.log(f"CSV contains {len(result)} IP address entries")
                
                # Enable start config button if we have cameras and a CSV
                if len(self.discovered_cameras) > 0:
                    self.start_config_btn.setEnabled(True)
            except Exception as e:
                self.log(f"Error loading CSV file: {str(e)}")
                QMessageBox.warning(self, "CSV Error", str(e))
    
    @Slot()
    def update_csv_format_text(self, index):
        """Update the CSV format explanation based on selected mode"""
        if index == 0:  # Sequential
            self.csv_format_label.setText(
                "<b>Sequential Assignment CSV Format:</b><br>"
                "Requires a single column CSV with header:<br>"
                "<code>FinalIPAddress</code><br><br>"
                "Example:<br>"
                "<code>FinalIPAddress<br>"
                "192.168.1.101<br>"
                "192.168.1.102<br>"
                "192.168.1.103</code>"
            )
        else:  # MAC-specific
            self.csv_format_label.setText(
                "<b>MAC-Specific Assignment CSV Format:</b><br>"
                "Requires two columns CSV with headers:<br>"
                "<code>MACAddress,FinalIPAddress</code><br><br>"
                "MAC addresses must be in serial format (e.g., 00408C123456)<br><br>"
                "Example:<br>"
                "<code>MACAddress,FinalIPAddress<br>"
                "00408C123456,192.168.1.101<br>"
                "00408CAABBCC,192.168.1.102</code>"
            )
    
    def show_step_help(self, step):
        """Show detailed help for a specific setup step as a tooltip"""
        help_texts = [
            "To set a static IP on Windows:\n1. Open Network Connections\n2. Right-click your network adapter\n" 
            "3. Select Properties\n4. Select IPv4\n5. Enter a static IP in the same subnet as your cameras",
            
            "Use a standard Ethernet switch to connect your PC and all cameras.\n"
            "Do not connect to your production network during initial setup.",
            
            "Select the network interface connected to the cameras.\n"
            "The DHCP server will provide temporary IP addresses to factory-new cameras.",
            
            "Once the DHCP server is running, power on your cameras one at a time.\n"
            "Wait approximately 30 seconds between powering on each camera."
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
        
    def show_ip_mode_help(self):
        """Show help about IP assignment modes as a tooltip"""
        help_text = (
            "<b>Sequential Assignment:</b><br>"
            "Cameras will be assigned IPs in the order they are discovered, "
            "using the sequence of IP addresses from your CSV file.<br><br>"
            "<b>MAC-Specific Assignment:</b><br>"
            "Each camera will be assigned an IP based on matching its MAC address "
            "to the corresponding entry in your CSV file."
        )
        
        # Get the global position of the button that was clicked
        btn = self.sender()
        if btn:
            global_pos = btn.mapToGlobal(btn.rect().topRight())
            # Show the tooltip slightly offset from the button
            QToolTip.showText(global_pos, help_text, btn)
        else:
            # Fallback to cursor position if sender not found
            QToolTip.showText(QCursor.pos(), help_text, self)
    
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
    def save_csv_template(self):
        """Save a CSV template based on the currently selected IP assignment mode"""
        mode_index = self.ip_mode_combo.currentIndex()
        
        if mode_index == 0:  # Sequential
            template_content = "FinalIPAddress\n192.168.1.101\n192.168.1.102\n192.168.1.103"
            default_filename = "sequential_ip_template.csv"
        else:  # MAC-specific
            template_content = "MACAddress,FinalIPAddress\n00408C123456,192.168.1.101\n00408CAABBCC,192.168.1.102"
            default_filename = "mac_specific_ip_template.csv"
        
        # Let user choose where to save the template
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV Template", default_filename, "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(template_content)
                self.log(f"CSV template saved to: {file_path}")
            except Exception as e:
                self.log(f"Error saving CSV template: {str(e)}")
                QMessageBox.warning(self, "Error", f"Could not save CSV template: {str(e)}")
    
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
    
    def closeEvent(self, event):
        """Handle application close event"""
        if self.is_dhcp_running:
            # Stop DHCP server if running
            self.stop_dhcp_server()
            
        event.accept()
