"""
CryptoBot - Solana Trading Bot
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
import json
import sys
import os
import aiohttp
from typing import Dict, Any

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.cryptobot.config.settings import settings
from src.cryptobot.security.credential_manager import CredentialManager
from src.cryptobot.token_scanner import TokenScanner
from src.cryptobot.sniper_bot import SniperBot
from src.cryptobot.risk_manager import RiskManager
from src.cryptobot.data_exporter import DataExporter
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.publickey import PublicKey

# Setup logging directory
logs_dir = Path(project_root) / "logs"
logs_dir.mkdir(exist_ok=True)

# Setup logging
log_file = logs_dir / f"cryptobot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
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
        
        # Load configuration
        config_dir = Path(project_root) / "config"
        with open(config_dir / "config.json") as f:
            self.config = json.load(f)
            
        # Initialize components
        self.token_scanner = TokenScanner(self.config)
        self.risk_manager = RiskManager(self.config.get('risk_management', {}))
        self.sniper_bot = SniperBot(self.config)
        self.data_exporter = DataExporter(output_dir=str(Path(project_root) / "data"))
        
        # Set up headers for APIs
        self.solscan_headers = {
            "token": self.config["solscan"]["api_key"],
            "Accept": "application/json"
        }
        
        # Initialize caches
        self.validated_tokens = {}
        self.active_trades = {}
        
    async def start(self):
        """Start the trading bot."""
        try:
            self.logger.info("Starting CryptoBot...")
            self.running = True
            
            # Start main components
            await asyncio.gather(
                self._run_token_scanner(),
                self._run_sniper_bot(),
                self._run_trade_monitor()
            )
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {str(e)}")
            raise
            
    async def _run_token_scanner(self):
        """Run token scanner loop"""
        while self.running:
            try:
                new_tokens = await self.token_scanner.scan_new_tokens()
                if new_tokens:
                    self.logger.info(f"Found {len(new_tokens)} new tokens")
                    # Export new tokens to CSV
                    self.data_exporter.export_tokens_to_csv(new_tokens)
                    
                await asyncio.sleep(3)  # Scan every 3 seconds
                
            except Exception as e:
                self.logger.error(f"Error in token scanner: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
                
    async def _run_sniper_bot(self):
        """Run sniper bot loop"""
        while self.running:
            try:
                await self.sniper_bot.start()
            except Exception as e:
                self.logger.error(f"Error in sniper bot: {str(e)}")
                await asyncio.sleep(5)
                
    async def _run_trade_monitor(self):
        """Monitor active trades"""
        while self.running:
            try:
                for token_address, trade in self.active_trades.items():
                    # Update position status
                    position_update = await self.risk_manager.update_position(
                        trade['position_id'],
                        trade['current_price']
                    )
                    
                    if position_update['action'] == 'close':
                        await self._close_position(token_address, position_update['reason'])
                        
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                self.logger.error(f"Error in trade monitor: {str(e)}")
                await asyncio.sleep(5)
                
    async def _close_position(self, token_address: str, reason: str):
        """Close a trading position"""
        try:
            trade = self.active_trades.get(token_address)
            if not trade:
                return
                
            self.logger.info(f"Closing position for {token_address}: {reason}")
            # Implement position closing logic here
            
            # Record trade result
            self.risk_manager.record_trade_result(trade.get('pnl', 0))
            
            # Remove from active trades
            del self.active_trades[token_address]
            
        except Exception as e:
            self.logger.error(f"Error closing position: {str(e)}")
            
    async def stop(self):
        """Stop the trading bot."""
        self.logger.info("Stopping CryptoBot...")
        self.running = False
        
        # Close all positions
        for token_address in list(self.active_trades.keys()):
            await self._close_position(token_address, "Bot shutdown")
            
        # Cleanup
        if self.client:
            await self.client.close()
            
        await self.sniper_bot.close()
        
async def main():
    """Main entry point."""
    bot = CryptoBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        await bot.stop()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        await bot.stop()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
