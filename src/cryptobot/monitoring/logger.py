"""
Logging Configuration for CryptoBot
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from pythonjsonlogger import jsonlogger

class BotLogger:
    """Custom logger for the trading bot."""
    
    def __init__(
        self,
        log_dir: Optional[str] = None,
        log_level: str = "INFO",
        max_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """Initialize logger configuration."""
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create formatters
        json_formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            timestamp=True
        )
        
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create handlers
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        
        # Create rotating file handlers
        trading_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "trading.log",
            maxBytes=max_size,
            backupCount=backup_count
        )
        trading_handler.setFormatter(json_formatter)
        
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "error.log",
            maxBytes=max_size,
            backupCount=backup_count
        )
        error_handler.setFormatter(json_formatter)
        error_handler.setLevel(logging.ERROR)
        
        # Create loggers
        self.trading_logger = logging.getLogger("cryptobot.trading")
        self.trading_logger.setLevel(getattr(logging, log_level))
        self.trading_logger.addHandler(console_handler)
        self.trading_logger.addHandler(trading_handler)
        self.trading_logger.addHandler(error_handler)
        
        self.wallet_logger = logging.getLogger("cryptobot.wallet")
        self.wallet_logger.setLevel(getattr(logging, log_level))
        self.wallet_logger.addHandler(console_handler)
        self.wallet_logger.addHandler(trading_handler)
        self.wallet_logger.addHandler(error_handler)
        
        # Set default logger for direct methods
        self._default_logger = self.trading_logger
    
    def get_trading_logger(self) -> logging.Logger:
        """Get the trading logger."""
        return self.trading_logger
    
    def get_wallet_logger(self) -> logging.Logger:
        """Get the wallet logger."""
        return self.wallet_logger
    
    def debug(self, msg: str, *args, **kwargs):
        """Log a debug message."""
        self._default_logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """Log an info message."""
        self._default_logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Log a warning message."""
        self._default_logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Log an error message."""
        self._default_logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """Log a critical message."""
        self._default_logger.critical(msg, *args, **kwargs)
    
    def archive_logs(self):
        """Archive current logs with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = self.log_dir / "archive" / timestamp
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        for log_file in self.log_dir.glob("*.log"):
            if log_file.stat().st_size > 0:  # Only archive non-empty logs
                new_name = archive_dir / log_file.name
                os.rename(log_file, new_name)
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up log files older than specified days."""
        import time
        
        current_time = time.time()
        archive_dir = self.log_dir / "archive"
        
        if not archive_dir.exists():
            return
            
        for timestamp_dir in archive_dir.iterdir():
            if timestamp_dir.stat().st_mtime < current_time - (days * 86400):
                for log_file in timestamp_dir.glob("*.log"):
                    os.remove(log_file)
                os.rmdir(timestamp_dir)
