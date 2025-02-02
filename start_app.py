"""
CryptoBot Application Launcher
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from logging_config import setup_logging, get_logger
from config import config

logger = get_logger('Launcher')

def check_environment() -> bool:
    """Check if the environment is properly set up"""
    try:
        # Check if .env file exists
        if not Path('.env').exists():
            logger.error("No .env file found. Please create one with your API credentials.")
            return False
            
        # Validate configuration
        if not config.validate_config():
            logger.error("Invalid configuration. Please check your .env file settings.")
            return False
            
        # Check if virtual environment exists
        if not Path('venv_py310').exists():
            logger.error("Virtual environment not found. Please run setup.py first.")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Environment check failed: {str(e)}")
        return False

def get_python_executable() -> str:
    """Get the correct Python executable path"""
    try:
        if sys.platform == 'win32':
            return str(Path('venv_py310/Scripts/python.exe').absolute())
        return str(Path('venv_py310/bin/python').absolute())
    except Exception as e:
        logger.error(f"Error getting Python executable: {str(e)}")
        raise

def get_streamlit_executable() -> str:
    """Get the correct Streamlit executable path"""
    try:
        if sys.platform == 'win32':
            return str(Path('venv_py310/Scripts/streamlit.exe').absolute())
        return str(Path('venv_py310/bin/streamlit').absolute())
    except Exception as e:
        logger.error(f"Error getting Streamlit executable: {str(e)}")
        raise

def kill_existing_processes():
    """Kill any existing Python/Streamlit processes"""
    try:
        if sys.platform == 'win32':
            os.system('taskkill /f /im python.exe >nul 2>&1')
            os.system('taskkill /f /im streamlit.exe >nul 2>&1')
        else:
            os.system('pkill -f "python|streamlit" >/dev/null 2>&1')
        logger.info("Cleaned up existing processes")
    except Exception as e:
        logger.error(f"Error killing existing processes: {str(e)}")

def start_application():
    """Start the CryptoBot application"""
    try:
        # Set up logging
        setup_logging()
        logger.info("Starting CryptoBot application...")
        
        # Check environment
        if not check_environment():
            sys.exit(1)
        
        # Kill existing processes
        kill_existing_processes()
        
        # Get executables
        streamlit_exe = get_streamlit_executable()
        
        # Start Streamlit app
        cmd = [streamlit_exe, 'run', 'app.py']
        
        # Set environment variables
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path.cwd())
        
        # Run the application
        logger.info("Launching Streamlit application...")
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Monitor the process
        while True:
            output = process.stdout.readline()
            if output:
                print(output.strip())
            if process.poll() is not None:
                break
                
        if process.returncode != 0:
            logger.error("Application crashed. Check the logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    start_application()
