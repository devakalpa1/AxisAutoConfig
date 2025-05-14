# AxisAutoConfig

AxisAutoConfig is a solution I developed for initializing and pre-configuring factory-new Axis IP cameras. This application significantly reduces deployment time by automating what is otherwise a tedious multi-step manual configuration process.

## Project Origin: Solving a Real-World Challenge

When I recently started as a security technician, one of my responsibilities involved pre-configuring Axis network cameras before they were sent out for final deployment. I quickly noticed that setting up each camera manually with identical settings was a significant time investment, especially when dealing with multiple units. My studies for the CCNA had introduced me to the power of network automation, and I was convinced there had to be a more efficient way to tackle this repetitive task.

The first major hurdle was clear: factory-new Axis cameras typically ship with the same default IP address (often 192.168.0.90). Connecting several of these to a switch simultaneously resulted in immediate IP conflicts, making individual access for configuration impossible.

Driven to find a solution, I began exploring Axis's VAPIX API documentation, which confirmed that many configuration tasks could indeed be scripted. The challenge of initial, unique network access for batch processing remained. While external DHCP servers can assign unique IP addresses, my goal for AxisAutoConfig was to create a fully self-contained, automated tool that managed the entire pre-configuration lifecycle from a single interface. This led me to develop the custom, lightweight DHCP server integrated directly into this application. This purpose-built component allows AxisAutoConfig to directly manage the assignment of unique temporary IP addresses, which is the cornerstone of the automation process.

What was once a 15-30 minute manual process per camera has now been transformed by AxisAutoConfig into a batch operation that takes just a few moments per device, significantly improving workflow efficiency at my workplace.

## Technical Approach

The solution implemented in AxisAutoConfig is based on the following key components:

### 1. Custom Integrated DHCP Server

To achieve a fully self-contained automation tool, I developed a custom lightweight DHCP implementation within AxisAutoConfig. This allows the application to:

- Directly control the assignment of unique temporary IP addresses to factory-new cameras on an isolated pre-configuration network.
- Track camera MAC addresses associated with these temporary IPs, which is essential for targeting individual cameras.
- Utilize a configurable IP pool tailored for this specific setup scenario.
- Provide internal lease information for process control and troubleshooting.

This integrated DHCP approach was chosen over reliance on external DHCP servers to ensure the tool is portable and manages the entire initial network bootstrapping process itself.

### 2. Specific User Authentication Workflow

For operational requirements at my company, AxisAutoConfig implements a specific multi-step user setup process on each camera, performed via its temporary DHCP-assigned IP:

- Set Initial root Password: For factory-new AXIS OS 10.12 cameras (the primary target for this tool), the application first sets a password for the root user. This is done via an unauthenticated /axis-cgi/pwdgrp.cgi call, using the root password specified by the user in the GUI.
- Login as root: The application then authenticates to the camera as root using this newly set password.
- Create New Administrator User: While logged in as root, a new, separate administrator account (with username and password specified by the user in the GUI) is created and added to the administrator group via an authenticated /axis-cgi/pwdgrp.cgi call.
- Use New Administrator for Subsequent Operations: All further configurations (ONVIF user, WDR, Replay Protection, final static IP) are performed by authenticating as this newly created administrator account.
- ONVIF User Creation: A dedicated ONVIF user (credentials specified in the GUI) is created with appropriate privileges for VMS integration, authenticating as the new administrator.

This specific sequence meets our internal pre-configuration standards.

### 3. Network Configuration Via VAPIX API (network_settings.cgi)

Setting the final static IP address reliably was a key research point. Based on my review of Axis API documentation and with valuable confirmation from Cacsjep in the Axis developer community regarding the specific endpoint, AxisAutoConfig exclusively uses the /axis-cgi/network_settings.cgi JSON API endpoint (via HTTP POST) to configure the final static IP address, subnet mask, and default gateway. This tool does not use param.cgi for setting these primary network interface parameters, as network_settings.cgi is the recommended method for modern Axis cameras.

## Key Features

- **Integrated Custom DHCP Server**: For assigning temporary IP addresses to new cameras.
- **Camera Discovery**: Identifies cameras that have received leases from the integrated DHCP server.
- **Automated User Setup**: Implements the specific root password setting, new administrator creation, and ONVIF user creation workflow.
- **Baseline Settings Automation**:
  - WDR (Wide Dynamic Range) disabling.
  - Replay Attack Protection disabling.
