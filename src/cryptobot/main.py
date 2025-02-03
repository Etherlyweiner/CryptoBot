"""
CryptoBot - Solana Trading Bot
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
import json
import sys

from config.settings import settings
from security.credential_manager import CredentialManager
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment

# Setup logging
log_file = settings.LOGS_DIR / f"cryptobot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CryptoBot")

class CryptoBot:
    def __init__(self):
        """Initialize the trading bot."""
        self.logger = logger
        self.credential_manager = CredentialManager()
        self.client = None
        self.running = False
        
        # Load RPC configuration
        with open(settings.CONFIG_DIR / "rpc.json") as f:
            self.rpc_config = json.load(f)
    
    async def connect(self):
        """Establish connection to Helius RPC."""
        try:
            endpoint = self.rpc_config["primary"]["url"].replace(
                "${HELIUS_API_KEY}", 
                self.credential_manager.get_credential("HELIUS_API_KEY")
            )
            
            self.logger.info(f"Connecting to Helius RPC...")
            self.client = AsyncClient(
                endpoint,
                commitment=Commitment.CONFIRMED,
                timeout=settings.RPC_TIMEOUT_MS / 1000.0
            )
            
            # Test connection
            version = await self.client.get_version()
            self.logger.info(f"Connected to Solana {version['result']['solana-core']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Helius RPC: {str(e)}")
            return False
    
    async def check_balance(self):
        """Check wallet balance."""
        try:
            wallet = self.credential_manager.get_credential("WALLET_ADDRESS")
            balance = await self.client.get_balance(wallet)
            self.logger.info(f"Wallet balance: {balance['result']['value'] / 1e9:.4f} SOL")
            return balance['result']['value']
        except Exception as e:
            self.logger.error(f"Failed to check balance: {str(e)}")
            return None
    
    async def monitor_market(self):
        """Monitor market conditions."""
        try:
            while self.running:
                # Get recent blockhash as heartbeat
                blockhash = await self.client.get_recent_blockhash()
                self.logger.debug(f"Latest blockhash: {blockhash['result']['value']['blockhash']}")
                
                # Check wallet balance periodically
                await self.check_balance()
                
                # Add your trading strategy logic here
                
                await asyncio.sleep(5)  # Adjust monitoring interval
                
        except Exception as e:
            self.logger.error(f"Error in market monitoring: {str(e)}")
            self.running = False
    
    async def start(self):
        """Start the trading bot."""
        try:
            self.logger.info("Starting CryptoBot...")
            
            # Connect to RPC
            if not await self.connect():
                self.logger.error("Failed to start bot due to connection error")
                return
            
            # Start market monitoring
            self.running = True
            self.logger.info("Bot started successfully")
            await self.monitor_market()
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {str(e)}")
            self.running = False
        finally:
            if self.client:
                await self.client.close()
    
    async def stop(self):
        """Stop the trading bot."""
        self.logger.info("Stopping bot...")
        self.running = False
        if self.client:
            await self.client.close()
        self.logger.info("Bot stopped")

async def main():
    """Main entry point."""
    bot = CryptoBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await bot.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown complete")
