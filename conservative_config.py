from decimal import Decimal
from risk_management import RiskManager
from trading_execution import TradingExecutor

def create_conservative_executor(initial_capital: Decimal) -> TradingExecutor:
    """
    Create a conservative trading executor focused on capital preservation
    and consistent profits.
    
    Key features:
    1. Small position sizes (max 5% per position)
    2. Limited total exposure (max 15% of capital)
    3. Tight stop losses (1.5x ATR)
    4. Aggressive take profits (2.5x ATR)
    5. High win rate requirement (50%)
    6. Low correlation threshold (0.5)
    7. Limited daily trades (3 max)
    8. Minimal slippage tolerance (0.05%)
    9. Risk per trade limited to 1%
    10. Maximum drawdown of 10%
    11. Volatility range: 1-5%
    12. Minimum liquidity: $1M daily volume
    13. Minimum trade interval: 5 minutes
    """
    risk_manager = RiskManager(
        initial_capital=initial_capital,
        # Conservative position sizing
        max_position_size=Decimal('0.05'),     # 5% max per position
        max_total_exposure=Decimal('0.15'),    # 15% max total exposure
        max_drawdown=Decimal('0.10'),          # 10% max drawdown
        risk_per_trade=Decimal('0.01'),        # 1% risk per trade
        
        # Technical indicators
        atr_period=14,                         # Standard ATR period
        stop_loss_atr_multiplier=Decimal('1.5'),  # Tighter stop loss
        take_profit_atr_multiplier=Decimal('2.5'), # Higher profit target
        
        # Trade frequency limits
        max_daily_trades=3,                    # Max 3 trades per day
        min_trade_interval=300,                # 5 minutes between trades
        
        # Quality filters
        min_win_rate=Decimal('0.5'),           # Minimum 50% win rate
        correlation_threshold=Decimal('0.5'),   # Lower correlation tolerance
        max_slippage=Decimal('0.0005'),        # 0.05% max slippage
        min_volatility=Decimal('0.01'),        # 1% minimum volatility
        max_volatility=Decimal('0.05'),        # 5% maximum volatility
        min_liquidity=Decimal('1000000')       # $1M minimum daily volume
    )
    
    executor = TradingExecutor(
        risk_manager=risk_manager,
        min_order_interval=300,                # 5 minutes between orders
        max_retries=5                          # More retries for better fills
    )
    
    return executor

# Example usage
if __name__ == '__main__':
    # Create executor with 10,000 initial capital
    executor = create_conservative_executor(Decimal('10000'))
    
    # Example of executing a trade signal
    symbol = 'BTC/USD'
    signal_type = 'long'
    price = Decimal('40000')
    confidence = Decimal('0.9')  # High confidence signal
    
    order_id = executor.execute_trade_signal(
        symbol=symbol,
        signal_type=signal_type,
        price=price,
        confidence=confidence
    )
    
    if order_id:
        print(f"Order placed successfully: {order_id}")
    else:
        print("Order not placed - risk checks failed")
