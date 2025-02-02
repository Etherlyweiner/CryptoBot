"""
Configuration management for CryptoBot
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cryptobot.log')
    ]
)
logger = logging.getLogger(__name__)

class Config:
    """Configuration class for the CryptoBot"""
    
    def __init__(self):
        """Initialize configuration"""
        try:
            # Get current working directory
            cwd = os.getcwd()
            logger.info(f"Initializing configuration in: {cwd}")
            
            # Load environment variables from .env file
            env_path = Path('.env').absolute()
            logger.info(f"Loading configuration from: {env_path}")
            
            if not env_path.exists():
                raise FileNotFoundError(f"Configuration file not found at {env_path}")
            
            # Load the .env file
            load_dotenv(dotenv_path=str(env_path), override=True, encoding='utf-8')
            
            # Network configuration
            self.NETWORK = os.getenv('NETWORK', 'mainnet-beta')  # mainnet-beta, testnet, or devnet
            
            # RPC configuration
            self.RPC_URL = os.getenv('RPC_URL', 'https://api.mainnet-beta.solana.com')
            self.RPC_TIMEOUT = int(os.getenv('RPC_TIMEOUT', '30'))
            
            # Trading configuration
            self.MAX_TRADES = int(os.getenv('MAX_TRADES', '5'))
            self.POSITION_SIZE = float(os.getenv('POSITION_SIZE', '0.1'))
            self.STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '2'))
            self.TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', '4'))
            
            # Technical analysis parameters
            self.RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
            self.RSI_OVERBOUGHT = float(os.getenv('RSI_OVERBOUGHT', '70'))
            self.RSI_OVERSOLD = float(os.getenv('RSI_OVERSOLD', '30'))
            self.EMA_FAST = int(os.getenv('EMA_FAST', '12'))
            self.EMA_SLOW = int(os.getenv('EMA_SLOW', '26'))
            self.MACD_SIGNAL = int(os.getenv('MACD_SIGNAL', '9'))
            
            # Risk management parameters
            self.MAX_DRAWDOWN = float(os.getenv('MAX_DRAWDOWN', '10'))
            self.DAILY_LOSS_LIMIT = float(os.getenv('DAILY_LOSS_LIMIT', '5'))
            self.MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '20'))
            
            # Solana-specific settings
            self.COMMITMENT_LEVEL = os.getenv('COMMITMENT_LEVEL', 'confirmed')
            self.TRANSACTION_TIMEOUT = int(os.getenv('TRANSACTION_TIMEOUT', '60'))
            self.MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
            self.RETRY_DELAY = int(os.getenv('RETRY_DELAY', '1'))
            
            # Jupiter DEX settings
            self.JUPITER_QUOTE_API = os.getenv('JUPITER_QUOTE_API', 'https://quote-api.jup.ag/v4')
            self.SLIPPAGE_BPS = int(os.getenv('SLIPPAGE_BPS', '50'))  # 0.5%
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error initializing configuration: {str(e)}")
            raise
    
    def validate(self) -> bool:
        """Validate the configuration"""
        try:
            # Validate network
            valid_networks = ['mainnet-beta', 'testnet', 'devnet']
            if self.NETWORK not in valid_networks:
                raise ValueError(f"Invalid network: {self.NETWORK}")
            
            # Validate trading parameters
            if not (0 < self.POSITION_SIZE <= 100):
                raise ValueError(f"Invalid POSITION_SIZE: {self.POSITION_SIZE}")
            
            if not (0 < self.STOP_LOSS_PERCENT <= 100):
                raise ValueError(f"Invalid STOP_LOSS_PERCENT: {self.STOP_LOSS_PERCENT}")
            
            if not (0 < self.TAKE_PROFIT_PERCENT <= 100):
                raise ValueError(f"Invalid TAKE_PROFIT_PERCENT: {self.TAKE_PROFIT_PERCENT}")
            
            # Validate technical analysis parameters
            if not (0 < self.RSI_PERIOD <= 50):
                raise ValueError(f"Invalid RSI_PERIOD: {self.RSI_PERIOD}")
            
            if not (50 < self.RSI_OVERBOUGHT <= 100):
                raise ValueError(f"Invalid RSI_OVERBOUGHT: {self.RSI_OVERBOUGHT}")
            
            if not (0 <= self.RSI_OVERSOLD <= 50):
                raise ValueError(f"Invalid RSI_OVERSOLD: {self.RSI_OVERSOLD}")
            
            # Validate risk parameters
            if not (0 < self.MAX_DRAWDOWN <= 100):
                raise ValueError(f"Invalid MAX_DRAWDOWN: {self.MAX_DRAWDOWN}")
            
            if not (0 < self.DAILY_LOSS_LIMIT <= 100):
                raise ValueError(f"Invalid DAILY_LOSS_LIMIT: {self.DAILY_LOSS_LIMIT}")
            
            logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False

# Create global config instance
config = Config()

# Validate configuration
if not config.validate():
    raise ValueError("Configuration validation failed")
