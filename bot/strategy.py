"""Trading strategy implementation."""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .price_monitor import PriceMonitor

logger = logging.getLogger(__name__)

class TradingStrategy:
    """Trading strategy implementation."""
    
    def __init__(self, price_monitor: PriceMonitor, config: Dict):
        """Initialize trading strategy.
        
        Args:
            price_monitor: Price monitor instance
            config: Strategy configuration
        """
        self.price_monitor = price_monitor
        self.config = config
        
        # Load strategy settings
        self.min_price_change = Decimal(str(config.get('min_price_change', '5.0')))  # Min price change %
        self.max_slippage = Decimal(str(config.get('max_slippage', '1.0')))  # Max slippage %
        self.min_liquidity = Decimal(str(config.get('min_liquidity', '1000.0')))  # Min liquidity in SOL
        self.max_position_size = Decimal(str(config.get('max_position_size', '1.0')))  # Max position size in SOL
        self.stop_loss = Decimal(str(config.get('stop_loss', '5.0')))  # Stop loss %
        self.take_profit = Decimal(str(config.get('take_profit', '10.0')))  # Take profit %
        
    def find_trading_opportunities(self) -> List[Dict]:
        """Find trading opportunities based on price movements.
        
        Returns:
            List of trading opportunities
        """
        opportunities = []
        prices = self.price_monitor.get_all_prices()
        
        for token_address, price_data in prices.items():
            # Check for significant price changes
            price_change = Decimal(str(price_data['priceChange']))
            if abs(price_change) >= self.min_price_change:
                opportunities.append({
                    'token': token_address,
                    'price': price_data['price'],
                    'priceChange': float(price_change),
                    'type': 'buy' if price_change < 0 else 'sell',
                    'score': self._calculate_opportunity_score(price_data)
                })
                
        # Sort opportunities by score
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        return opportunities
        
    def _calculate_opportunity_score(self, price_data: Dict) -> float:
        """Calculate opportunity score based on various factors.
        
        Args:
            price_data: Price data for the token
            
        Returns:
            Opportunity score (0-100)
        """
        try:
            # Basic score based on price change
            price_change = abs(Decimal(str(price_data['priceChange'])))
            base_score = float(min(price_change / self.min_price_change * 50, 50))
            
            # Add momentum factor
            momentum = price_data.get('priceChangeMomentum', 0)
            momentum_score = min(abs(momentum) * 10, 25)
            
            # Add volume factor
            volume = price_data.get('volume24h', 0)
            volume_score = min(volume / float(self.min_liquidity) * 25, 25)
            
            return base_score + momentum_score + volume_score
            
        except Exception as e:
            logger.error(f"Error calculating opportunity score: {str(e)}")
            return 0
            
    def calculate_position_size(self, opportunity: Dict, available_balance: Decimal) -> Decimal:
        """Calculate position size for a trade.
        
        Args:
            opportunity: Trading opportunity
            available_balance: Available balance in SOL
            
        Returns:
            Position size in SOL
        """
        try:
            # Base position size on available balance
            base_size = min(available_balance * Decimal('0.1'), self.max_position_size)
            
            # Adjust based on opportunity score
            score_factor = Decimal(str(opportunity['score'])) / Decimal('100')
            position_size = base_size * score_factor
            
            # Ensure minimum trade size
            min_trade = Decimal('0.1')  # 0.1 SOL
            if position_size < min_trade:
                return Decimal('0')
                
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return Decimal('0')
            
    def should_close_position(self, entry_price: Decimal, current_price: Decimal, position_type: str) -> Tuple[bool, str]:
        """Check if position should be closed.
        
        Args:
            entry_price: Entry price
            current_price: Current price
            position_type: Position type ('long' or 'short')
            
        Returns:
            (should_close, reason)
        """
        try:
            price_change = ((current_price - entry_price) / entry_price) * Decimal('100')
            
            if position_type == 'long':
                # Check stop loss
                if price_change <= -self.stop_loss:
                    return True, 'stop_loss'
                    
                # Check take profit
                if price_change >= self.take_profit:
                    return True, 'take_profit'
                    
            elif position_type == 'short':
                # Check stop loss
                if price_change >= self.stop_loss:
                    return True, 'stop_loss'
                    
                # Check take profit
                if price_change <= -self.take_profit:
                    return True, 'take_profit'
                    
            return False, ''
            
        except Exception as e:
            logger.error(f"Error checking position closure: {str(e)}")
            return False, ''
