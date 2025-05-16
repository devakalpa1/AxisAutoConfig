#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
Camera operations module for VAPIX and ONVIF interactions
"""

import logging
import re
import time
import socket
import ipaddress
import json
import requests
from requests.auth import HTTPDigestAuth
from typing import Dict, Any, Tuple, Optional, Union, List
from zeep import Client, Transport
from zeep.wsse.username import UsernameToken
from urllib.parse import urljoin
import xml.etree.ElementTree as ET


class CameraOperations:
    """VAPIX and ONVIF operations for Axis cameras"""
    
    def __init__(self):
        """Initialize Camera Operations module"""
        self.timeout = 10  # Default timeout for requests (seconds)
        self.retry_count = 3  # Number of retries for failed requests
        self.retry_delay = 2  # Seconds to wait between retries
    
    def create_initial_admin(self, temp_ip: str, new_admin_user: str, 
                             new_admin_pass: str, protocol: str = "HTTP") -> Tuple[bool, str]:
        """
        Create initial administrator user on a factory-new camera
        
        For AXIS OS version 10, username must be 'root' and role must be Administrator
        with PTZ control. This user can only be created once.
        
        Args:
            temp_ip: Camera's temporary DHCP IP address
            new_admin_user: Provided administrator username (ignored, will use 'root')
            new_admin_pass: New administrator password to set
            protocol: 'HTTP' or 'HTTPS'
            
        Returns:
            Tuple of (success, message)
        """
        # Force username to be 'root' for OS version 10
        admin_user = 'root'
        
        logging.info(f"Creating initial admin user 'root' on camera at {temp_ip}")
        if new_admin_user != 'root':
            logging.warning(f"Provided admin username '{new_admin_user}' overridden with 'root' as required by Axis OS v10")
        
        # Construct the base URL
        base_url = f"{protocol.lower()}://{temp_ip}"
        
        # Endpoint for creating users
        endpoint = "/axis-cgi/pwdgrp.cgi"
        
        # Parameters for the request - ensure we use required groups for OS v10
        params = {
            "action": "add",
            "user": "root",  # Force root username
            "pwd": new_admin_pass,
            "grp": "root",
            "sgrp": "admin:operator:viewer:ptz"  # Required security groups for OS v10
        }
        
        # Make the request without authentication (factory-new state)
        url = urljoin(base_url, endpoint)
        
        for attempt in range(self.retry_count):
            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    verify=False  # Skip SSL verification for self-signed certs
                )
                
                # Check if request was successful
                if response.status_code == 200:
                    logging.info(f"Successfully created admin user 'root' on {temp_ip}")
                    return True, f"Initial admin user 'root' created successfully"
                
                # Check for specific error cases
                if response.status_code == 401 or response.status_code == 403:
                    # Camera might already have admin accounts set up
                    logging.warning(f"Authentication required for {temp_ip} - camera may not be in factory-new state")
                    
                    # Try to check if user exists by attempting to authenticate with these credentials
                    # This is a common case - the admin was already set up but we're using the same credentials
                    try:
                        auth_check_url = urljoin(base_url, "/axis-cgi/usergroup.cgi")
                        auth_response = requests.get(
                            auth_check_url,
                            auth=HTTPDigestAuth('root', new_admin_pass),
                            timeout=self.timeout,
                            verify=False
                        )
                        
                        if auth_response.status_code == 200:
                            logging.info(f"User 'root' already exists and credentials work on {temp_ip}")
                            return True, f"Admin user 'root' already exists with matching credentials"
                        else:
                            logging.error(f"Failed to create user on {temp_ip} - camera is not in factory-new state")
                            return False, "Camera is not in factory-new state and provided credentials invalid"
                    
                    except Exception as auth_error:
                        logging.error(f"Error checking existing credentials on {temp_ip}: {str(auth_error)}")
                        return False, f"Camera is not in factory-new state: {str(auth_error)}"
                
                # Other error cases
                error_message = f"Failed to create user (HTTP {response.status_code}): {response.text}"
                logging.error(error_message)
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds... (attempt {attempt + 1}/{self.retry_count})")
                    time.sleep(self.retry_delay)
                else:
                    return False, error_message
            
            except requests.exceptions.ConnectionError as e:
                if "Connection refused" in str(e):
                    logging.error(f"Connection refused to {temp_ip}. Camera may not be online.")
                else:
                    logging.error(f"Connection error to {temp_ip}: {str(e)}")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds... (attempt {attempt + 1}/{self.retry_count})")
                    time.sleep(self.retry_delay)
                else:
                    return False, f"Connection error: {str(e)}"
                
            except requests.exceptions.Timeout:
                logging.error(f"Request to {temp_ip} timed out")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds... (attempt {attempt + 1}/{self.retry_count})")
                    time.sleep(self.retry_delay)
                else:
                    return False, "Request timed out"
                
            except Exception as e:
                logging.error(f"Unexpected error creating user on {temp_ip}: {str(e)}")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds... (attempt {attempt + 1}/{self.retry_count})")
                    time.sleep(self.retry_delay)
                else:
                    return False, f"Unexpected error: {str(e)}"
        
        # If we get here, all retry attempts failed
        return False, f"Failed to create admin user after {self.retry_count} attempts"
    
    def create_secondary_admin(self, temp_ip: str, root_pass: str, 
                              secondary_admin_user: str, secondary_admin_pass: str,
                              protocol: str = "HTTP") -> Tuple[bool, str]:
        """
        Create secondary administrator user on a camera
        
        This method requires authentication as the root user that was previously set up.
        
        Args:
            temp_ip: Camera's temporary DHCP IP address
            root_pass: Password for the root user (for authentication)
            secondary_admin_user: Username for the secondary admin to create
            secondary_admin_pass: Password for the secondary admin
            protocol: 'HTTP' or 'HTTPS'
            
        Returns:
            Tuple of (success, message)
        """
        logging.info(f"Creating secondary admin user '{secondary_admin_user}' on camera at {temp_ip}")
        
        # Construct the base URL
        base_url = f"{protocol.lower()}://{temp_ip}"
        
        # Endpoint for creating users
        endpoint = "/axis-cgi/pwdgrp.cgi"
        
        # Parameters for the request
        params = {
            "action": "add",
            "user": secondary_admin_user,
            "pwd": secondary_admin_pass,
            "grp": "users",
            "sgrp": "admin:operator:viewer:ptz",  # Admin privileges with PTZ control
            "comment": "Secondary administrator created by Axis Camera Unified Setup Tool"
        }
        
        # Make the request with root authentication
        url = urljoin(base_url, endpoint)
        
        for attempt in range(self.retry_count):
            try:
                response = requests.get(
                    url,
                    params=params,
                    auth=HTTPDigestAuth('root', root_pass),  # Always authenticate as root
                    timeout=self.timeout,
                    verify=False  # Skip SSL verification for self-signed certs
                )
                
                # Check if request was successful
                if response.status_code == 200:
                    logging.info(f"Successfully created secondary admin user '{secondary_admin_user}' on {temp_ip}")
                    return True, f"Secondary admin user '{secondary_admin_user}' created successfully"
                
                # Handle specific error cases
                if "account already exist" in response.text.lower():
                    logging.warning(f"User '{secondary_admin_user}' already exists on {temp_ip}")
                    return True, f"Secondary admin user '{secondary_admin_user}' already exists"
                
                # Other error cases
                error_message = f"Failed to create secondary admin (HTTP {response.status_code}): {response.text}"
                logging.error(error_message)
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds... (attempt {attempt + 1}/{self.retry_count})")
                    time.sleep(self.retry_delay)
                else:
                    return False, error_message
            
            except requests.exceptions.ConnectionError as e:
                if "Connection refused" in str(e):
                    logging.error(f"Connection refused to {temp_ip}. Camera may not be online.")
                else:
                    logging.error(f"Connection error to {temp_ip}: {str(e)}")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds... (attempt {attempt + 1}/{self.retry_count})")
                    time.sleep(self.retry_delay)
                else:
                    return False, f"Connection error: {str(e)}"
                
            except requests.exceptions.Timeout:
                logging.error(f"Request to {temp_ip} timed out")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds... (attempt {attempt + 1}/{self.retry_count})")
                    time.sleep(self.retry_delay)
                else:
                    return False, "Request timed out"
                
            except Exception as e:
                logging.error(f"Unexpected error creating secondary admin on {temp_ip}: {str(e)}")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds... (attempt {attempt + 1}/{self.retry_count})")
                    time.sleep(self.retry_delay)
                else:
                    return False, f"Unexpected error: {str(e)}"
        
        # If we get here, all retry attempts failed
        return False, f"Failed to create secondary admin user after {self.retry_count} attempts"
    
    def create_onvif_user(self, temp_ip: str, admin_user: str, admin_pass: str,
                         onvif_user: str, onvif_pass: str, 
                         protocol: str = "HTTP") -> Tuple[bool, str]:
        """
        Create ONVIF user on camera
        
        This uses the ONVIF SOAP API via zeep to create a new ONVIF user
        
        Args:
            temp_ip: Camera's temporary DHCP IP address
            admin_user: Administrator username for authentication
            admin_pass: Administrator password for authentication
            onvif_user: ONVIF username to create
            onvif_pass: ONVIF password to set
            protocol: 'HTTP' or 'HTTPS'
            
        Returns:
            Tuple of (success, message)
        """
        logging.info(f"Creating ONVIF user '{onvif_user}' on camera at {temp_ip}")
        
        # First, try using VAPIX to create the ONVIF user
        # This is often easier than using the ONVIF API directly
        try:
            vapix_result = self._create_onvif_user_via_vapix(
                temp_ip, admin_user, admin_pass, onvif_user, onvif_pass, protocol
            )
            
            if vapix_result[0]:
                return vapix_result
            else:
                logging.info(f"VAPIX method failed, trying ONVIF SOAP API: {vapix_result[1]}")
        except Exception as e:
            logging.info(f"VAPIX method failed, trying ONVIF SOAP API: {str(e)}")
        
        # If VAPIX method failed, try using ONVIF SOAP API
        try:
            # Construct the ONVIF device service WSDL URL
            onvif_port = 80 if protocol.lower() == "http" else 443
            wsdl_url = f"{protocol.lower()}://{temp_ip}:{onvif_port}/onvif/device_service"
            
            # Custom transport with digest auth
            transport = Transport(timeout=self.timeout, operation_timeout=self.timeout)
            
            # Create zeep client with username token authentication
            client = Client(
                'http://www.onvif.org/ver10/device/wsdl/devicemgmt.wsdl',  # Local WSDL reference
                wsse=UsernameToken(admin_user, admin_pass),
                transport=transport
            )
            
            # Set the service address dynamically
            client.service._binding_options["address"] = wsdl_url
            
            # Create a user with administrator privileges
            for attempt in range(self.retry_count):
                try:
                    # Define the user with admin privileges using ONVIF schema
                    user_info = {
                        'Username': onvif_user,
                        'Password': onvif_pass,
                        'UserLevel': 'Administrator'  # ONVIF UserLevel enum: Administrator, Operator, User, Anonymous
                    }
                    
                    # Call the CreateUsers method
                    response = client.service.CreateUsers(user_info)
                    
                    logging.info(f"Successfully created ONVIF user '{onvif_user}' on {temp_ip} via ONVIF API")
                    return True, f"ONVIF user '{onvif_user}' created successfully"
                    
                except Exception as soap_error:
                    error_str = str(soap_error)
                    
                    # Check if user already exists
                    if "UsernameclashException" in error_str or "already exists" in error_str.lower():
                        logging.warning(f"ONVIF user '{onvif_user}' already exists on {temp_ip}")
                        
                        # Try to update the password (if necessary)
                        try:
                            update_user = {
                                'Username': onvif_user,
                                'Password': onvif_pass
                            }
                            client.service.SetUser(update_user)
                            return True, f"ONVIF user '{onvif_user}' already exists, updated password"
                        except Exception as update_error:
                            logging.warning(f"Could not update existing ONVIF user: {str(update_error)}")
                            return True, f"ONVIF user '{onvif_user}' already exists, but could not update password"
                    
                    logging.error(f"ONVIF API error on attempt {attempt + 1}: {error_str}")
                    
                    if attempt < self.retry_count - 1:
                        logging.info(f"Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        return False, f"Failed to create ONVIF user: {error_str}"
                    
        except Exception as e:
            logging.error(f"Unexpected error creating ONVIF user on {temp_ip}: {str(e)}")
            return False, f"Unexpected error creating ONVIF user: {str(e)}"
            
        # If we get here, all retry attempts failed
        return False, f"Failed to create ONVIF user after {self.retry_count} attempts"
    
    def _create_onvif_user_via_vapix(self, temp_ip: str, admin_user: str, admin_pass: str,
                                   onvif_user: str, onvif_pass: str, 
                                   protocol: str = "HTTP") -> Tuple[bool, str]:
        """
        Create ONVIF user using VAPIX API (simpler approach than SOAP)
        
        Args:
            temp_ip: Camera's temporary DHCP IP address
            admin_user: Administrator username for authentication
            admin_pass: Administrator password for authentication
            onvif_user: ONVIF username to create
            onvif_pass: ONVIF password to set
            protocol: 'HTTP' or 'HTTPS'
            
        Returns:
            Tuple of (success, message)
        """
        # Construct the base URL
        base_url = f"{protocol.lower()}://{temp_ip}"
        
        # Endpoint for creating users
        endpoint = "/axis-cgi/pwdgrp.cgi"
        
        # Parameters for the request - correct format for Axis OS 10.12
        # The key is to include both 'onvif' in sgrp (special group) and proper privilege groups
        params = {
            "action": "add",
            "user": onvif_user,
            "pwd": onvif_pass,
            "grp": "users",  # Basic user group for Axis OS 10.12
            "sgrp": "onvif:admin:operator:viewer",  # ONVIF with proper privileges for Axis OS 10.12
            "comment": "ONVIF user created by AxisAutoConfig"
        }
        
        url = urljoin(base_url, endpoint)
        
        for attempt in range(self.retry_count):
            try:
                response = requests.get(
                    url,
                    params=params,
                    auth=HTTPDigestAuth(admin_user, admin_pass),
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    logging.info(f"Successfully created ONVIF user '{onvif_user}' on {temp_ip} via VAPIX")
                    return True, f"ONVIF user '{onvif_user}' created successfully via VAPIX"
                
                # Handle specific error cases
                if "account already exist" in response.text.lower():
                    logging.warning(f"ONVIF user '{onvif_user}' already exists on {temp_ip}")
                    
                    # Try to update existing user with correct groups
                    update_params = {
                        "action": "update",
                        "user": onvif_user,
                        "pwd": onvif_pass,  # Update password
                        "grp": "users",  # Ensure basic user group
                        "sgrp": "onvif:admin:operator:viewer"  # Ensure correct ONVIF access for OS 10.12
                    }
                    
                    update_response = requests.get(
                        url,
                        params=update_params,
                        auth=HTTPDigestAuth(admin_user, admin_pass),
                        timeout=self.timeout,
                        verify=False
                    )
                    
                    if update_response.status_code == 200:
                        return True, f"ONVIF user '{onvif_user}' already exists, updated settings"
                    else:
                        return True, f"ONVIF user '{onvif_user}' already exists, but could not update"
                
                error_message = f"Failed to create ONVIF user via VAPIX (HTTP {response.status_code}): {response.text}"
                logging.error(error_message)
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    return False, error_message
                    
            except Exception as e:
                logging.error(f"Error creating ONVIF user via VAPIX on {temp_ip}: {str(e)}")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    return False, f"Error creating ONVIF user via VAPIX: {str(e)}"
        
        return False, f"Failed to create ONVIF user via VAPIX after {self.retry_count} attempts"

    def set_wdr_off(self, temp_ip: str, admin_user: str, admin_pass: str,
                    protocol: str = "HTTP") -> Tuple[bool, str]:
        """
        Turn off Wide Dynamic Range (WDR) on camera
        
        Args:
            temp_ip: Camera's temporary DHCP IP address
            admin_user: Administrator username for authentication
            admin_pass: Administrator password for authentication
            protocol: 'HTTP' or 'HTTPS'
            
        Returns:
            Tuple of (success, message)
        """
        logging.info(f"Setting WDR off on camera at {temp_ip}")
        
        # Construct the base URL
        base_url = f"{protocol.lower()}://{temp_ip}"
        
        # VAPIX parameter API endpoint
        endpoint = "/axis-cgi/param.cgi"
        
        # Parameter for disabling WDR
        params = {
            "action": "update",
            "ImageSource.I0.Sensor.WDR": "off"
        }
        
        url = urljoin(base_url, endpoint)
        
        for attempt in range(self.retry_count):
            try:
                response = requests.get(
                    url,
                    params=params,
                    auth=HTTPDigestAuth(admin_user, admin_pass),
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    logging.info(f"Successfully turned off WDR on {temp_ip}")
                    return True, "WDR turned off successfully"
                
                # Handle specific error cases
                error_message = f"Failed to turn off WDR (HTTP {response.status_code}): {response.text}"
                logging.error(error_message)
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    return False, error_message
                
            except Exception as e:
                logging.error(f"Error turning off WDR on {temp_ip}: {str(e)}")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    return False, f"Error turning off WDR: {str(e)}"
        
        return False, f"Failed to turn off WDR after {self.retry_count} attempts"
    
    def set_replay_protection_off(self, temp_ip: str, admin_user: str, admin_pass: str,
                               protocol: str = "HTTP") -> Tuple[bool, str]:
        """
        Turn off Replay Protection on camera
        
        Args:
            temp_ip: Camera's temporary DHCP IP address
            admin_user: Administrator username for authentication
            admin_pass: Administrator password for authentication
            protocol: 'HTTP' or 'HTTPS'
            
        Returns:
            Tuple of (success, message)
        """
        logging.info(f"Setting Replay Protection off on camera at {temp_ip}")
        
        # Construct the base URL
        base_url = f"{protocol.lower()}://{temp_ip}"
        
        # VAPIX parameter API endpoint
        endpoint = "/axis-cgi/param.cgi"
        
        # Parameter for disabling replay protection
        params = {
            "action": "update",
            "WebService.UsernameToken.ReplayAttackProtection": "no"
        }
        
        url = urljoin(base_url, endpoint)
        
        for attempt in range(self.retry_count):
            try:
                response = requests.get(
                    url,
                    params=params,
                    auth=HTTPDigestAuth(admin_user, admin_pass),
                    timeout=self.timeout,
                    verify=False
                )
                
                if response.status_code == 200:
                    logging.info(f"Successfully turned off Replay Protection on {temp_ip}")
                    return True, "Replay Protection turned off successfully"
                
                # Check for error indicating the parameter doesn't exist (some models don't have this)
                if "No such parameter" in response.text:
                    logging.warning(f"Replay Protection parameter not found on {temp_ip}, camera may not support it")
                    return True, "Replay Protection setting not applicable for this camera model"
                    
                error_message = f"Failed to turn off Replay Protection (HTTP {response.status_code}): {response.text}"
                logging.error(error_message)
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    return False, error_message
                
            except Exception as e:
                logging.error(f"Error turning off Replay Protection on {temp_ip}: {str(e)}")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    return False, f"Error turning off Replay Protection: {str(e)}"
        
        return False, f"Failed to turn off Replay Protection after {self.retry_count} attempts"

    def set_final_static_ip(self, temp_ip: str, admin_user: str, admin_pass: str,
                           ip_config: Dict[str, str], protocol: str = "HTTP") -> Tuple[bool, str]:
        """
        Set final static IP configuration on camera
        
        Args:
            temp_ip: Camera's temporary DHCP IP address
            admin_user: Administrator username for authentication
            admin_pass: Administrator password for authentication
            ip_config: Dictionary containing IP configuration details
                       {'ip': '192.168.1.100', 'subnet': '255.255.255.0', 'gateway': '192.168.1.1'}
            protocol: 'HTTP' or 'HTTPS'
            
        Returns:
            Tuple of (success, message)
        """
        final_ip = ip_config.get('ip', '')
        subnet = ip_config.get('subnet', '255.255.255.0')
        gateway = ip_config.get('gateway', '')
        
        if not final_ip:
            return False, "No IP address provided in configuration"
        
        logging.info(f"Setting static IP {final_ip} on camera at {temp_ip}")
        
        # Construct the base URL
        base_url = f"{protocol.lower()}://{temp_ip}"
        
        # For newer Axis cameras, use the JSON API
        # Try modern API first, then fall back to older methods if needed
        success, message = self._set_ip_using_json_api(base_url, admin_user, admin_pass, final_ip, subnet, gateway)
        
        if success:
            return success, message
        
        # If JSON API failed, try the legacy param.cgi API
        logging.info(f"JSON API failed, trying legacy param.cgi API: {message}")
        return self._set_ip_using_param_cgi(base_url, admin_user, admin_pass, final_ip, subnet, gateway)

    def _subnet_mask_to_prefix_length(self, subnet_mask: str) -> int:
        """
        Convert a subnet mask to CIDR prefix length
        
        Args:
            subnet_mask: Subnet mask in dotted decimal format (e.g., 255.255.255.0)
            
        Returns:
            CIDR prefix length (e.g., 24)
        """
        try:
            # Use ipaddress module for reliable conversion
            network = ipaddress.IPv4Network(f"0.0.0.0/{subnet_mask}", strict=False)
            prefix_length = network.prefixlen
            return prefix_length
        except Exception as e:
            # Fallback to manual calculation if ipaddress module method fails
            try:
                # Convert the subnet mask to an integer
                subnet_int = int(ipaddress.IPv4Address(subnet_mask))
                
                # Count the number of '1' bits in the subnet mask
                binary = bin(subnet_int)[2:]  # Convert to binary and remove '0b' prefix
                prefix_length = binary.count('1')
                
                # Validate that the subnet mask is contiguous (all 1's followed by all 0's)
                if subnet_int & (subnet_int + 1) != 0:
                    raise ValueError("Invalid subnet mask: non-contiguous mask")
                    
                return prefix_length
                
            except Exception as e:
                raise ValueError(f"Invalid subnet mask format: {str(e)}")
                
    def _set_ip_using_json_api(self, base_url: str, admin_user: str, admin_pass: str,
                              final_ip: str, subnet: str, gateway: str) -> Tuple[bool, str]:
        """
        Set static IP using the modern JSON API
        
        Args:
            base_url: Base URL of the camera
            admin_user: Administrator username
            admin_pass: Administrator password
            final_ip: Final static IP address
            subnet: Subnet mask
            gateway: Default gateway
            
        Returns:
            Tuple of (success, message)
        """
        # Convert subnet mask to prefix length (e.g., 255.255.255.0 -> 24)
        try:
            prefix_length = self._subnet_mask_to_prefix_length(subnet)
            logging.info(f"Calculated prefix length {prefix_length} from subnet mask {subnet}")
        except ValueError as e:
            return False, f"Invalid subnet mask: {str(e)}"
        
        # Calculate broadcast address for completeness
        try:
            ip_obj = ipaddress.IPv4Address(final_ip)
            subnet_obj = ipaddress.IPv4Network(f"{final_ip}/{prefix_length}", strict=False)
            broadcast = str(subnet_obj.broadcast_address)
            logging.info(f"Calculated broadcast address: {broadcast}")
        except Exception as e:
            logging.warning(f"Could not calculate broadcast address: {str(e)}")
            broadcast = ""  # Not including broadcast address in payload
        
        # Modern JSON API endpoint 
        endpoint = "/axis-cgi/network_settings.cgi"
        url = urljoin(base_url, endpoint)
        
        # Prepare JSON payload with better structure for Axis OS 10.12
        payload = {
            "apiVersion": "1.0",
            "context": "AxisAutoConfig",
            "method": "setIPv4AddressConfiguration",
            "params": {
                "deviceName": "eth0",  # Primary interface name (typically eth0 on Axis cameras)
                "configurationMode": "static",
                "staticDefaultRouter": gateway,
                "staticAddressConfigurations": [
                    {
                        "address": final_ip,
                        "prefixLength": prefix_length
                    }
                ]
            }
        }
        
        # Add broadcast address if successfully calculated
        if broadcast:
            payload["params"]["staticAddressConfigurations"][0]["broadcast"] = broadcast
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        logging.info(f"Sending network configuration payload: {json.dumps(payload, indent=2)}")
        
        for attempt in range(self.retry_count):
            try:
                response = requests.post(
                    url,
                    json=payload,  # This sets the Content-Type header automatically
                    headers=headers,
                    auth=HTTPDigestAuth(admin_user, admin_pass),
                    timeout=self.timeout,
                    verify=False  # Skip SSL verification
                )
                
                # For debugging
                logging.info(f"Network settings response status: {response.status_code}")
                logging.info(f"Network settings response: {response.text}")
                
                # Check if request was successful
                if response.status_code == 200:
                    # Check if response contains JSON
                    try:
                        resp_json = response.json()
                        if resp_json.get('error'):
                            error_message = f"API error: {resp_json.get('error', {}).get('message', 'Unknown API error')}"
                            logging.error(error_message)
                            
                            if attempt < self.retry_count - 1:
                                logging.info(f"Retrying in {self.retry_delay} seconds...")
                                time.sleep(self.retry_delay)
                                continue
                            else:
                                return False, error_message
                    except ValueError:
                        # Not JSON response, but status code is 200
                        pass
                    
                    logging.info(f"Successfully set static IP {final_ip} on camera")
                    return True, f"Static IP successfully set to {final_ip}"
                
                # Handle specific error cases
                error_message = f"Failed to set static IP (HTTP {response.status_code}): {response.text}"
                logging.error(error_message)
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    return False, error_message
                    
            except Exception as e:
                logging.error(f"Error setting static IP: {str(e)}")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    return False, f"Error setting static IP: {str(e)}"
        
        # If we get here, all retry attempts failed
        return False, f"Failed to set static IP after {self.retry_count} attempts"

    def _set_ip_using_param_cgi(self, base_url: str, admin_user: str, admin_pass: str,
                               final_ip: str, subnet: str, gateway: str) -> Tuple[bool, str]:
        """
        Set static IP using the legacy param.cgi API
        
        Args:
            base_url: Base URL of the camera
            admin_user: Administrator username
            admin_pass: Administrator password
            final_ip: Final static IP address
            subnet: Subnet mask
            gateway: Default gateway
            
        Returns:
            Tuple of (success, message)
        """
        # Legacy param.cgi API endpoint
        endpoint = "/axis-cgi/param.cgi"
        url = urljoin(base_url, endpoint)
        
        # Parameters for the request - standard format for all Axis OS versions
        params = {
            "action": "update",
            "Network.InterfaceName": "eth0",  # Typically eth0 is the main interface
            "Network.BootProto": "static",    # Set to static mode
            "Network.IPAddress": final_ip,
            "Network.SubnetMask": subnet,
            "Network.DefaultRouter": gateway
        }
        
        logging.info(f"Using legacy param.cgi API to set static IP: {final_ip}, subnet: {subnet}, gateway: {gateway}")
        
        for attempt in range(self.retry_count):
            try:
                response = requests.get(
                    url,
                    params=params,
                    auth=HTTPDigestAuth(admin_user, admin_pass),
                    timeout=self.timeout,
                    verify=False  # Skip SSL verification
                )
                
                # Check if request was successful
                if response.status_code == 200:
                    # Some cameras return 200 but still have errors in the content
                    if "Error" in response.text:
                        error_message = f"API error: {response.text}"
                        logging.error(error_message)
                        
                        if attempt < self.retry_count - 1:
                            logging.info(f"Retrying in {self.retry_delay} seconds...")
                            time.sleep(self.retry_delay)
                            continue
                        else:
                            return False, error_message
                    
                    logging.info(f"Successfully set static IP {final_ip} using param.cgi API")
                    return True, f"Static IP successfully set to {final_ip}"
                
                # Handle specific error cases
                error_message = f"Failed to set static IP (HTTP {response.status_code}): {response.text}"
                logging.error(error_message)
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    return False, error_message
                    
            except Exception as e:
                logging.error(f"Error setting static IP: {str(e)}")
                
                if attempt < self.retry_count - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    return False, f"Error setting static IP: {str(e)}"
        
        # If we get here, all retry attempts failed
        return False, f"Failed to set static IP after {self.retry_count} attempts"
