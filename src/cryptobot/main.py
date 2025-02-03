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
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.publickey import PublicKey

# Setup logging directory
logs_dir = Path(project_root) / "logs"
logs_dir.mkdir(exist_ok=True)

# Setup logging
log_file = logs_dir / f"cryptobot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
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
        config_dir = Path(project_root) / "config"
        with open(config_dir / "config.json") as f:
            self.config = json.load(f)
        
        # Set up headers for Solscan API
        self.solscan_headers = {
            "token": self.config["solscan"]["api_key"],
            "Accept": "application/json"
        }
        
        # Initialize token validation cache with timestamp
        self.validated_tokens = {}
        
    def _is_cache_valid(self, token_address: str) -> bool:
        """Check if cached validation result is still valid."""
        if token_address not in self.validated_tokens:
            return False
            
        cache_duration = self.config["token_validation"]["cache_duration_minutes"]
        cache_entry = self.validated_tokens[token_address]
        cache_age = (datetime.now() - cache_entry["timestamp"]).total_seconds() / 60
        
        return cache_age < cache_duration
    
    async def validate_token(self, token_address: str) -> bool:
        """
        Validate a token by checking multiple sources based on configuration.
        Returns True if token meets all validation criteria.
        """
        try:
            self.logger.info(f"Validating token: {token_address}")
            
            # Check cache first
            if self._is_cache_valid(token_address):
                return self.validated_tokens[token_address]["is_valid"]
            
            # Check if token is blacklisted
            if token_address in self.config["token_validation"]["blacklisted_tokens"]:
                self.logger.warning(f"Token is blacklisted: {token_address}")
                return False
            
            validation_count = 0
            token_data = {}
            
            # 1. Check Solscan if configured
            if "solscan" in self.config["token_validation"]["verification_sources"]:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://api.solscan.io/v2/token/{token_address}",
                            headers=self.solscan_headers
                        ) as response:
                            if response.status == 200:
                                solscan_data = await response.json()
                                if solscan_data.get('success'):
                                    token_data['solscan'] = solscan_data
                                    checks = self.config["token_validation"]["verification_checks"]["solscan"]
                                    
                                    # Verify token meets Solscan criteria
                                    token_info = solscan_data.get('data', {})
                                    if (not checks["require_verified"] or token_info.get('verified')) and \
                                       (token_info.get('holder_count', 0) >= checks["min_holder_count"]):
                                        validation_count += 1
                                        self.logger.info(f"Token passed Solscan validation: {token_address}")
                except Exception as e:
                    self.logger.error(f"Solscan validation error: {str(e)}")
            
            # 2. Check DexScreener if configured
            if "dexscreener" in self.config["token_validation"]["verification_sources"]:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                        ) as response:
                            if response.status == 200:
                                dex_data = await response.json()
                                if dex_data.get('pairs'):
                                    token_data['dexscreener'] = dex_data
                                    checks = self.config["token_validation"]["verification_checks"]["dexscreener"]
                                    
                                    # Check if any pair meets the criteria
                                    for pair in dex_data['pairs']:
                                        liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                                        volume = float(pair.get('volume', {}).get('h24', 0))
                                        price_impact = float(pair.get('priceChange', {}).get('h24', 0))
                                        
                                        if liquidity >= checks["min_liquidity_usd"] and \
                                           volume >= checks["min_daily_volume"] and \
                                           abs(price_impact) <= checks["max_price_impact"]:
                                            validation_count += 1
                                            self.logger.info(f"Token passed DexScreener validation: {token_address}")
                                            break
                except Exception as e:
                    self.logger.error(f"DexScreener validation error: {str(e)}")
            
            # Determine if token is valid based on required verifications
            is_valid = validation_count >= self.config["token_validation"]["required_verifications"]
            
            # Cache the result with timestamp
            self.validated_tokens[token_address] = {
                "is_valid": is_valid,
                "timestamp": datetime.now(),
                "data": token_data
            }
            
            if is_valid:
                self.logger.info(f"Token validated successfully: {token_address}")
            else:
                self.logger.warning(f"Token validation failed: {token_address}")
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Token validation error: {str(e)}")
            self.logger.exception("Full validation error:")
            return False
    
    async def connect(self):
        """Establish connection to Helius RPC."""
        try:
            self.logger.info("Starting Helius RPC connection...")
            endpoint = f"https://mainnet.helius-rpc.com/?api-key={self.config['helius']['api_key']}"
            
            self.logger.info(f"Creating AsyncClient...")
            self.client = AsyncClient(
                endpoint,
                commitment=Confirmed,
                timeout=self.config["helius"]["timeout_ms"] / 1000.0
            )
            
            # Test connection
            self.logger.info("Testing connection with get_version...")
            version = await self.client.get_version()
            self.logger.info(f"Connected to Solana node, version: {version}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Helius RPC: {str(e)}")
            self.logger.exception("Full connection error:")
            return False
    
    async def check_balance(self):
        """Check wallet balance using both RPC and Solscan."""
        try:
            self.logger.info("Starting balance check...")
            wallet_address = self.config["wallet"]["address"]
            self.logger.info(f"Checking balance for wallet: {wallet_address}")
            
            if self.client is None:
                self.logger.error("Client is None, connection not established")
                return None
            
            try:
                # Convert string address to PublicKey
                wallet = PublicKey(wallet_address)
                self.logger.info(f"Wallet PublicKey created: {wallet}")
                
                # Get balance from RPC
                self.logger.info("Requesting balance from RPC...")
                balance = await self.client.get_balance(wallet)
                if not balance.value:
                    self.logger.error("RPC returned no balance value")
                    return None
                    
                lamports = balance.value
                self.logger.info(f"Raw balance received: {lamports} lamports")
                
                # Get additional data from Solscan
                try:
                    self.logger.info("Requesting data from Solscan...")
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://api.solscan.io/v2/account/{wallet_address}",
                            headers=self.solscan_headers
                        ) as response:
                            if response.status == 200:
                                solscan_data = await response.json()
                                self.logger.info("Solscan data retrieved successfully")
                                self.logger.info(f"Solscan response: {solscan_data}")
                except Exception as solscan_error:
                    self.logger.error(f"Solscan API error: {str(solscan_error)}")
                    # Continue even if Solscan fails
                
                sol_balance = lamports / 1e9
                self.logger.info(f"Final calculated balance: {sol_balance:.4f} SOL")
                return lamports
                
            except ValueError as ve:
                self.logger.error(f"Invalid wallet address format: {str(ve)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to check balance: {str(e)}")
            self.logger.exception("Full balance check error:")
            return None
    
    async def start(self):
        """Start the trading bot."""
        try:
            self.logger.info("Starting CryptoBot...")
            
            # Initialize wallet connection
            await self.connect()
            
            # Start monitoring
            self.running = True
            while self.running:
                try:
                    # Check wallet balance
                    balance = await self.client.get_balance(self._public_key)
                    if balance is None:
                        self.logger.error("Failed to get wallet balance")
                        continue
                        
                    sol_balance = balance.value / 1e9
                    self.logger.info(f"Current wallet balance: {sol_balance:.4f} SOL")
                    
                    # Look for trading opportunities
                    for token_address in self.config.get("watchlist", []):
                        try:
                            # Validate token first
                            if not await self.validate_token(token_address):
                                self.logger.warning(f"Token validation failed: {token_address}")
                                continue
                                
                            # Check token price and liquidity
                            token_data = await self.get_token_data(token_address)
                            if not token_data:
                                continue
                                
                            # Apply trading strategy
                            if await self.should_trade(token_data):
                                await self.execute_trade(token_address, token_data)
                                
                        except Exception as e:
                            self.logger.error(f"Error processing token {token_address}: {str(e)}")
                            continue
                            
                    # Wait before next iteration
                    await asyncio.sleep(self.config.get("scan_interval", 60))
                    
                except asyncio.CancelledError:
                    self.logger.info("Bot execution cancelled")
                    break
                    
                except Exception as e:
                    self.logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except Exception as e:
            self.logger.error(f"Critical error in bot execution: {str(e)}")
            self.logger.exception("Full error trace:")
            raise
            
        finally:
            self.running = False
            await self.cleanup()
            
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.client:
                await self.client.close()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            
    async def should_trade(self, token_data: Dict[str, Any]) -> bool:
        """Determine if we should trade based on token data and strategy."""
        try:
            # Get trading parameters from config
            min_liquidity = self.config["token_validation"]["min_liquidity_usd"]
            min_volume = self.config["token_validation"]["min_daily_volume_usd"]
            max_price_impact = self.config["token_validation"]["verification_checks"]["dexscreener"]["max_price_impact"]
            
            # Check liquidity
            if token_data.get("liquidity", 0) < min_liquidity:
                self.logger.info(f"Insufficient liquidity: ${token_data.get('liquidity', 0):,.2f} < ${min_liquidity:,.2f}")
                return False
                
            # Check volume
            if token_data.get("volume_24h", 0) < min_volume:
                self.logger.info(f"Insufficient 24h volume: ${token_data.get('volume_24h', 0):,.2f} < ${min_volume:,.2f}")
                return False
                
            # Check price impact
            price_impact = abs(float(token_data.get("price_change_24h", 0)))
            if price_impact > max_price_impact:
                self.logger.info(f"Price impact too high: {price_impact:.1f}% > {max_price_impact:.1f}%")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error in trade decision: {str(e)}")
            return False
            
    async def execute_trade(self, token_address: str, token_data: Dict[str, Any]):
        """Execute a trade based on strategy and market conditions."""
        try:
            # Get trading parameters
            max_trade_size = self.config["trading"]["max_trade_size_sol"]
            stop_loss = self.config["trading"]["stop_loss_percentage"]
            max_slippage = self.config["trading"]["max_slippage_percent"]
            
            # Calculate trade size based on wallet balance
            balance = await self.get_balance()
            trade_size = min(balance * 0.1, max_trade_size)  # Use 10% of balance or max_trade_size
            
            if trade_size < 0.01:  # Minimum trade size of 0.01 SOL
                self.logger.info("Trade size too small")
                return
                
            # Execute the trade
            result = await self.trading_engine.execute_trade(
                input_token="So11111111111111111111111111111111111111112",  # SOL
                output_token=token_address,
                amount=trade_size,
                is_buy=True
            )
            
            if result.success:
                self.logger.info(f"Trade executed successfully: {result.transaction_id}")
                # Record trade in database
                await self.record_trade(result)
            else:
                self.logger.error(f"Trade failed: {result.error}")
                
        except Exception as e:
            self.logger.error(f"Error executing trade: {str(e)}")
            self.logger.exception("Full trade error:")
            
    async def get_token_data(self, token_address: str) -> Dict[str, Any]:
        """Get token data from Solscan API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.solscan.io/v2/token/{token_address}",
                    headers=self.solscan_headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', {})
        except Exception as e:
            self.logger.error(f"Error getting token data: {str(e)}")
            return {}
            
    async def get_balance(self) -> float:
        """Get wallet balance."""
        try:
            wallet_address = self.config["wallet"]["address"]
            balance = await self.client.get_balance(PublicKey(wallet_address))
            return balance.value / 1e9
        except Exception as e:
            self.logger.error(f"Error getting balance: {str(e)}")
            return 0.0
            
    async def record_trade(self, result: Dict[str, Any]):
        """Record trade in database."""
        try:
            # Implement trade recording logic here
            pass
        except Exception as e:
            self.logger.error(f"Error recording trade: {str(e)}")
            
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
