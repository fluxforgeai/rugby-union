"""
Port availability utilities for Gradio application.

Handles finding available ports for the web interface.
"""

import socket
from typing import Optional


def find_available_port(start_port: int = 7860, end_port: int = 7870) -> Optional[int]:
    """
    Find an available port in the specified range.
    
    Scans through ports in the given range and returns the first available one.
    
    Args:
        start_port: Starting port number to check
        end_port: Ending port number to check (inclusive)
        
    Returns:
        int: Available port number, or None if no ports available
    """
    for port in range(start_port, end_port + 1):
        if _is_port_available(port):
            return port
    
    return None


def _is_port_available(port: int) -> bool:
    """
    Check if a specific port is available for binding.
    
    Args:
        port: Port number to check
        
    Returns:
        bool: True if port is available, False otherwise
    """
    try:
        # Create a socket and try to bind to the port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Set socket option to reuse address
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try to bind to the port
            sock.bind(('127.0.0.1', port))
            return True
            
    except socket.error:
        # Port is in use or not available
        return False


def get_port_status(port: int) -> str:
    """
    Get human-readable status of a port.
    
    Args:
        port: Port number to check
        
    Returns:
        str: Status description
    """
    if _is_port_available(port):
        return f"Port {port} is available"
    else:
        return f"Port {port} is in use"