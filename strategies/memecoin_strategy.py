"""Memecoin trading strategy for Solana."""

import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
import numpy as np
from dataclasses import dataclass
import pandas as pd
from datetime import datetime, timedelta

from exchanges.solana import SolanaExchange
from exchanges.jupiter import JupiterDEX

logger = logging.getLogger('MemeStrategy')

@dataclass
class Signal:
    """Trading signal."""
    symbol: str
    action: str  # 'buy' or 'sell'
    confidence: float
    timestamp: datetime
    
@dataclass
class StrategyConfig:
    """Strategy configuration."""
    min_liquidity: Decimal
    max_slippage_bps: int
    min_confidence: float
    position_size: Decimal
    stop_loss_pct: Decimal
    take_profit_pct: Decimal
    cooldown_minutes: int
    
class MemeStrategy:
    """Memecoin trading strategy."""
    
    def __init__(self,
                 exchange: SolanaExchange,
                 dex: JupiterDEX,
                 config: StrategyConfig):
        """Initialize strategy."""
        self.exchange = exchange
        self.dex = dex
        self.config = config
        self.last_trade_time = {}
        self.positions = {}
        
        # Technical indicators
        self.rsi_period = 14
        self.volume_ma_period = 24
        self.price_ma_period = 50
        
    def calculate_rsi(self, prices: pd.Series) -> float:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs.iloc[-1]))
        
    def calculate_volume_profile(self, volumes: pd.Series) -> float:
        """Calculate volume profile strength."""
        current_vol = volumes.iloc[-1]
        avg_vol = volumes.rolling(window=self.volume_ma_period).mean().iloc[-1]
        return current_vol / avg_vol if avg_vol > 0 else 0
        
    def detect_price_momentum(self, prices: pd.Series) -> float:
        """Detect price momentum."""
        ma = prices.rolling(window=self.price_ma_period).mean()
        current_price = prices.iloc[-1]
        
        # Calculate distance from moving average
        distance = (current_price - ma.iloc[-1]) / ma.iloc[-1]
        
        # Calculate rate of change
        roc = (current_price - prices.iloc[-5]) / prices.iloc[-5]
        
        return (distance + roc) / 2
        
    def analyze_social_sentiment(self, token: str) -> float:
        """Analyze social media sentiment."""
        # In a real implementation, this would:
        # 1. Monitor Twitter/Discord for mentions
        # 2. Analyze Reddit activity
        # 3. Check trading volume spikes
        # 4. Monitor influencer activity
        return 0.5
        
    async def get_market_data(self,
                            token: str,
                            timeframe: str = '1h',
                            limit: int = 100) -> Optional[pd.DataFrame]:
        """Get historical market data."""
        try:
            # Get price data from Jupiter
            prices = []
            timestamps = []
            volumes = []
            
            # In reality, we'd fetch this from an API
            # For now, we'll use dummy data
            current_time = datetime.now()
            for i in range(limit):
                time = current_time - timedelta(hours=i)
                timestamps.append(time)
                prices.append(100 + np.random.normal(0, 1))
                volumes.append(1000 + np.random.normal(0, 100))
                
            return pd.DataFrame({
                'timestamp': timestamps,
                'price': prices,
                'volume': volumes
            }).set_index('timestamp').sort_index()
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return None
            
    def validate_liquidity(self, token: str, route: Optional[Dict]) -> bool:
        """Validate if token has sufficient liquidity."""
        if not route:
            return False
            
        # Check if the price impact is acceptable
        price_impact = self.dex.calculate_price_impact(route)
        return price_impact <= float(self.config.max_slippage_bps) / 10000
        
    async def generate_signal(self, token: str) -> Optional[Signal]:
        """Generate trading signal."""
        try:
            # Get market data
            data = await self.get_market_data(token)
            if data is None:
                return None
                
            # Calculate technical indicators
            rsi = self.calculate_rsi(data['price'])
            volume_strength = self.calculate_volume_profile(data['volume'])
            momentum = self.detect_price_momentum(data['price'])
            sentiment = self.analyze_social_sentiment(token)
            
            # Combine signals
            signal_strength = (
                0.3 * (1 - rsi/100)  # RSI (inverted)
                + 0.3 * volume_strength  # Volume
                + 0.2 * momentum  # Price momentum
                + 0.2 * sentiment  # Social sentiment
            )
            
            # Generate signal
            if signal_strength > self.config.min_confidence:
                return Signal(
                    symbol=token,
                    action='buy',
                    confidence=signal_strength,
                    timestamp=datetime.now()
                )
            elif signal_strength < -self.config.min_confidence:
                return Signal(
                    symbol=token,
                    action='sell',
                    confidence=abs(signal_strength),
                    timestamp=datetime.now()
                )
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate signal: {e}")
            return None
            
    def check_cooldown(self, token: str) -> bool:
        """Check if token is in cooldown period."""
        if token not in self.last_trade_time:
            return False
            
        elapsed = datetime.now() - self.last_trade_time[token]
        return elapsed.total_seconds() < self.config.cooldown_minutes * 60
        
    async def execute_signal(self, signal: Signal) -> bool:
        """Execute a trading signal."""
        try:
            if self.check_cooldown(signal.symbol):
                logger.info(f"Signal rejected - {signal.symbol} in cooldown")
                return False
                
            # Get quote
            route = await self.dex.get_price(
                'SOL',  # Base currency
                signal.symbol,
                int(self.config.position_size * 1e9)  # Convert to lamports
            )
            
            if not self.validate_liquidity(signal.symbol, route):
                logger.info(f"Signal rejected - insufficient liquidity for {signal.symbol}")
                return False
                
            # Execute trade
            tx_id = await self.dex.execute_swap(
                self.exchange.wallet,
                'SOL' if signal.action == 'buy' else signal.symbol,
                signal.symbol if signal.action == 'buy' else 'SOL',
                int(self.config.position_size * 1e9)
            )
            
            if tx_id:
                self.last_trade_time[signal.symbol] = datetime.now()
                logger.info(f"Executed {signal.action} signal for {signal.symbol}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to execute signal: {e}")
            return False
            
    async def run(self):
        """Main strategy loop."""
        while True:
            try:
                # Get list of trending tokens
                tokens = await self.dex.get_token_list()
                
                for token in tokens:
                    # Generate and execute signals
                    signal = await self.generate_signal(token['address'])
                    if signal and signal.confidence >= self.config.min_confidence:
                        await self.execute_signal(signal)
                        
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Strategy error: {e}")
                await asyncio.sleep(60)
