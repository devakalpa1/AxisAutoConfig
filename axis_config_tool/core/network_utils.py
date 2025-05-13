#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
Network utilities for camera connectivity operations

This module provides robust networking functionality for:
1. Validating and verifying camera connectivity
2. Waiting for cameras to become available after IP changes
3. Checking network conditions and port accessibility
4. Validating IP address and subnet configurations

These utilities are critical to the camera configuration workflow,
particularly when transitioning cameras from temporary DHCP addresses
to final static IP configurations.

The implementation uses multiple connection verification methods
(ping, HTTP requests, port checks) for maximum reliability across
different network environments and camera firmware versions.
"""

import socket
import time
import logging
import ipaddress
import requests
import subprocess
import platform
from typing import Tuple, Optional, List, Dict
from requests.auth import HTTPDigestAuth
from urllib.parse import urljoin


def wait_for_camera_online(ip: str, username: str, password: str, protocol: str = "HTTP", 
                          max_wait_time: int = 60, check_interval: int = 2) -> Tuple[bool, float]:
    """
    Wait for a camera to come online at the specified IP address
    
    This function is critical when cameras change IP addresses (e.g., going from
    DHCP to static IP). It implements a multi-layered verification approach:
    
    1. Initial ping check (fastest, network-level connectivity)
    2. Port availability check (TCP socket connection to HTTP/HTTPS port)
    3. API endpoint authentication (final verification of camera web services)
    
    The progressive approach minimizes unnecessary authentication attempts
    and provides detailed feedback about connectivity issues.
    
    Args:
        ip: Camera IP address to check
        username: Admin username for authentication
        password: Admin password for authentication
        protocol: 'HTTP' or 'HTTPS' 
        max_wait_time: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
        
    Returns:
        Tuple of (success, elapsed_time):
        - success: True if camera comes online, False if timeout or error
        - elapsed_time: Time taken for camera to come online (seconds)
    """
    logging.info(f"Waiting for camera to become available at {ip} (timeout: {max_wait_time}s)")
    
    base_url = f"{protocol.lower()}://{ip}"
    endpoint = "/axis-cgi/usergroup.cgi"  # Simple endpoint to check auth
    url = urljoin(base_url, endpoint)
    
    # Determine which port to check based on protocol
    port = 80 if protocol.lower() == "http" else 443
    
    start_time = time.time()
    elapsed = 0
    
    # Track connection attempts for logging and troubleshooting
    ping_attempts = 0
    port_attempts = 0
    http_attempts = 0
    
    while elapsed < max_wait_time:
        # STEP 1: Try ping first (fastest method)
        ping_attempts += 1
        if ping_host(ip):
            logging.info(f"Host {ip} is responding to ping")
            
            # STEP 2: Check if port is open
            port_attempts += 1
            if check_port_open(ip, port):
                logging.info(f"Port {port} is open on {ip}")
                
                # STEP 3: Try HTTP connection to verify camera web interface is up
                http_attempts += 1
                try:
                    response = requests.get(
                        url,
                        auth=HTTPDigestAuth(username, password),
                        timeout=5,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        elapsed_time = time.time() - start_time
                        logging.info(f"Camera at {ip} is online and accepting authentication (took {elapsed_time:.2f}s)")
                        return True, elapsed_time
                    else:
                        logging.debug(f"Camera at {ip} responded with status code {response.status_code}")
                        # If we get a 401, the camera is online but credentials might be wrong
                        if response.status_code == 401:
                            logging.warning(f"Authentication failed for {ip} - check credentials")
                except requests.exceptions.SSLError:
                    logging.warning(f"SSL verification failed for {ip} - certificate may be self-signed")
                    # We still consider the camera online if we get an SSL error, as this indicates
                    # the web server is responding but with a self-signed/invalid certificate
                    elapsed_time = time.time() - start_time
                    return True, elapsed_time
                except Exception as e:
                    logging.debug(f"HTTP connection attempt to {ip} failed: {str(e)}")
            else:
                logging.debug(f"Port {port} not responding on {ip}")
        
        # Wait before next check
        time.sleep(check_interval)
        elapsed = time.time() - start_time
        
        # Provide progressive feedback during longer waits
        if elapsed >= max_wait_time:
            logging.warning(f"Timeout waiting for camera at {ip} to come online after {max_wait_time}s")
        elif elapsed >= max_wait_time * 0.75:
            logging.info(f"Still waiting for camera at {ip} to come online ({int(elapsed)}s elapsed, 75% of timeout)")
        elif elapsed >= max_wait_time / 2 and elapsed < max_wait_time * 0.75:
            logging.info(f"Still waiting for camera at {ip} to come online ({int(elapsed)}s elapsed, 50% of timeout)")
    
    # Log detailed connection attempt statistics for troubleshooting
    logging.debug(f"Connection attempts for {ip}: ping={ping_attempts}, port={port_attempts}, http={http_attempts}")
    return False, elapsed


def ping_host(ip: str, count: int = 1, timeout: int = 2) -> bool:
    """
    Ping a host to check if it's online
    
    Args:
        ip: IP address to ping
        count: Number of ping packets to send
        timeout: Timeout in seconds
        
    Returns:
        True if host responds to ping, False otherwise
    """
    try:
        # Platform-specific ping command
        system = platform.system().lower()
        
        if system == "windows":
            args = ["ping", "-n", str(count), "-w", f"{int(timeout*1000)}", ip]
        else:
            args = ["ping", "-c", str(count), "-W", str(timeout), ip]
        
        # Run ping command
        result = subprocess.run(
            args, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout + 1  # Add 1 second margin
        )
        
        # Check if ping was successful (return code 0)
        return result.returncode == 0
            
    except (subprocess.SubprocessError, OSError) as e:
        logging.debug(f"Ping failed for {ip}: {str(e)}")
        return False


def validate_ip_address(ip: str) -> Tuple[bool, str]:
    """
    Validate IP address format and provide detailed feedback
    
    Uses the ipaddress module for RFC-compliant validation of IPv4 addresses.
    This function checks for:
    - Proper format (4 octets of numbers 0-255 separated by dots)
    - Reserved/special addresses (like 0.0.0.0, 127.0.0.1, etc.)
    - Private network ranges
    
    Args:
        ip: IP address to validate
        
    Returns:
        Tuple of (valid, message):
        - valid: True if valid IPv4 address, False otherwise
        - message: Empty string if valid, error message if invalid
    """
    try:
        # Parse the IP address
        ip_obj = ipaddress.IPv4Address(ip)
        
        # Check for special/reserved addresses that might cause issues
        if ip_obj.is_loopback:
            return False, "Loopback address (127.x.x.x) not allowed for camera configuration"
        if ip_obj.is_multicast:
            return False, "Multicast address not allowed for camera configuration"
        if ip_obj.is_reserved:
            return False, "Reserved address not allowed for camera configuration"
        if ip_obj.is_unspecified:  # 0.0.0.0
            return False, "Unspecified address (0.0.0.0) not allowed"
            
        # For informational purposes, log if the IP is in a private range
        if ip_obj.is_private:
            logging.debug(f"IP {ip} is in a private address range (recommended)")
            
        # Valid IP address
        return True, ""
    except ValueError as e:
        return False, f"Invalid IP format: {str(e)}"


def is_ip_in_network(ip: str, network: str) -> Tuple[bool, str]:
    """
    Check if an IP address is in a network range
    
    This function verifies if a given IP address belongs to a specified
    network range. It's useful for:
    - Validating that static IPs are in the correct subnet
    - Ensuring gateway and camera IPs are in the same network
    - Detecting potential routing issues before they occur
    
    Args:
        ip: IP address to check
        network: Network range in CIDR format (e.g., '192.168.1.0/24')
        
    Returns:
        Tuple of (in_network, message):
        - in_network: True if IP is in network, False otherwise
        - message: Empty string if in network, error message if not
    """
    try:
        ip_obj = ipaddress.IPv4Address(ip)
        network_obj = ipaddress.IPv4Network(network, strict=False)
        
        if ip_obj in network_obj:
            return True, ""
        else:
            return False, f"IP address {ip} is not in network {network}"
            
    except ValueError as e:
        msg = f"Invalid IP address or network format: {str(e)}"
        logging.error(msg)
        return False, msg


def check_port_open(ip: str, port: int, timeout: int = 2) -> bool:
    """
    Check if a specific TCP port is open on a host
    
    This function performs a TCP socket connection test to determine
    if a specific port is open and accepting connections. This is 
    particularly useful for verifying that a camera's web server is
    functioning before attempting more complex API requests.
    
    Args:
        ip: IP address to check
        port: Port number to check
        timeout: Timeout in seconds
        
    Returns:
        True if port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        # If result is 0, the port is open
        return result == 0
        
    except socket.error as e:
        logging.debug(f"Socket error checking port {port} on {ip}: {str(e)}")
        return False


