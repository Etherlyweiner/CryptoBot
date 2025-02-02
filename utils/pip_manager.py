"""
Utility module for managing pip updates and package dependencies.
"""

import subprocess
import sys
import logging
import pkg_resources
from packaging import version
from typing import Tuple, Optional
import os

logger = logging.getLogger(__name__)

def get_pip_version() -> Tuple[str, str]:
    """
    Get current and latest pip versions.
    
    Returns:
        Tuple[str, str]: (current_version, latest_version)
    """
    try:
        # Get current version
        current_version = pkg_resources.get_distribution('pip').version
        
        # Get latest version using pip index
        process = subprocess.run(
            [sys.executable, '-m', 'pip', 'index', 'versions', 'pip'],
            capture_output=True,
            text=True
        )
        
        # Parse output to find latest version
        lines = process.stdout.split('\n')
        latest_version = None
        for line in lines:
            if 'Available versions:' in line:
                versions = line.split(':')[1].strip().split(',')
                latest_version = versions[0].strip()
                break
                
        if not latest_version:
            latest_version = current_version
            
        return current_version, latest_version
        
    except Exception as e:
        logger.error(f"Error checking pip version: {str(e)}")
        return "unknown", "unknown"

def update_pip(force: bool = False) -> Optional[str]:
    """
    Update pip if a newer version is available.
    
    Args:
        force (bool): Force update even if current version is up to date
        
    Returns:
        Optional[str]: Error message if update fails, None if successful
    """
    try:
        current, latest = get_pip_version()
        
        # Skip update if already on latest version and not forced
        if not force and version.parse(current) >= version.parse(latest):
            logger.info(f"pip is already up to date (version {current})")
            return None
            
        logger.info(f"Updating pip from version {current} to {latest}")
        
        # Use python -m pip to avoid system pip conflicts
        process = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'],
            capture_output=True,
            text=True
        )
        
        if process.returncode != 0:
            error_msg = f"Failed to update pip: {process.stderr}"
            logger.error(error_msg)
            return error_msg
            
        logger.info(f"Successfully updated pip to version {latest}")
        return None
        
    except Exception as e:
        error_msg = f"Error updating pip: {str(e)}"
        logger.error(error_msg)
        return error_msg

def check_and_update_pip() -> None:
    """
    Check for pip updates and perform update if needed.
    Logs results but doesn't raise exceptions.
    """
    try:
        current, latest = get_pip_version()
        
        if version.parse(current) < version.parse(latest):
            logger.info(f"New pip version available: {current} -> {latest}")
            if error := update_pip():
                logger.warning(f"Pip update failed: {error}")
        else:
            logger.debug(f"pip is up to date (version {current})")
            
    except Exception as e:
        logger.error(f"Error in pip version check: {str(e)}")

if __name__ == "__main__":
    # Configure basic logging when run directly
    logging.basicConfig(level=logging.INFO)
    check_and_update_pip()