- **Static IP Assignment**: Configures final static IP, subnet, and gateway using the robust /axis-cgi/network_settings.cgi VAPIX endpoint.
- **Flexible IP Assignment CSV Input**:
  - Sequential mode: Assigns IPs from a single-column CSV (IP) in the order cameras are processed.
  - MAC-specific mode: Assigns specific IPs to cameras based on a two-column CSV (IP, MAC), matching camera serial numbers (MACs without delimiters).
- **GUI-Driven Process**: User-friendly interface built with PySide6, featuring system theme adaptation, responsive layout, real-time logging, and instructional elements.
- **Comprehensive Reporting**: Generates a CSV report detailing the temporary IP, final assigned static IP, MAC address (serial format), and status of pre-configuration for each camera.

## Installation

### Prerequisites

- Python 3.7 or higher (Python 3.8+ recommended for PySide6).
- A Windows operating system (developed and primarily aimed at Windows 10/11).
- Administrative privileges for the application (required for the custom DHCP server to bind to network ports and for potential PyInstaller-related actions).

### From Source

1. Clone the repository:
```
git clone https://github.com/devakalpa1/AxisAutoConfig.git
cd AxisAutoConfig
```

2. Create and activate a virtual environment (highly recommended):
```
python -m venv venv
venv\Scripts\activate
```

3. Install the required packages:
```
pip install -r requirements.txt
```

4. Run the application:
```
python main.py
```

### Creating an Executable with PyInstaller

To create a standalone executable:

1. Ensure PyInstaller is installed in your environment:
```
pip install pyinstaller
```

2. Navigate to the project's root directory in your terminal.

3. Use a .spec file for reliable builds with PySide6. A basic command to generate one (which you'll then likely need to edit) is:
```
pyinstaller --name AxisAutoConfig --windowed main.py
```
You will then need to edit AxisAutoConfig.spec to correctly include PySide6 hidden imports, data files (like app_icon.ico and README.md if accessed by the app), and Qt plugins if necessary.
A more complete command incorporating common needs might look like:
```
pyinstaller --name AxisAutoConfig --windowed --icon=axis_config_tool/resources/app_icon.ico --add-data "axis_config_tool/resources/app_icon.ico;axis_config_tool/resources/" --add-data "README.md;." main.py
```

(Note: PyInstaller with PySide6 can sometimes be complex. The PySide6 module itself might need to be added to hiddenimports in the .spec file, along with submodules like PySide6.QtCore, PySide6.QtGui, PySide6.QtWidgets, and PySide6.QtNetwork if used by the DHCP server. Extensive testing of the bundled executable is crucial.)

4. Build the executable using the spec file:
```
pyinstaller AxisAutoConfig.spec
```

5. The executable will typically be in the dist/AxisAutoConfig directory (for --onedir builds, which is recommended for GUI apps with assets).

## Usage Guide

### Network Setup Best Practices

- **Isolate Network**: Connect your computer and the factory-new Axis cameras to a dedicated network switch, isolated from your main production network.
- **Host PC Static IP**: Manually configure a static IP address on the network interface of your computer that will be used for this process (e.g., 192.168.0.1, Subnet Mask 255.255.255.0). This IP must be outside the DHCP range you will configure in the AxisAutoConfig tool.
- **Administrator Privileges**: Run the AxisAutoConfig application with administrator privileges.

### Step-by-Step Configuration Process

#### 1. DHCP Server Configuration

- Launch AxisAutoConfig.
- Click the "Configure & Start DHCP Server" button (or similar, based on final GUI design).
- In the DHCP Setup dialog:
  - Select the network interface on your PC that is connected to the camera switch.
  - Verify or input your PC's static IP for that interface (this will be the DHCP server's IP).
  - Adjust the DHCP IP range and lease time if needed (defaults are provided).
- Click "Start DHCP Server." Monitor the status.

#### 2. Camera Discovery

- Once the DHCP server is running, power on your Axis cameras. It's often best to power them on sequentially with a few seconds in between, especially for the very first discovery.
- In the main window of AxisAutoConfig, click "Discover Cameras on DHCP Network."
- Wait for cameras to appear in the discovered list (showing their temporary DHCP IP and MAC address). Verify the count.

#### 3. Configuration Inputs

