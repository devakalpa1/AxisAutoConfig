#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
Camera discovery module
"""

import socket
import logging
import subprocess
import platform
from typing import List, Tuple, Dict, Optional
from urllib.parse import urlparse
import requests
from requests.exceptions import RequestException


class CameraDiscovery:
    """Camera discovery functionality for Axis cameras"""
    
    def __init__(self):
        """Initialize the Camera Discovery module"""
        self.timeout = 2  # Timeout for connection attempts (seconds)
    
    def check_device(self, ip: str) -> bool:
        """
        Check if a device at the specified IP is potentially an Axis camera
        
        This performs multiple checks to identify Axis cameras:
        1. Basic connectivity (ping)
        2. HTTP port availability
        3. Axis-specific response characteristics
        
        Args:
            ip: IP address to check
            
        Returns:
            True if device is responsive and likely an Axis camera, False otherwise
        """
        # First check basic connectivity
        is_pingable = self._check_ping(ip)
        if not is_pingable:
            logging.debug(f"Device at {ip} did not respond to ping")
            # Continue with other checks even if ping fails (some cameras may have ping disabled)
        
        # Check for Axis-specific HTTP characteristics
        is_axis = self._check_axis_specific(ip)
        if is_axis:
            logging.info(f"Device at {ip} identified as an Axis camera")
            return True
            
        # Try basic HTTP connectivity as a fallback
        if self._check_http_connection(ip):
            logging.info(f"Device at {ip} has open HTTP port (possibly an Axis camera)")
            return True
            
        # If device responded to ping but not to HTTP, it's likely not a camera
        if is_pingable:
            logging.debug(f"Device at {ip} responded to ping but doesn't appear to be an Axis camera")
            
        return False
    
    def _check_axis_specific(self, ip: str) -> bool:
        """
        Check for Axis-specific characteristics to identify cameras
        
        Args:
            ip: IP address to check
            
        Returns:
            True if likely an Axis camera, False otherwise
        """
        try:
            # First try to access a common Axis endpoint
            for endpoint in ['/axis-cgi/usergroup.cgi', '/axis-cgi/basicdeviceinfo.cgi', '/']:
                try:
                    url = f"http://{ip}{endpoint}"
                    response = requests.head(
                        url,
                        timeout=self.timeout,
                        allow_redirects=False
                    )
                    
                    # Check for Axis-specific HTTP headers
                    headers = response.headers
                    server_header = headers.get('Server', '').lower()
                    
                    # Axis cameras often have "AXIS" in their server header
                    if 'axis' in server_header:
                        logging.info(f"Axis server header detected at {ip}")
                        return True
                        
                    # Response code 401 (Unauthorized) is common for Axis cameras with default endpoints
                    if response.status_code == 401:
                        auth_header = headers.get('WWW-Authenticate', '').lower()
                        if 'digest' in auth_header and ('axis' in auth_header or 'realm' in auth_header):
                            logging.info(f"Axis digest authentication detected at {ip}")
                            return True
                            
                    # Sometimes, an Axis camera redirects to the web interface
                    if response.status_code == 302 or response.status_code == 301:
                        location = headers.get('Location', '').lower()
                        if 'index.html' in location or 'axis' in location:
                            logging.info(f"Axis-like redirect detected at {ip}")
                            return True
                    
                except requests.RequestException:
                    # If this endpoint fails, try the next one
                    continue
            
            # Try a GET request to analyze the response body
            try:
                response = requests.get(
                    f"http://{ip}/",
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                # Look for Axis indicators in the response content
                content = response.text.lower()
                if any(x in content for x in ['axis communications', 'axis camera', 'axis network camera']):
                    logging.info(f"Axis-specific content detected at {ip}")
                    return True
            except requests.RequestException:
                pass
                
            return False
            
        except Exception as e:
            logging.debug(f"Error in Axis-specific check for {ip}: {str(e)}")
            return False
    
    def _check_ping(self, ip: str) -> bool:
        """
        Check if a device responds to ping
        
        Args:
            ip: IP address to ping
            
        Returns:
            True if ping successful, False otherwise
        """
        try:
            # Platform-specific ping command
            system = platform.system().lower()
            
            if system == "windows":
                # Windows ping command (less verbose, faster, single attempt)
                args = ["ping", "-n", "1", "-w", f"{int(self.timeout*1000)}", ip]
            else:
                # Unix/Linux/MacOS ping command
                args = ["ping", "-c", "1", "-W", str(self.timeout), ip]
            
            # Run ping command
            result = subprocess.run(
                args, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout + 1  # Add 1 second margin
            )
            
            # Check if ping was successful (return code 0)
            return result.returncode == 0
            
        except (subprocess.SubprocessError, OSError) as e:
            logging.debug(f"Ping failed for {ip}: {str(e)}")
            return False
    
    def _check_http_connection(self, ip: str) -> bool:
        """
        Check if a device has an open HTTP port (80)
        
        Args:
            ip: IP address to check
            
        Returns:
            True if HTTP connection can be established, False otherwise
        """
        try:
            # Try to connect to HTTP port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, 80))
            sock.close()
            
            if result == 0:
                # HTTP port is open, try a simple GET request
                try:
                    # Attempt a HEAD request to "/" with a short timeout
                    # We don't authenticate yet, just check if the server responds
                    response = requests.head(
                        f"http://{ip}/", 
                        timeout=self.timeout,
                        allow_redirects=False
                    )
                    
                    # Any response (even 401 Unauthorized) suggests a web server is present
                    return True
                    
                except RequestException:
                    # If the HTTP request fails, but the port was open,
                    # still consider it as potentially a camera
                    return True
            
            return False
            
        except (socket.error, OSError) as e:
            logging.debug(f"HTTP connection failed for {ip}: {str(e)}")
            return False
    
    def get_device_info(self, ip: str, username: str = None, password: str = None) -> Dict[str, str]:
        """
        Get basic device information
        
        This method retrieves minimal device information for discovery purposes
        
        Args:
            ip: IP address of the camera
            username: Optional username for authentication
            password: Optional password for authentication
            
        Returns:
            Dictionary with device information
        """
        # Simple implementation returning minimal info
        return {
            "ip": ip,
            "status": "discovered"
        }


# Basic test if run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(levelname)s - %(message)s')
    
    discovery = CameraDiscovery()
    
    # Test with localhost
    test_ip = "127.0.0.1"
    result = discovery.check_device(test_ip)
    
    print(f"Device check for {test_ip}: {'Responsive' if result else 'Not responsive'}")
