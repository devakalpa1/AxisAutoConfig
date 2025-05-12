# AxisAutoConfig

**AxisAutoConfig** is a comprehensive solution for initializing and pre-configuring factory-new Axis IP cameras. This Phase 3 release features a fully implemented three-user workflow, enhanced CSV handling, and improved UI/UX experience.

## Overview

This Python desktop application provides an all-in-one solution for system integrators and network administrators working with Axis cameras. It helps automate the initial setup process, including:

- Managing a custom DHCP server for temporary IP assignment to factory-new cameras
- Discovering cameras on the network
- Setting initial admin and ONVIF user credentials
- Applying baseline settings (WDR off, Replay Protection off)
- Assigning final static IP addresses based on user-provided CSV
- Generating inventory reports of configured cameras

## User Creation Workflow

The application implements a three-user creation workflow for secure camera setup:

1. **Root Administrator (Step 1)**
   - For Axis OS version 10 and below, the initial admin must be "root"
   - This user is created without authentication (factory-new state)
   - This is a requirement of the Axis OS and cannot be changed

2. **Secondary Administrator (Step 2, Optional)**
   - After the root admin is created, you can create a secondary admin user
   - This user will have a custom username of your choice
   - This user shares the same password as the root admin
   - Useful for organizational management and tracking

3. **ONVIF User (Step 3)**
   - Dedicated user created specifically for ONVIF client connections
   - Has appropriate ONVIF permissions for third-party VMS integration
   - Can have different credentials than the admin users

All subsequent camera operations (turning off WDR, disabling Replay Protection, setting static IP) are performed using the root admin credentials for maximum compatibility.

## Features

- **Custom DHCP Server**: Temporarily assign IPs to factory-new cameras
- **Camera Discovery**: Automatically detect Axis cameras on the network
- **Batch Configuration**: Apply settings to multiple cameras simultaneously
- **IP Assignment Modes**:
  - Sequential assignment from a list
  - MAC address specific assignment
- **Configuration Options**:
  - Three-user setup workflow (root admin, secondary admin, ONVIF user)
  - Disable WDR (Wide Dynamic Range)
  - Disable Replay Protection
  - Set final static IP addresses
- **Inventory Reporting**: Generate CSV reports with configuration status
- **Enhanced UI**: Interactive help, CSV templates, and intuitive user workflow

## Installation

### Prerequisites

- Python 3.6 or higher
- Network interface with administrator privileges
- Windows operating system (tested on Windows 10/11)

### From Source

1. Clone the repository:
   ```
   git clone https://github.com/devakalpa1/AxisAutoConfig.git
   cd AxisAutoConfig
   ```

2. Create and activate a virtual environment (recommended):
   ```
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python main.py
   ```

### Using pip

```bash
pip install axis-config-tool
```

After installation, run the tool with:

```bash
axis-config-tool
```

### Using PyInstaller

To create a standalone executable:

1. Install PyInstaller:
   ```
   pip install pyinstaller
   ```

2. Create the executable:
   ```
   pyinstaller --name AxisConfigTool --windowed --icon=app_icon.ico --add-data "axis_config_tool/resources/*;axis_config_tool/resources/" main.py
   ```

3. The executable will be in the `dist/AxisConfigTool` directory.

## Usage

### Network Setup

1. Connect your computer to the same network switch as your factory-new cameras
2. Set a static IP address on your computer
3. Start the application

### DHCP Server Configuration

1. Select the network interface connected to the cameras
2. Enter your PC's static IP as the DHCP server IP
3. Use default DHCP settings or customize as needed
4. Click "Start DHCP Server"

### Camera Discovery

1. Power on your Axis cameras one at a time
2. Click "Discover Cameras on DHCP Network"
3. Wait for cameras to appear in the discovery list

### Camera Configuration

1. Enter the administrator password you want to set
2. Enter ONVIF username and password (optional)
3. Specify subnet mask and default gateway
4. Select IP assignment mode (Sequential or MAC-specific)
5. Load your CSV file with static IP assignments
6. Click "Start Camera Pre-Configuration Process"

### Review Results

1. Monitor the real-time log for progress updates
2. After completion, save the inventory report (CSV)

## CSV Format

### Sequential Assignment

For sequential IP assignment, use a CSV with a single column:

```csv
FinalIPAddress
192.168.1.101
192.168.1.102
192.168.1.103
```

### MAC-Specific Assignment

For MAC address specific assignment, use a CSV with two columns:

```csv
FinalIPAddress,MACAddress
192.168.1.101,00408C123456
192.168.1.102,00408CAABBCC
```

Note: MAC addresses should be in a single string format with no delimiters (no colons or dashes).

## Project Structure

```
axis_config_tool/
├── core/                # Core functionality
│   ├── camera_discovery.py
│   ├── camera_operations.py
│   ├── csv_handler.py
│   ├── dhcp_manager.py
│   └── network_utils.py
├── gui/                 # GUI components
│   ├── about_dialog.py
│   ├── gui_tour.py
│   └── main_window.py
├── workers/             # Worker threads
│   └── unified_worker.py
├── resources/           # Application resources
└── run.py               # Package entry point
```

## Troubleshooting

### Common Issues

1. **"No network interfaces found"** - Ensure your network adapter is enabled and has a valid IP configuration.

2. **"Failed to start DHCP server"** - The application requires administrator privileges to run the DHCP server. Try running the application as administrator.

3. **"No cameras discovered"** - Ensure your cameras are powered on and connected to the same network switch. Factory-reset the cameras if they were previously configured.

4. **"CSV parsing error"** - Check your CSV file format against the examples provided above.

## Notes for Axis OS Version 10 and Above

Starting with Axis OS version 10, the administrator username must be `root` regardless of what username is specified. The tool automatically enforces this requirement.

## Logging

The application logs are stored in `axis_config.log` in the application directory.

## License

This project is licensed under the MIT License:

```
MIT License

Copyright (c) 2025 Geoffrey Stephens

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Credits

Developed by Geoffrey Stephens

Contact: gstephens@storypolish.com

## Acknowledgements

- PySide6 for the GUI framework
- Axis Communications for their VAPIX and ONVIF documentation
