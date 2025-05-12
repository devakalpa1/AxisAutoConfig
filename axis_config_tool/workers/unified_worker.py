#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
Worker threads for background operations
"""

from PySide6.QtCore import QThread, Signal
from axis_config_tool.core import network_utils


class DHCPWorker(QThread):
    """Worker thread for running the DHCP server"""
    
    status_update = Signal(str)
    log_message = Signal(str)
    
    def __init__(self, dhcp_manager):
        super().__init__()
        self.dhcp_manager = dhcp_manager
        self._should_stop = False
        
    def run(self):
        """Run the DHCP server in a separate thread"""
        self.log_message.emit("Starting DHCP server thread...")
        try:
            self.status_update.emit("Running")
            self.dhcp_manager.start(stop_event=self._should_stop)
        except Exception as e:
            self.log_message.emit(f"DHCP server error: {str(e)}")
            self.status_update.emit("Error")
        finally:
            self.status_update.emit("Stopped")
            self.log_message.emit("DHCP server thread finished")
    
    def stop(self):
        """Signal the DHCP server to stop"""
        self.log_message.emit("Stopping DHCP server...")
        self._should_stop = True
        self.dhcp_manager.stop()
        self.wait()  # Wait for the thread to finish


class DiscoveryWorker(QThread):
    """Worker thread for camera discovery"""
    
    camera_found = Signal(str, str)  # IP, MAC
    log_message = Signal(str)
    
    def __init__(self, camera_discovery, leases):
        super().__init__()
        self.camera_discovery = camera_discovery
        self.leases = leases
        
    def run(self):
        """Run the camera discovery process in a separate thread"""
        self.log_message.emit(f"Starting camera discovery for {len(self.leases)} potential devices...")
        
        try:
            for ip, mac in self.leases:
                try:
                    if self.camera_discovery.check_device(ip):
                        self.camera_found.emit(ip, mac)
                except Exception as e:
                    self.log_message.emit(f"Error checking device at {ip}: {str(e)}")
        except Exception as e:
            self.log_message.emit(f"Discovery process error: {str(e)}")
        finally:
            self.log_message.emit("Discovery process completed")


class ConfigurationWorker(QThread):
    """Worker thread for camera configuration"""
    
    progress_update = Signal(int, int)  # current, total
    camera_configured = Signal(str, bool, dict)  # IP, success, details
    log_message = Signal(str)
    configuration_complete = Signal(list)  # List of results for all cameras
    
    def __init__(self, camera_operations, cameras, config_params):
        """
        Initialize the configuration worker
        
        Args:
            camera_operations: Instance of CameraOperations class
            cameras: List of discovered cameras [{'ip': temp_ip, 'mac': mac_address}, ...]
            config_params: Dictionary with configuration parameters
                {
                    'admin_user': str, 'admin_pass': str,
                    'onvif_user': str, 'onvif_pass': str,
                    'subnet_mask': str, 'gateway': str,
                    'protocol': str,
                    'ip_mode': 'sequential' or 'mac_specific',
                    'ip_list': [str] or {'mac': 'ip'} depending on mode
                }
        """
        super().__init__()
        self.camera_operations = camera_operations
        self.cameras = cameras
        self.config_params = config_params
        self._should_stop = False
        self.results = []  # Will store configuration results for reporting
        
    def run(self):
        """Run the camera configuration process in a separate thread"""
        self.log_message.emit("Camera configuration process started")
        self.log_message.emit(f"Found {len(self.cameras)} camera(s) to configure")
        
        # Extract configuration parameters
        admin_user = self.config_params.get('admin_user', '')
        admin_pass = self.config_params.get('admin_pass', '')
        onvif_user = self.config_params.get('onvif_user', '')
        onvif_pass = self.config_params.get('onvif_pass', '')
        subnet_mask = self.config_params.get('subnet_mask', '255.255.255.0')
        gateway = self.config_params.get('gateway', '')
        protocol = self.config_params.get('protocol', 'HTTP')
        ip_mode = self.config_params.get('ip_mode', 'sequential')
        ip_list = self.config_params.get('ip_list', [])
        
        # For OS version 10, we will always use 'root' as the admin username
        # regardless of what was provided by the user
        actual_admin_user = 'root'
        if admin_user != 'root':
            self.log_message.emit(f"Note: Provided admin username '{admin_user}' will be overridden with 'root' as required by Axis OS v10")
        
        # Validation
        if not admin_pass:
            self.log_message.emit("Error: Admin password is required")
            return
        
        if not self.cameras:
            self.log_message.emit("Error: No cameras to configure")
            return
            
        # IP assignment validation/preparation
        if ip_mode == 'sequential' and (not ip_list or not isinstance(ip_list, list)):
            self.log_message.emit("Error: Sequential IP mode requires a list of IP addresses")
            return
            
        if ip_mode == 'mac_specific' and (not ip_list or not isinstance(ip_list, dict)):
            self.log_message.emit("Error: MAC-specific IP mode requires a mapping of MAC addresses to IP addresses")
            return
        
        # Initialize the sequential IP counter if needed
        sequential_ip_index = 0
            
        # Process each discovered camera
        total_cameras = len(self.cameras)
        for i, camera in enumerate(self.cameras):
            if self._should_stop:
                self.log_message.emit("Camera configuration process stopped by user")
                break
                
            temp_ip = camera['ip']
            mac = camera['mac']
            
            self.progress_update.emit(i + 1, total_cameras)
            self.log_message.emit(f"Processing camera {i + 1} of {total_cameras} at temporary IP {temp_ip}")
            
            # Dictionary to track operations and results for this camera
            camera_result = {
                'temp_ip': temp_ip,
                'mac': mac,
                'operations': {},
                'final_ip': None,
                'status': 'Processing'
            }
            
            # Step 1: Create initial root admin user
            self.log_message.emit(f"Creating root administrator on {temp_ip}...")
            root_success, root_message = self.camera_operations.create_initial_admin(
                temp_ip, 'root', admin_pass, protocol
            )
            
            camera_result['operations']['root_admin'] = {
                'success': root_success,
                'message': root_message
            }
            
            if not root_success:
                self.log_message.emit(f"Failed to create root admin on {temp_ip}: {root_message}")
                camera_result['status'] = 'Failed - Root Admin Creation'
                self.results.append(camera_result)
                self.camera_configured.emit(temp_ip, False, camera_result)
                continue
                
            self.log_message.emit(f"Root admin created or verified on {temp_ip}")
            
            # Step 2: Create secondary admin user with custom username
            # Only if a different username than 'root' was specified
            if admin_user and admin_user != 'root':
                self.log_message.emit(f"Creating secondary admin user '{admin_user}' on {temp_ip}...")
                secondary_success, secondary_message = self.camera_operations.create_secondary_admin(
                    temp_ip, admin_pass, admin_user, admin_pass, protocol
                )
                
                camera_result['operations']['secondary_admin'] = {
                    'success': secondary_success,
                    'message': secondary_message
                }
                
                if not secondary_success:
                    self.log_message.emit(f"Failed to create secondary admin user '{admin_user}' on {temp_ip}: {secondary_message}")
                    # Continue anyway - not critical as we have root
                else:
                    self.log_message.emit(f"Secondary admin user '{admin_user}' created on {temp_ip}")
            
            # Step 3: Create ONVIF user if needed - always authenticate as root
            if onvif_user and onvif_pass:
                self.log_message.emit(f"Creating ONVIF user '{onvif_user}' on {temp_ip}...")
                onvif_success, onvif_message = self.camera_operations.create_onvif_user(
                    temp_ip, 'root', admin_pass, onvif_user, onvif_pass, protocol
                )
                
                camera_result['operations']['onvif_user'] = {
                    'success': onvif_success,
                    'message': onvif_message
                }
                
                if not onvif_success:
                    self.log_message.emit(f"Failed to create ONVIF user on {temp_ip}: {onvif_message}")
                    # Continue anyway - not critical
                else:
                    self.log_message.emit(f"ONVIF user created or verified on {temp_ip}")
            
            # Step 4: Set WDR off - always authenticate as root
            self.log_message.emit(f"Setting WDR off on {temp_ip}...")
            wdr_success, wdr_message = self.camera_operations.set_wdr_off(
                temp_ip, 'root', admin_pass, protocol
            )
            
            camera_result['operations']['wdr_off'] = {
                'success': wdr_success,
                'message': wdr_message
            }
            
            if not wdr_success:
                self.log_message.emit(f"Failed to turn off WDR on {temp_ip}: {wdr_message}")
                # Continue anyway - not critical
            else:
                self.log_message.emit(f"WDR turned off on {temp_ip}")
            
            # Step 5: Set Replay Protection off - always authenticate as root
            self.log_message.emit(f"Setting Replay Protection off on {temp_ip}...")
            replay_success, replay_message = self.camera_operations.set_replay_protection_off(
                temp_ip, 'root', admin_pass, protocol
            )
            
            camera_result['operations']['replay_protection_off'] = {
                'success': replay_success,
                'message': replay_message
            }
            
            if not replay_success:
                self.log_message.emit(f"Failed to turn off Replay Protection on {temp_ip}: {replay_message}")
                # Continue anyway - not critical
            else:
                self.log_message.emit(f"Replay Protection turned off on {temp_ip}")
            
            # Step 6: Determine final static IP based on mode
            try:
                final_ip = None
                
                if ip_mode == 'sequential':
                    # Check if we still have IPs available in the list
                    if sequential_ip_index < len(ip_list):
                        final_ip = ip_list[sequential_ip_index]
                        sequential_ip_index += 1
                    else:
                        self.log_message.emit(f"Error: No more IP addresses available in sequential list for {temp_ip}")
                        camera_result['status'] = 'Failed - No Available IP'
                        self.results.append(camera_result)
                        self.camera_configured.emit(temp_ip, False, camera_result)
                        continue
                        
                elif ip_mode == 'mac_specific':
                    # Try to find the MAC address in the mapping
                    # First try exact match, then normalize and try again
                    if mac in ip_list:
                        final_ip = ip_list[mac]
                    else:
                        # Try normalized MAC (remove colons, uppercase)
                        normalized_mac = mac.replace(':', '').upper()
                        for map_mac, map_ip in ip_list.items():
                            if map_mac.replace(':', '').upper() == normalized_mac:
                                final_ip = map_ip
                                break
                                
                    if not final_ip:
                        self.log_message.emit(f"Error: No IP mapping found for MAC {mac}")
                        camera_result['status'] = 'Failed - No MAC Match'
                        self.results.append(camera_result)
                        self.camera_configured.emit(temp_ip, False, camera_result)
                        continue
                
                # Validate the final IP
                if not network_utils.validate_ip_address(final_ip):
                    self.log_message.emit(f"Error: Invalid IP address format: {final_ip}")
                    camera_result['status'] = 'Failed - Invalid IP'
                    self.results.append(camera_result)
                    self.camera_configured.emit(temp_ip, False, camera_result)
                    continue
                    
                self.log_message.emit(f"Final static IP for {temp_ip} determined as {final_ip}")
                
            except Exception as e:
                self.log_message.emit(f"Error determining final IP for {temp_ip}: {str(e)}")
                camera_result['status'] = 'Failed - IP Assignment Error'
                self.results.append(camera_result)
                self.camera_configured.emit(temp_ip, False, camera_result)
                continue
            
            # Step 7: Set final static IP - always authenticate as root
            ip_config = {
                'ip': final_ip,
                'subnet': subnet_mask,
                'gateway': gateway
            }
            
            self.log_message.emit(f"Setting static IP {final_ip} on {temp_ip}...")
            ip_success, ip_message = self.camera_operations.set_final_static_ip(
                temp_ip, 'root', admin_pass, ip_config, protocol
            )
            
            camera_result['operations']['set_static_ip'] = {
                'success': ip_success,
                'message': ip_message
            }
            
            if not ip_success:
                self.log_message.emit(f"Failed to set static IP on {temp_ip}: {ip_message}")
                camera_result['status'] = 'Failed - IP Configuration'
                self.results.append(camera_result)
                self.camera_configured.emit(temp_ip, False, camera_result)
                continue
                
            self.log_message.emit(f"Static IP set to {final_ip} on camera (previously {temp_ip})")
            camera_result['final_ip'] = final_ip
            
            # Step 8: Wait for camera to come back online with new IP
            wait_time = 60  # seconds
            self.log_message.emit(f"Waiting for camera to come online at {final_ip} (up to {wait_time} seconds)...")
            
            if network_utils.wait_for_camera_online(final_ip, 'root', admin_pass, protocol, wait_time):
                self.log_message.emit(f"Camera successfully came online at {final_ip}")
                
                # Step 9: Get final MAC/serial for verification - always authenticate as root
                self.log_message.emit(f"Retrieving MAC and serial number from {final_ip}...")
                info_success, info_data = self.camera_operations.get_camera_mac_serial(
                    final_ip, 'root', admin_pass, protocol
                )
                
                if info_success:
                    camera_result['serial'] = info_data.get('serial', '')
                    verified_mac = info_data.get('mac', '')
                    if verified_mac:
                        camera_result['verified_mac'] = verified_mac
                        
                    self.log_message.emit(f"Retrieved information from {final_ip}: MAC={verified_mac}, Serial={camera_result.get('serial', 'N/A')}")
                else:
                    self.log_message.emit(f"Could not retrieve MAC/serial from {final_ip}")
                
                # Mark as successfully configured
                camera_result['status'] = 'Success'
                self.results.append(camera_result)
                self.camera_configured.emit(final_ip, True, camera_result)
                self.log_message.emit(f"Camera {i + 1} successfully configured with IP {final_ip}")
            else:
                self.log_message.emit(f"Camera did not come online at {final_ip} after configuration")
                camera_result['status'] = 'Failed - Camera Offline After IP Change'
                self.results.append(camera_result)
                self.camera_configured.emit(temp_ip, False, camera_result)
            
        # End of camera processing loop
        
        self.log_message.emit(f"Camera configuration process completed for {len(self.cameras)} cameras")
        
        # Calculate success/failure statistics
        success_count = len([r for r in self.results if r.get('status') == 'Success'])
        self.log_message.emit(f"Results: {success_count} of {len(self.cameras)} cameras successfully configured")
        
        # Emit signal with all results for reporting
        self.configuration_complete.emit(self.results)
    
    def stop(self):
        """Signal the configuration process to stop"""
        self._should_stop = True
        self.log_message.emit("Requesting configuration process to stop...")
