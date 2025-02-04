"""
Trading Engine for CryptoBot
"""

import asyncio
import logging
from typing import Dict, List, Optional
from .phantom import PhantomWallet
from .market_scanner import MarketScanner
from ..monitoring.logger import BotLogger
from ..config.manager import ConfigurationManager

logger = logging.getLogger(__name__)

class TradingEngine:
    """Main trading engine for executing trades."""
    
    def __init__(self, config: Dict):
        """Initialize trading engine"""
        self.config = config
        self.wallet = None
        self.logger = BotLogger()
        self.market_scanner = MarketScanner()
        self.active_trades = {}
        self.trading_enabled = True
        
    def set_wallet(self, wallet: PhantomWallet):
        """Set the wallet for trading"""
        self.wallet = wallet
        
    async def initialize(self) -> bool:
        """Initialize trading engine components."""
        try:
            # Initialize wallet connection
            if not await self.wallet.initialize():
                self.logger.error("❌ Failed to initialize Phantom Wallet")
                return False
            
            self.logger.info("✅ Trading engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize trading engine: {str(e)}")
            return False
    
    async def scan_market_opportunities(self) -> List[Dict]:
        """Scan for new trading opportunities."""
        try:
            opportunities = await self.market_scanner.analyze_market_opportunities()
            
            if opportunities:
                self.logger.info(f"Found {len(opportunities)} potential trading opportunities")
                for opp in opportunities[:5]:  # Log top 5 opportunities
                    self.logger.info(
                        f"Token: {opp['symbol']} ({opp['name']})\n"
                        f"Score: {opp['score']:.2f}\n"
                        f"Reason: {opp['reason']}"
                    )
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Failed to scan market opportunities: {str(e)}")
            return []
    
    async def analyze_token(self, address: str) -> Dict:
        """Analyze a specific token for trading potential."""
        try:
            metrics = await self.market_scanner.get_token_metrics(address)
            tokens = await self.market_scanner.get_all_tokens()
            
            if address in tokens and metrics:
                token = tokens[address]
                score = self.market_scanner._calculate_opportunity_score(token, metrics)
                
                return {
                    'address': address,
                    'symbol': token['symbol'],
                    'name': token['name'],
                    'score': score,
                    'metrics': metrics,
                    'analysis': self.market_scanner._get_opportunity_reason(token, metrics)
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to analyze token {address}: {str(e)}")
            return {}
    
    async def execute_trade(self, token_address: str, amount: float, is_buy: bool) -> bool:
        """Execute a trade for a specific token."""
        try:
            # Get token information
            token_info = await self.analyze_token(token_address)
            if not token_info:
                self.logger.error(f"Failed to get token information for {token_address}")
                return False
            
            # Check if trade meets criteria
            trading_config = self.config.get_trading_config()
            if amount < trading_config['min_trade_size'] or amount > trading_config['max_trade_size']:
                self.logger.warning(f"Trade size {amount} outside allowed range")
                return False
            
            # Execute trade through Phantom wallet
            # Note: Actual trade execution will depend on Phantom wallet implementation
            trade_type = "BUY" if is_buy else "SELL"
            self.logger.info(
                f"Executing {trade_type} trade:\n"
                f"Token: {token_info['symbol']} ({token_info['name']})\n"
                f"Amount: {amount}\n"
                f"Current Score: {token_info['score']:.2f}"
            )
            
            # Track active trade
            if is_buy:
                self.active_trades[token_address] = {
                    'entry_price': token_info['metrics'].get('price', 0),
                    'amount': amount,
                    'timestamp': asyncio.get_event_loop().time()
                }
            else:
                self.active_trades.pop(token_address, None)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to execute trade: {str(e)}")
            return False
    
    async def monitor_positions(self):
        """Monitor active trading positions."""
        try:
            while self.trading_enabled:
                for token_address, trade in list(self.active_trades.items()):
                    token_info = await self.analyze_token(token_address)
                    if not token_info:
                        continue
                    
                    entry_price = trade['entry_price']
                    current_price = token_info['metrics'].get('price', 0)
                    
                    if current_price <= 0:
                        continue
                    
                    profit_loss = (current_price - entry_price) / entry_price
                    
                    # Check stop loss and take profit
                    trading_config = self.config.get_trading_config()
                    if profit_loss <= -trading_config['stop_loss']:
                        self.logger.warning(
                            f"Stop loss triggered for {token_info['symbol']}\n"
                            f"Loss: {profit_loss:.2%}"
                        )
                        await self.execute_trade(token_address, trade['amount'], False)
                        
                    elif profit_loss >= trading_config['profit_target']:
                        self.logger.info(
                            f"Take profit triggered for {token_info['symbol']}\n"
                            f"Profit: {profit_loss:.2%}"
                        )
                        await self.execute_trade(token_address, trade['amount'], False)
                
                await asyncio.sleep(60)  # Check positions every minute
                
        except Exception as e:
            self.logger.error(f"Error in position monitoring: {str(e)}")
    
    async def run(self):
        """Run the trading engine."""
        try:
            if not await self.initialize():
                return
            
            # Start position monitoring in background
            asyncio.create_task(self.monitor_positions())
            
            while self.trading_enabled:
                # Scan for new opportunities
                opportunities = await self.scan_market_opportunities()
                
                # Filter for high-potential opportunities
                for opp in opportunities:
                    if opp['score'] > 0.8:  # Only trade highest potential tokens
                        trading_config = self.config.get_trading_config()
                        await self.execute_trade(
                            opp['address'],
                            trading_config['position_size'],
                            True
                        )
                
                # Wait before next scan
                await asyncio.sleep(trading_config['cycle_interval'])
                
        except Exception as e:
            self.logger.error(f"Trading engine error: {str(e)}")
            self.trading_enabled = False
