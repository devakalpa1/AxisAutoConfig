#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Axis Camera Unified Setup & Configuration Tool
CSV Handler module for reading IP lists and generating reports

This module provides functionality for:
1. Validating and reading IP assignment lists from CSV files
2. Generating inventory reports of configured cameras
3. Creating sample CSV templates for users
"""

import csv
import os
import logging
import ipaddress
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple


class CSVHandler:
    """
    CSV file operations for IP lists and inventory reports
    
    Handles validation, parsing, and generation of CSV files for IP assignment
    and configuration reporting. Special attention is given to validating
    IP addresses and MAC addresses to prevent configuration errors.
    """
    
    def __init__(self):
        """Initialize CSV Handler module"""
        # No specific initialization needed
        pass
    
    def read_ip_list(self, file_path: str) -> List[Dict[str, str]]:
        """
        Read IP assignment list from CSV file with enhanced validation
        
        The CSV can be in one of two formats:
        1. Sequential assignment: A single column of IP addresses
           Example:
           FinalIPAddress
           192.168.1.101
           192.168.1.102
           
        2. MAC-specific assignment: Two columns with IP and MAC
           Example:
           FinalIPAddress,MACAddress
           192.168.1.101,00408C123456
           192.168.1.102,00408CAABBCC
        
        The function performs extensive validation:
        - Checks for duplicate IP addresses
        - Validates IP address format
        - In MAC-specific mode, validates MAC format and checks for duplicates
        - Verifies column headers match expected format
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of dictionaries containing IP assignments
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: For validation errors (duplicate IPs, format issues)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        results = []
        
        try:
            with open(file_path, 'r', newline='') as csvfile:
                # Determine the CSV format (with or without MAC addresses)
                sample = csvfile.read(1024)
                csvfile.seek(0)  # Return to beginning of file
                
                has_mac = 'mac' in sample.lower()
                
                # Parse the CSV
                reader = csv.DictReader(csvfile)
                
                # Validate headers
                headers = [h.lower() for h in reader.fieldnames or []]
                if 'finalipaddress' not in headers and 'ip' not in headers:
                    raise ValueError("CSV file must contain a 'FinalIPAddress' column")
                
                if has_mac and 'macaddress' not in headers and 'mac' not in headers:
                    raise ValueError("CSV file appears to be MAC-specific but is missing a 'MACAddress' column")
                
                # Read and validate each row
                for i, row in enumerate(reader, start=2):  # Start at 2 to account for header row
                    ip = (row.get('finalipaddress') or row.get('FinalIPAddress') or 
                          row.get('ip') or row.get('IP'))
                    
                    if not ip:
                        logging.warning(f"Skipping row {i}: Missing IP address")
                        continue
                    
                    # Validate IP address format
                    try:
                        ipaddress.IPv4Address(ip)
                    except ValueError:
                        logging.warning(f"Skipping row {i}: Invalid IP address '{ip}'")
                        continue
                    
                    # Process according to format
                    if has_mac:
                        mac = (row.get('macaddress') or row.get('MACAddress') or 
                               row.get('mac') or row.get('MAC'))
                        if not mac:
                            logging.warning(f"Skipping row {i}: Missing MAC address")
                            continue
                        
                        # Basic MAC address format validation
                        if not self._validate_mac_format(mac):
                            logging.warning(f"Skipping row {i}: Invalid MAC address format '{mac}'")
                            continue
                        
                        results.append({'ip': ip, 'mac': mac.upper()})
                    else:
                        results.append({'ip': ip})
        
        except csv.Error as e:
            raise ValueError(f"CSV parsing error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error reading CSV file: {str(e)}")
        
        if not results:
            raise ValueError("No valid IP assignments found in the CSV file")
        
        # Perform comprehensive validation of the results
        
        # 1. Check for duplicate IPs - critical to prevent network conflicts
        ips = [item['ip'] for item in results]
        duplicate_ips = self._find_duplicates(ips)
        if duplicate_ips:
            dup_list = ', '.join(duplicate_ips)
            logging.error(f"Duplicate IP addresses in CSV: {dup_list}")
            raise ValueError(f"Duplicate IP addresses found in CSV: {dup_list}")
        
        # 2. Check for duplicate MACs in MAC-specific mode
        if has_mac:
            macs = [item['mac'] for item in results]
            duplicate_macs = self._find_duplicates(macs)
            if duplicate_macs:
                dup_list = ', '.join(duplicate_macs)
                logging.error(f"Duplicate MAC addresses in CSV: {dup_list}")
                raise ValueError(f"Duplicate MAC addresses found in CSV: {dup_list}")
            
            # 3. Additional check - verify all MACs are properly formatted
            invalid_macs = []
            for idx, item in enumerate(results):
                if not self._is_valid_mac(item['mac']):
                    invalid_macs.append(f"Row {idx+2}: {item['mac']}")
            
            if invalid_macs:
                error_msg = f"Invalid MAC address format: {', '.join(invalid_macs)}"
                logging.error(error_msg)
                raise ValueError(error_msg)
        
        # 4. Verify all IPs are in the same subnet if more than one IP exists
        if len(ips) > 1:
            try:
                subnet_consistent = self._verify_ip_subnet_consistency(ips)
                if not subnet_consistent:
                    logging.warning(f"IP addresses in CSV span multiple subnets - this might cause connectivity issues")
            except Exception as e:
                logging.warning(f"Could not verify subnet consistency: {str(e)}")
        
        logging.info(f"Successfully validated and read {len(results)} IP assignments from {file_path}")
        return results
    
    def write_inventory_report(self, file_path: str, camera_data: List[Dict[str, Any]]) -> bool:
        """
        Write comprehensive inventory report to CSV file
        
        Creates a detailed report containing:
        - Camera identification (IPs, MACs, serials)
        - Configuration status for each operation performed
        - Timestamp information for tracking purposes
        - Version information for record-keeping
        
        Args:
            file_path: Path where to save the CSV file
            camera_data: List of dictionaries containing camera information
            
        Returns:
            True if successful, raises exception otherwise
        """
        try:
            if not camera_data:
                raise ValueError("No camera data provided for inventory report")
            
            # Define the standard fields we want in the report, in order
            standard_fields = [
                'final_ip', 'temp_ip', 'mac', 'verified_mac', 'serial', 'status'
            ]
            
            # Check what operation fields are present across all cameras
            operation_fields = set()
            for camera in camera_data:
                operations = camera.get('operations', {})
                operation_fields.update(operations.keys())
            
            # Prepare all fields
            fieldnames = standard_fields.copy()
            
            # Add operation fields as "operation_name_success" and "operation_name_message"
            for op in sorted(operation_fields):
                fieldnames.append(f"{op}_success")
                fieldnames.append(f"{op}_message")
            
            # Add timestamp and version information to the report
            report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            from axis_config_tool import __version__
            
            # Add metadata fields to the report
            fieldnames.extend(['report_generated', 'tool_version'])
            
            # Open file and write header
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Process each camera's data
                for camera in camera_data:
                    # Prepare a flattened row with all fields
                    row = {}
                    
                    # Add standard fields
                    for field in standard_fields:
                        row[field] = camera.get(field, '')
                    
                    # Add operation results (flattened)
                    operations = camera.get('operations', {})
                    for op in operation_fields:
                        op_data = operations.get(op, {})
                        row[f"{op}_success"] = op_data.get('success', '')
                        row[f"{op}_message"] = op_data.get('message', '')
                    
                    # Add metadata
                    row['report_generated'] = report_time
                    row['tool_version'] = __version__
                    
                    writer.writerow(row)
            
            logging.info(f"Wrote inventory report for {len(camera_data)} cameras to {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error writing inventory report: {str(e)}")
            raise
    
    def create_sample_csv(self, file_path: str, mode: str = 'sequential', count: int = 10, 
                         base_ip: str = '192.168.1.100') -> bool:
        """
        Create a sample CSV file with IP addresses for testing
        
        Args:
            file_path: Path where to save the CSV file
            mode: 'sequential' or 'mac_specific'
            count: Number of entries to generate
            base_ip: Base IP address to start from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse the base IP to generate sequential IPs
            ip_parts = base_ip.split('.')
            if len(ip_parts) != 4:
                raise ValueError(f"Invalid IP address format: {base_ip}")
            
            base = int(ip_parts[3])
            prefix = '.'.join(ip_parts[:3])
            
            with open(file_path, 'w', newline='') as csvfile:
                if mode == 'sequential':
                    # Create a sequential IP list
                    writer = csv.writer(csvfile)
                    writer.writerow(['FinalIPAddress'])
                    
                    for i in range(count):
                        writer.writerow([f"{prefix}.{base + i}"])
                        
                elif mode == 'mac_specific':
                    # Create a MAC-to-IP mapping
                    writer = csv.writer(csvfile)
                    writer.writerow(['FinalIPAddress', 'MACAddress'])
                    
                    # Generate sample MAC addresses (just for demonstration)
                    for i in range(count):
                        # Generate a sample MAC address without delimiters
                        mac = f"00408C{i:02X}{i+10:02X}{i+20:02X}"
                        ip = f"{prefix}.{base + i}"
                        writer.writerow([ip, mac])
                else:
                    raise ValueError(f"Invalid mode: {mode}")
            
            logging.info(f"Created sample CSV file with {count} entries in {mode} mode at {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating sample CSV: {str(e)}")
            return False
    
    def _verify_ip_subnet_consistency(self, ip_addresses: List[str]) -> bool:
        """
        Check if all IP addresses are in the same subnet
        
        Args:
            ip_addresses: List of IP addresses as strings
            
        Returns:
            True if all IPs are in the same subnet, False otherwise
        """
        if not ip_addresses or len(ip_addresses) < 2:
            return True
            
        try:
            # Use the first IP to determine the subnet (assuming /24)
            first_ip = ipaddress.IPv4Address(ip_addresses[0])
            expected_network = ipaddress.IPv4Network(f"{first_ip}/24", strict=False)
            
            # Check all other IPs against this subnet
            for ip in ip_addresses[1:]:
                current_ip = ipaddress.IPv4Address(ip)
                if current_ip not in expected_network:
                    return False
                    
            return True
        except Exception as e:
            logging.warning(f"Error checking subnet consistency: {str(e)}")
            return True  # Default to True on error to not block the process
    
    def _is_valid_mac(self, mac: str) -> bool:
        """
        Perform comprehensive MAC address validation
        
        This goes beyond basic format checking to ensure:
        - MAC follows correct format (with or without delimiters)
        - Characters are valid hexadecimal digits
        - No invalid patterns (all zeros, all FFs, etc.)
        
        Args:
            mac: MAC address string to validate
            
        Returns:
            True if MAC is valid, False otherwise
        """
        # Remove any delimiters
        clean_mac = mac.replace(':', '').replace('-', '').replace('.', '').upper()
        
        # Check length and hex characters
        if len(clean_mac) != 12 or not all(c in '0123456789ABCDEF' for c in clean_mac):
            return False
            
        # Check for invalid patterns (all zeros, all FFs)
        if clean_mac == '000000000000' or clean_mac == 'FFFFFFFFFFFF':
            return False
            
        return True
    
    def _find_duplicates(self, items: List[str]) -> List[str]:
        """
        Find duplicate items in a list
        
        Important for identifying both duplicate IP addresses and MAC addresses
        in CSV files, which would cause conflicts during configuration.
        
        Args:
            items: List of items to check for duplicates
            
        Returns:
            List of duplicate items found
        """
        seen = set()
        duplicates = set()
        
        for item in items:
            if item in seen:
                duplicates.add(item)
            else:
                seen.add(item)
        
        return list(duplicates)
    
    def _validate_mac_format(self, mac: str) -> bool:
        """
        Validate basic MAC address format (for initial parsing)
        
        Detects common MAC address formats:
        - 00:40:8C:12:34:56 (colon delimited)
        - 00-40-8C-12-34-56 (hyphen delimited)
        - 00408C123456 (no delimiters)
        
        For more comprehensive validation, use _is_valid_mac()
        
        Args:
            mac: MAC address string to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        # Remove any whitespace
        mac = mac.strip()
        
        # Check for common MAC address formats
        formats = [
            # 00:40:8C:12:34:56
            lambda m: len(m) == 17 and m[2] == ':' and m[5] == ':' and m[8] == ':' and m[11] == ':' and m[14] == ':',
            
            # 00-40-8C-12-34-56
            lambda m: len(m) == 17 and m[2] == '-' and m[5] == '-' and m[8] == '-' and m[11] == '-' and m[14] == '-',
            
            # 00408C123456
            lambda m: len(m) == 12 and all(c.isalnum() for c in m)
        ]
        
        return any(format_check(mac) for format_check in formats)


# Basic test if run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(levelname)s - %(message)s')
    
    handler = CSVHandler()
    
    # Example usage (commented out as there's no actual file)
    # ip_list = handler.read_ip_list("sample_ips.csv")
    # print(f"Read {len(ip_list)} IP assignments")
