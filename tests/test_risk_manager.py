"""Unit tests for risk management system"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cryptobot.risk_manager import RiskManager

@pytest.fixture
def test_config():
    return {
        'max_position_size_sol': 0.5,
        'max_daily_loss_sol': 1.0,
        'max_trades_per_day': 10,
        'min_liquidity_usd': 50000,
        'max_slippage_percent': 10,
        'emergency_stop_loss': 20,
        'profit_lock_threshold': 50,
        'trailing_stop_percent': 10
    }

@pytest.fixture
def mock_token_info():
    return {
        'liquidity_usd': 100000,
        'volatility_24h': 0.5,
        'atr_24h': 0.1,
        'price_change_24h': 5.0
    }

def test_risk_manager_initialization(test_config):
    """Test risk manager initialization"""
    risk_manager = RiskManager(test_config)
    assert risk_manager.config.max_position_size == 0.5
    assert risk_manager.config.max_daily_loss == 1.0
    assert risk_manager.config.max_trade_count == 10
    assert risk_manager.config.min_liquidity_usd == 50000
    assert risk_manager.config.max_slippage == 0.1
    assert risk_manager.config.emergency_stop_loss == 0.2
    assert risk_manager.config.profit_lock_threshold == 0.5
    assert risk_manager.config.trailing_stop_distance == 0.1

def test_can_open_position(test_config, mock_token_info):
    """Test position opening validation"""
    risk_manager = RiskManager(test_config)
    
    # Test valid position
    result = risk_manager.can_open_position(mock_token_info, 0.1)
    assert result['allowed'] is True
    
    # Test position too large
    result = risk_manager.can_open_position(mock_token_info, 1.0)
    assert result['allowed'] is False
    assert 'Position size' in result['reason']
    
    # Test insufficient liquidity
    low_liquidity = mock_token_info.copy()
    low_liquidity['liquidity_usd'] = 10000
    result = risk_manager.can_open_position(low_liquidity, 0.1)
    assert result['allowed'] is False
    assert 'liquidity' in result['reason'].lower()

def test_position_size_calculation(test_config, mock_token_info):
    """Test position size calculation"""
    risk_manager = RiskManager(test_config)
    wallet_balance = 10.0  # 10 SOL
    
    size = risk_manager.calculate_position_size(mock_token_info, wallet_balance)
    assert size <= risk_manager.config.max_position_size
    assert size > 0
    
    # Test with high volatility
    high_vol_token = mock_token_info.copy()
    high_vol_token['volatility_24h'] = 0.8
    high_vol_size = risk_manager.calculate_position_size(high_vol_token, wallet_balance)
    assert high_vol_size < size  # Higher volatility should reduce position size

def test_stop_loss_calculation(test_config, mock_token_info):
    """Test stop loss calculation"""
    risk_manager = RiskManager(test_config)
    entry_price = 100.0
    
    stop_loss = risk_manager.calculate_stop_loss(entry_price, mock_token_info)
    
    # Stop loss should be below entry price
    assert stop_loss < entry_price
    # Stop loss should not be more than emergency stop loss
    min_price = entry_price * (1 - risk_manager.config.emergency_stop_loss)
    assert stop_loss >= min_price

def test_take_profit_calculation(test_config):
    """Test take profit calculation"""
    risk_manager = RiskManager(test_config)
    entry_price = 100.0
    stop_loss = 90.0
    
    take_profit = risk_manager.calculate_take_profit(entry_price, stop_loss)
    
    # Take profit should be above entry price
    assert take_profit > entry_price
    # Take profit should maintain at least 2:1 reward:risk ratio
    risk = entry_price - stop_loss
    reward = take_profit - entry_price
    assert reward >= risk * 2

def test_daily_limits(test_config):
    """Test daily trading limits"""
    risk_manager = RiskManager(test_config)
    
    # Simulate trades
    for _ in range(test_config['max_trades_per_day']):
        result = risk_manager.can_open_position({'liquidity_usd': 100000}, 0.1)
        assert result['allowed'] is True
        risk_manager.record_trade_result(-0.05)  # Small loss each trade
    
    # Next trade should be rejected due to trade count
    result = risk_manager.can_open_position({'liquidity_usd': 100000}, 0.1)
    assert result['allowed'] is False
    assert 'trade limit' in result['reason'].lower()

def test_risk_reset_on_new_day(test_config):
    """Test risk stats reset on new day"""
    risk_manager = RiskManager(test_config)
    
    # Set stats for previous day
    risk_manager.daily_stats['date'] = (datetime.now() - timedelta(days=1)).date()
    risk_manager.daily_stats['trade_count'] = 10
    risk_manager.daily_stats['total_loss'] = -1.0
    
    # First trade of new day should be allowed
    result = risk_manager.can_open_position({'liquidity_usd': 100000}, 0.1)
    assert result['allowed'] is True
    assert risk_manager.daily_stats['trade_count'] == 0
    assert risk_manager.daily_stats['total_loss'] == 0.0
