"""
Minimal test script to verify Streamlit configuration and logging setup.
"""

import streamlit as st
import logging
from logging_config import setup_logging
import time
from pathlib import Path
from config import config

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

def main():
    st.title("CryptoBot Configuration Test")
    
    # Test logging
    logger.info("Starting configuration test")
    logger.warning("This is a test warning message")
    logger.error("This is a test error message")
    
    # Display configuration
    st.subheader("Current Configuration")
    st.json(config.to_dict())
    
    # Display log file contents
    log_dir = Path("logs")
    st.subheader("Log Files")
    
    if not log_dir.exists():
        st.warning("Logs directory not found. Creating it now...")
        log_dir.mkdir(exist_ok=True)
    
    for log_file in ["cryptobot.log", "error.log", "trading.log"]:
        log_path = log_dir / log_file
        if log_path.exists():
            with open(log_path, 'r') as f:
                content = f.read().strip()
                if content:
                    st.text_area(f"Contents of {log_file}", value=content, height=200)
                else:
                    st.info(f"{log_file} is empty")
        else:
            st.warning(f"{log_file} not found")
    
    # Test caching
    @st.cache_data(ttl=60)
    def cached_function():
        time.sleep(2)  # Simulate expensive operation
        return "Cached result"
    
    # Test session state
    if 'counter' not in st.session_state:
        st.session_state.counter = 0
    
    st.subheader("Cache and Session State Test")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Cached result (should be instant after first run):", cached_function())
        
        if st.button("Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared!")
    
    with col2:
        if st.button("Increment Counter"):
            st.session_state.counter += 1
        st.write("Session state counter:", st.session_state.counter)
    
    # Test configuration validation
    st.subheader("Configuration Validation")
    if config.validate_config():
        st.success("Configuration is valid!")
    else:
        st.error("Configuration validation failed. Check the logs for details.")
    
    # Display Streamlit settings
    st.subheader("Streamlit Settings")
    st.json({
        "Theme": {
            "Primary Color": st.get_option("theme.primaryColor"),
            "Background Color": st.get_option("theme.backgroundColor"),
            "Text Color": st.get_option("theme.textColor"),
            "Font": st.get_option("theme.font")
        },
        "Server": {
            "Port": st.get_option("server.port"),
            "Address": st.get_option("server.address"),
            "Headless": st.get_option("server.headless")
        }
    })

if __name__ == "__main__":
    main()
