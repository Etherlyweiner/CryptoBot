"""Start Edge browser with remote debugging enabled."""

import subprocess
import os
import time
import sys
import psutil

def is_edge_running_with_debug():
    """Check if Edge is already running with debug port."""
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] == 'msedge.exe':
                cmdline = proc.info.get('cmdline', [])
                if any('--remote-debugging-port=9222' in arg for arg in cmdline):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def start_edge_with_debug():
    """Start Microsoft Edge with remote debugging enabled."""
    try:
        # Check if Edge is already running with debug port
        if is_edge_running_with_debug():
            print("Edge is already running with remote debugging enabled")
            return True
            
        # Get Edge installation path
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
        
        edge_path = None
        for path in edge_paths:
            if os.path.exists(path):
                edge_path = path
                break
                
        if not edge_path:
            print("Microsoft Edge not found. Please install Edge browser.")
            return False
            
        # Start Edge with remote debugging
        cmd = [
            edge_path,
            "--remote-debugging-port=9222",
            "--user-data-dir=" + os.path.abspath("browser_data"),
            "--no-first-run",
            "--no-default-browser-check",
            "https://photon-sol.tinyastro.io/en/discover"
        ]
        
        subprocess.Popen(cmd)
        print("Started Edge with remote debugging enabled")
        print("Please log in to Photon DEX and connect your wallet")
        return True
        
    except Exception as e:
        print(f"Error starting Edge: {str(e)}")
        return False

if __name__ == "__main__":
    if not start_edge_with_debug():
        sys.exit(1)
    
    print("\nWaiting for you to authenticate...")
    print("1. Log in to Photon DEX")
    print("2. Connect your Phantom wallet")
    print("3. Complete any security verifications")
    print("\nOnce done, you can start the trading bot")
