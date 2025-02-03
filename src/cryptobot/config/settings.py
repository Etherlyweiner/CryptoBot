"""
Global configuration settings for CryptoBot
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Global settings configuration."""
    
    def __init__(self):
        """Initialize settings."""
        # Project paths
        self.PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
        self.CONFIG_DIR = self.PROJECT_ROOT / "config"
        self.LOGS_DIR = self.PROJECT_ROOT / "logs"
        
        # Create necessary directories
        self.LOGS_DIR.mkdir(exist_ok=True)
        
        # Network settings
        self.SOLANA_NETWORK = os.getenv("SOLANA_NETWORK", "mainnet")
        self.RPC_TIMEOUT_MS = int(os.getenv("RPC_TIMEOUT_MS", "30000"))
        
        # Trading settings
        self.MAX_TRADE_SIZE_SOL = float(os.getenv("MAX_TRADE_SIZE_SOL", "0.1"))
        self.RISK_LEVEL = os.getenv("RISK_LEVEL", "medium")
        
        # Security settings
        self.ENABLE_2FA = os.getenv("ENABLE_2FA", "true").lower() == "true"
        self.API_REQUEST_TIMEOUT = int(os.getenv("API_REQUEST_TIMEOUT", "45000"))
        
        # Monitoring settings
        self.ENABLE_PERFORMANCE_METRICS = os.getenv("ENABLE_PERFORMANCE_METRICS", "true").lower() == "true"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
        
        # WebSocket settings
        self.USE_WEBSOCKET = os.getenv("USE_WEBSOCKET", "true").lower() == "true"
        self.WEBSOCKET_RECONNECT_DELAY = int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "1000"))
        
        # Notification settings
        self.ENABLE_TELEGRAM = os.getenv("ENABLE_TELEGRAM", "false").lower() == "true"
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # Database settings
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cryptobot.db")
        
        # Cache settings
        self.CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes default
        
        # API Rate limiting
        self.API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "100"))
        self.API_RATE_WINDOW = int(os.getenv("API_RATE_WINDOW", "60"))  # 60 seconds

# Create global settings instance
settings = Settings()
