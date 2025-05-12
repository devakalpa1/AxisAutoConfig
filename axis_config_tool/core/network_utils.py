#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
Network utilities for camera connectivity operations
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
                          max_wait_time: int = 60, check_interval: int = 2) -> bool:
    """
    Wait for a camera to come online at the specified IP address
    
    Args:
        ip: Camera IP address to check
        username: Admin username for authentication
        password: Admin password for authentication
        protocol: 'HTTP' or 'HTTPS' 
        max_wait_time: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
        
    Returns:
        True if camera comes online, False if timeout or error
    """
    logging.info(f"Waiting for camera to become available at {ip} (timeout: {max_wait_time}s)")
    
    base_url = f"{protocol.lower()}://{ip}"
    endpoint = "/axis-cgi/usergroup.cgi"  # Simple endpoint to check auth
    url = urljoin(base_url, endpoint)
    
    start_time = time.time()
    elapsed = 0
    
    while elapsed < max_wait_time:
        # Try ping first (faster)
        if ping_host(ip):
            logging.info(f"Host {ip} is responding to ping")
            
            # Try HTTP connection to verify camera web interface is up
            try:
                response = requests.get(
                    url,
                    auth=HTTPDigestAuth(username, password),
                    timeout=5,
                    verify=False
                )
                
                if response.status_code == 200:
                    logging.info(f"Camera at {ip} is online and accepting authentication")
                    return True
                else:
                    logging.debug(f"Camera at {ip} responded with status code {response.status_code}")
            except Exception as e:
                logging.debug(f"HTTP connection attempt to {ip} failed: {str(e)}")
        
        # Wait before next check
        time.sleep(check_interval)
        elapsed = time.time() - start_time
        
        if elapsed >= max_wait_time:
            logging.warning(f"Timeout waiting for camera at {ip} to come online")
        elif elapsed >= max_wait_time / 2:
            logging.info(f"Still waiting for camera at {ip} to come online ({int(elapsed)}s elapsed)")
    
    return False


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


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address format
    
    Args:
        ip: IP address to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ValueError:
        return False


def is_ip_in_network(ip: str, network: str) -> bool:
    """
    Check if an IP address is in a network range
    
    Args:
        ip: IP address to check
        network: Network range in CIDR format (e.g., '192.168.1.0/24')
        
    Returns:
        True if IP is in network, False otherwise
    """
    try:
        return ipaddress.IPv4Address(ip) in ipaddress.IPv4Network(network)
    except ValueError:
        logging.error(f"Invalid IP address or network format: {ip}, {network}")
        return False


def check_port_open(ip: str, port: int, timeout: int = 2) -> bool:
    """
    Check if a specific TCP port is open on a host
    
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
