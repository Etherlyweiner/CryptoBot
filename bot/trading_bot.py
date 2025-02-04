"""Trading bot implementation."""

import asyncio
import logging
from typing import Dict, Any, Optional
import aiohttp
from .api.helius_client import HeliusClient
from .api.solscan_client import SolscanClient
from .wallet.phantom_integration import PhantomWalletManager

logger = logging.getLogger(__name__)

class TradingBot:
    """Trading bot for monitoring and executing trades on Solana."""
    
    def __init__(self, wallet: PhantomWalletManager, config: Dict[str, Any]):
        """Initialize trading bot.
        
        Args:
            wallet: Initialized wallet manager
            config: Configuration dictionary
        """
        self.wallet = wallet
        self.config = config
        self.session = None
        self.websocket = None
        self.running = False
        self.reconnect_delay = 1  # Initial reconnect delay in seconds
        self.max_reconnect_delay = 60  # Maximum reconnect delay in seconds
        
        # Initialize API clients
        self.helius = HeliusClient(
            api_key=config['api_keys']['helius']['key'],
            rpc_url=config['api_keys']['helius']['rpc_url']
        )
        self.solscan = SolscanClient(
            api_key=config['api_keys']['solscan']['key']
        )
        
    async def start_trading(self):
        """Start the trading bot."""
        try:
            self.running = True
            self.session = aiohttp.ClientSession()
            
            # Initialize connections
            logger.info("Testing API connections...")
            if not await self._test_connections():
                logger.error("API connection tests failed")
                return
                
            logger.info("Validating configuration...")
            if not self._validate_config():
                logger.error("Configuration validation failed")
                return
                
            logger.info("Setting up monitoring...")
            if not await self._setup_monitoring():
                logger.error("Monitoring setup failed")
                return
                
            logger.info("Trading bot initialized successfully")
            
            # Start monitoring mempool
            while self.running:
                try:
                    await self._monitor_mempool()
                except Exception as e:
                    logger.error(f"Mempool monitoring error: {str(e)}", exc_info=True)
                    if self.running:
                        await self._handle_reconnect()
            
        except Exception as e:
            logger.error(f"Error in trading bot: {str(e)}", exc_info=True)
            raise
            
        finally:
            await self.stop_trading()
            
    async def stop_trading(self):
        """Stop the trading bot."""
        logger.info("Stopping trading bot...")
        self.running = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing websocket: {str(e)}")
                
        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                logger.error(f"Error closing session: {str(e)}")
                
        logger.info("Trading bot stopped")
        
    async def _handle_reconnect(self):
        """Handle reconnection with exponential backoff."""
        logger.info(f"Attempting reconnection in {self.reconnect_delay} seconds...")
        await asyncio.sleep(self.reconnect_delay)
        
        # Exponential backoff
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        
    async def _monitor_mempool(self):
        """Monitor mempool for interesting transactions."""
        try:
            async def handle_mempool_update(data: Dict[str, Any]):
                try:
                    logger.debug(f"Received mempool update: {data}")
                    if self._is_interesting_transaction(data):
                        token_address = self._extract_token_address(data)
                        if token_address:
                            await self._analyze_token_opportunity(token_address)
                except Exception as e:
                    logger.error(f"Error handling mempool update: {str(e)}", exc_info=True)
            
            # Reset reconnect delay on successful connection
            self.reconnect_delay = 1
            
            # Start mempool subscription
            logger.info("Starting mempool subscription...")
            await self.helius.subscribe_mempool(handle_mempool_update)
            
        except Exception as e:
            logger.error(f"Error monitoring mempool: {str(e)}", exc_info=True)
            raise
            
    async def _test_connections(self) -> bool:
        """Test all API connections."""
        try:
            # Test Helius connection
            logger.info("Testing Helius API connection...")
            if not await self.helius.test_connection():
                logger.error("Helius connection test failed")
                return False
                
            # Test Solscan connection
            logger.info("Testing Solscan API connection...")
            if not self.solscan.test_connection():
                logger.warning("Solscan connection test failed, continuing anyway...")
                
            return True
            
        except Exception as e:
            logger.error(f"Error testing connections: {str(e)}", exc_info=True)
            return False
            
    def _validate_config(self) -> bool:
        """Validate configuration."""
        try:
            required_keys = [
                'api_keys.helius.key',
                'api_keys.helius.rpc_url',
                'api_keys.solscan.key',
                'trading.max_position_size',
                'trading.stop_loss',
                'trading.take_profit',
                'trading.trailing_stop'
            ]
            
            for key in required_keys:
                parts = key.split('.')
                current = self.config
                for part in parts:
                    if part not in current:
                        logger.error(f"Missing required config key: {key}")
                        return False
                    current = current[part]
                    
            logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Error validating config: {str(e)}", exc_info=True)
            return False
            
    async def _setup_monitoring(self) -> bool:
        """Setup monitoring and alerts."""
        try:
            # Setup prometheus metrics if enabled
            if self.config.get('monitoring', {}).get('enable_prometheus', False):
                logger.info("Setting up Prometheus metrics...")
                # TODO: Initialize prometheus metrics
                pass
                
            # Setup alerts if enabled
            if self.config.get('monitoring', {}).get('enable_alerts', False):
                logger.info("Setting up alerting system...")
                # TODO: Initialize alerting system
                pass
                
            return True
            
        except Exception as e:
            logger.error(f"Error setting up monitoring: {str(e)}", exc_info=True)
            return False
            
    def _is_interesting_transaction(self, tx_data: Dict[str, Any]) -> bool:
        """Check if transaction is interesting for trading."""
        try:
            # Check if we have transaction data
            if not tx_data or not isinstance(tx_data, dict):
                return False
                
            # Log transaction data at debug level
            logger.debug(f"Checking transaction: {tx_data}")
            
            # Look for token program interactions
            if "transaction" in tx_data and "message" in tx_data["transaction"]:
                message = tx_data["transaction"]["message"]
                
                # Check account keys
                if "accountKeys" not in message:
                    return False
                    
                # Look for token program account
                token_program = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                account_keys = [key["pubkey"] for key in message["accountKeys"]]
                if token_program not in account_keys:
                    return False
                    
                # Check instructions
                if "instructions" in message:
                    for ix in message["instructions"]:
                        # Check for token program instructions
                        if ix["programId"] == token_program:
                            # Check for token initialization or large transfers
                            if "data" in ix:
                                data = ix["data"]
                                if data.startswith("3"):  # InitializeMint instruction
                                    logger.info(f"Found token initialization: {tx_data}")
                                    return True
                                elif data.startswith("2"):  # Transfer instruction
                                    # Check transfer amount
                                    try:
                                        amount = int(data[1:], 16)
                                        if amount > 1000000:  # Adjust threshold as needed
                                            logger.info(f"Found large token transfer: {amount} tokens")
                                            return True
                                    except ValueError:
                                        pass
            return False
            
        except Exception as e:
            logger.error(f"Error checking transaction interest: {str(e)}", exc_info=True)
            return False
            
    def _extract_token_address(self, tx_data: Dict[str, Any]) -> Optional[str]:
        """Extract token address from transaction data."""
        try:
            if "transaction" in tx_data and "message" in tx_data["transaction"]:
                message = tx_data["transaction"]["message"]
                
                # Look for token program interactions
                if "accountKeys" in message:
                    for key in message["accountKeys"]:
                        # Check if this is a token mint account
                        if key.get("signer", False) and key.get("writable", False):
                            logger.info(f"Found token address: {key['pubkey']}")
                            return key["pubkey"]
            return None
            
        except Exception as e:
            logger.error(f"Error extracting token address: {str(e)}", exc_info=True)
            return None
            
    async def _analyze_token_opportunity(self, token_address: str):
        """Analyze a token for trading opportunity."""
        try:
            # Get token information from Solscan
            logger.info(f"Analyzing token: {token_address}")
            token_info = self.solscan.get_token_info(token_address)
            
            if token_info:
                logger.info(f"Token analysis for {token_info.symbol} ({token_address}):")
                logger.info(f"Market cap: ${token_info.market_cap:,.2f}")
                logger.info(f"24h volume: ${token_info.volume_24h:,.2f}")
                logger.info(f"Holder count: {token_info.holder_count:,}")
            else:
                logger.warning(f"Could not get token info for {token_address}")
            
        except Exception as e:
            logger.error(f"Error analyzing token opportunity: {str(e)}", exc_info=True)
            
    async def _monitor_positions(self):
        """Monitor active trading positions."""
        # TODO: Implement position monitoring logic
        pass
