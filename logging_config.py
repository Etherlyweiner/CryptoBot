"""
Logging configuration for CryptoBot
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    logger = logging.getLogger(name)
    
    # Only configure handlers if they haven't been added yet
    if not logger.handlers:
        # Set logging level
        logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create and configure file handler for detailed logging
        detailed_handler = RotatingFileHandler(
            log_dir / 'cryptobot_detailed.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        detailed_handler.setLevel(logging.DEBUG)
        detailed_handler.setFormatter(detailed_formatter)
        
        # Create and configure file handler for normal logging
        file_handler = RotatingFileHandler(
            log_dir / 'cryptobot.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(simple_formatter)
        
        # Create and configure console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        
        # Add handlers to logger
        logger.addHandler(detailed_handler)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

def setup_streamlit_logging():
    """Configure logging specifically for Streamlit"""
    # Get the streamlit logger
    st_logger = logging.getLogger('streamlit')
    st_logger.setLevel(logging.DEBUG)
    
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and configure file handler
    file_handler = RotatingFileHandler(
        log_dir / 'streamlit.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Add handler if it hasn't been added yet
    if not any(isinstance(h, RotatingFileHandler) for h in st_logger.handlers):
        st_logger.addHandler(file_handler)

# Initialize logging when module is imported
get_logger('cryptobot')
