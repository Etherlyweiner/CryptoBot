"""Tests for the risk management system"""
import pytest
from datetime import datetime, timedelta
from cryptobot.risk_manager import RiskManager

def test_risk_manager_initialization(test_config):
    """Test risk manager initialization"""
    risk_manager = RiskManager(test_config['risk_management'])
    assert risk_manager.config.max_position_size == 1.0
    assert risk_manager.config.max_daily_loss == 2.0
    assert risk_manager.config.max_trade_count == 10

def test_position_size_calculation(test_config, mock_token_info):
    """Test position size calculation"""
    risk_manager = RiskManager(test_config['risk_management'])
    wallet_balance = 10.0  # 10 SOL
    
    # Calculate position size
    size = risk_manager.calculate_position_size(mock_token_info, wallet_balance)
    
    # Should not exceed max position size
    assert size <= risk_manager.config.max_position_size
    # Should not be zero
    assert size > 0
    # Should be adjusted for volatility
    assert size < wallet_balance

def test_stop_loss_calculation(test_config, mock_token_info):
    """Test stop loss calculation"""
    risk_manager = RiskManager(test_config['risk_management'])
    entry_price = 100.0
    
    stop_loss = risk_manager.calculate_stop_loss(entry_price, mock_token_info)
    
    # Stop loss should be below entry price
    assert stop_loss < entry_price
    # Stop loss should not be more than emergency stop loss
    min_price = entry_price * (1 - risk_manager.config.emergency_stop_loss)
    assert stop_loss >= min_price

def test_take_profit_calculation(test_config):
    """Test take profit calculation"""
    risk_manager = RiskManager(test_config['risk_management'])
    entry_price = 100.0
    stop_loss = 90.0
    
    take_profit = risk_manager.calculate_take_profit(entry_price, stop_loss)
    
    # Take profit should be above entry price
    assert take_profit > entry_price
    # Should maintain at least 2:1 reward:risk ratio
    risk = entry_price - stop_loss
    reward = take_profit - entry_price
    assert reward >= risk * 2

def test_daily_limits(test_config):
    """Test daily trading limits"""
    risk_manager = RiskManager(test_config['risk_management'])
    
    # Simulate trades
    for _ in range(test_config['risk_management']['max_trades_per_day']):
        result = risk_manager.can_open_position({'liquidity_usd': 100000}, 0.1)
        assert result['allowed'] is True
    
    # Next trade should be rejected
    result = risk_manager.can_open_position({'liquidity_usd': 100000}, 0.1)
    assert result['allowed'] is False
    assert 'Daily trade limit' in result['reason']

def test_position_validation(test_config):
    """Test position validation"""
    risk_manager = RiskManager(test_config['risk_management'])
    
    # Test with valid parameters
    assert risk_manager.validate_trade(
        price=100.0,
        liquidity=1000000.0,
        market_cap=10000000.0
    ) is True
    
    # Test with insufficient liquidity
    assert risk_manager.validate_trade(
        price=100.0,
        liquidity=1000.0,
        market_cap=10000000.0
    ) is False

def test_risk_reset_on_new_day(test_config):
    """Test risk stats reset on new day"""
    risk_manager = RiskManager(test_config['risk_management'])
    
    # Set stats for previous day
    risk_manager.daily_stats['date'] = (datetime.now() - timedelta(days=1)).date()
    risk_manager.daily_stats['trade_count'] = 10
    risk_manager.daily_stats['total_loss'] = -1.0
    
    # First trade of new day should be allowed
    result = risk_manager.can_open_position({'liquidity_usd': 100000}, 0.1)
    assert result['allowed'] is True
    assert risk_manager.daily_stats['trade_count'] == 1