- In the designated section of the main window:
  - Enter the desired password for the root user on the cameras.
  - Enter the New Administrator Username and New Administrator Password (this will be a separate admin account created after root is set up).
  - Enter the ONVIF Username and ONVIF Password.
  - Specify the Final Static Subnet Mask and Final Static Default Gateway for the cameras.
  - Select the VAPIX Protocol (HTTP/HTTPS) for configuration actions.
  - Choose the Final IP Assignment Mode:
    - "Assign Sequentially from IP List"
    - "Assign Specific IP to MAC Address"
  - Click "Load Final Static IP List (CSV)..." and select your prepared CSV file. The GUI should provide clear instructions on the expected CSV format based on the selected mode. Use the "Download CSV Template" button if available for guidance.

#### 4. Start Camera Pre-Configuration Process

- Click the "Start Camera Pre-Configuration Process" button.
- A confirmation dialog might appear summarizing the actions.
- Monitor the real-time log for progress, individual camera status, and any errors.
- The application will execute the multi-step process on each camera:
  - Setting the root password.
  - Logging in as root, then creating the new specified administrator account.
  - Logging in as the new administrator, then creating the ONVIF user.
  - Disabling WDR and Replay Attack Protection.
  - Setting the final static IP address, subnet, and gateway.
  - Verifying connectivity to each camera at its new static IP and retrieving its definitive MAC/Serial.

#### 5. Review and Export Results

- Once the process completes, review the summary.
- Click "Save Pre-Configuration Report..." (or similar) to save the detailed inventory CSV. This report will include the final static IP, MAC address (serial format), and status for each camera.

### CSV Format for Final IP Assignment

The application uses a single CSV file upload. It intelligently determines the assignment strategy based on the CSV content and your selected mode.

#### Sequential Assignment Mode

- Expected CSV Header: `IP`
- Content: A single column listing the final static IP addresses in the order you want them assigned to cameras as they are processed.

```
IP
10.28.128.10
10.28.128.11
10.28.128.12
```

#### MAC-Specific Assignment Mode

- Expected CSV Headers: `IP,MAC`
- Content: Two columns. Column 1 is IP and column 2 is MAC. The MAC must be the camera's serial number (MAC without colons or dashes, e.g., 00408CAABBCC).

```
IP,MAC
10.28.128.10,00408C123456
10.28.128.11,00408CAABBCC
```

The tool will perform validation on the CSV structure and content.

### Notes for Axis OS Version Compatibility

This application has been specifically developed and tested with:

- Camera Model: AXIS P-3267-LV
- Axis OS Version: 10.12

For AXIS OS 10.12, the initial administrator setup involves setting the password for the root user. The behavior for other OS versions, particularly regarding the initial administrator username (whether "root" is mandatory or if a custom name can be used for the very first unauthenticated setup), may vary. This tool attempts to set the password for the root user as the first step.

- **Firmware Updates**: Firmware updates are not automated by this tool and must be performed separately if required.
- **Untested Versions**: Compatibility with AXIS OS 11+ or 12+ (which may default to link-local addressing if DHCP fails) has not been specifically tested with this tool.

## Troubleshooting Guide

(This section should be populated based on actual issues encountered during development and testing. For now, it can include general advice.)

- **"No network interfaces found"**: Ensure your network adapter is enabled and has a manually configured static IP address on the 192.168.0.x pre-configuration network.
- **"Failed to start DHCP server"**: Run AxisAutoConfig with administrator privileges. Ensure no other DHCP server is active on the selected network interface. Check firewall settings.
- **"No cameras discovered"**: Verify cameras are powered on, connected to the correct isolated switch, and are factory-new (or reset). Ensure your PC's static IP and the DHCP server settings are correct for that network segment.
- **"CSV validation error"**: Double-check your CSV file against the format requirements for the selected IP assignment mode. Use the "Download CSV Template" button in the GUI for a correctly formatted example. Ensure no duplicate IPs (in any mode) or duplicate MACs (in MAC-specific mode).
- **"Authentication failures" / VAPIX errors during configuration**:
  - Ensure the "Set root Password" entered in the GUI is correct and was successfully applied.
  - Verify the "New Administrator Username/Password" are correctly entered.
  - If cameras are not factory-new, they may have existing credentials preventing the initial root password set. A hardware factory reset of the camera may be required.

## Contact & Support

This tool was developed by Geoffrey Stephens to solve a specific workflow challenge.
For bug reports, feature requests, or other questions:

- Email: gstephens@storypolish.com
- GitHub Issues: https://github.com/devakalpa1/AxisAutoConfig/issues

## License

This project is licensed under the MIT License. 

## Acknowledgements

- Axis Communications for their VAPIX and ONVIF documentation.
- Thanks to Cacsjep from the Axis developer community for assistance in confirming the /axis-cgi/network_settings.cgi endpoint for static IP configuration.