def calculate_network_parameters(ip: str, subnet_mask: str) -> Dict[str, str]:
    """
    Calculate network parameters from IP address and subnet mask
    
    This utility function computes various useful network values:
    - Network address (e.g., 192.168.1.0)
    - Broadcast address (e.g., 192.168.1.255)
    - CIDR notation (e.g., 192.168.1.0/24)
    - Valid IP range (first usable to last usable)
    - Prefix length (e.g., 24)
    
    These values are useful for:
    - Validating gateway addresses
    - Computing proper IP ranges for DHCP
    - Ensuring IPs are within valid ranges
    - Network configuration validation
    
    Args:
        ip: IP address in dotted decimal format (e.g., '192.168.1.100')
        subnet_mask: Subnet mask in dotted decimal format (e.g., '255.255.255.0')
        
    Returns:
        Dictionary containing calculated network parameters:
        {
            'network_address': str,
            'broadcast_address': str, 
            'first_usable': str,
            'last_usable': str,
            'cidr': str,
            'prefix_length': int,
            'num_hosts': int
        }
    """
    try:
        # Create the network object
        interface = ipaddress.IPv4Interface(f"{ip}/{subnet_mask}")
        network = interface.network
        
        # First and last usable addresses
        host_addresses = list(network.hosts())
        first_usable = str(host_addresses[0]) if host_addresses else None
        last_usable = str(host_addresses[-1]) if host_addresses else None
        
        # Calculate results
        results = {
            'network_address': str(network.network_address),
            'broadcast_address': str(network.broadcast_address),
            'cidr': str(network),
            'prefix_length': network.prefixlen,
            'first_usable': first_usable,
            'last_usable': last_usable,
            'num_hosts': network.num_addresses - 2  # Subtract network and broadcast addresses
        }
        
        return results
        
    except ValueError as e:
        logging.error(f"Failed to calculate network parameters: {str(e)}")
        return {
            'error': f"Invalid network parameters: {str(e)}"
        }
