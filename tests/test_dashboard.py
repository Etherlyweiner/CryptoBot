"""Tests for the dashboard functionality"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cryptobot.ui.dashboard import Dashboard

@pytest.mark.asyncio
async def test_dashboard_initialization(test_config):
    """Test dashboard initialization"""
    mock_bot = Mock()
    dashboard = Dashboard(mock_bot)
    assert dashboard.bot == mock_bot
    assert isinstance(dashboard.last_update, datetime)

@pytest.mark.asyncio
async def test_statistics_calculation():
    """Test trading statistics calculation"""
    mock_bot = Mock()
    dashboard = Dashboard(mock_bot)
    
    # Test with empty data
    stats = dashboard._calculate_statistics([], [])
    assert stats['daily_pnl'] == 0
    assert stats['win_rate'] == 0
    assert stats['active_positions'] == 0
    assert stats['daily_trades'] == 0
    
    # Test with sample data
    positions = [
        {'token': 'test1', 'size': 1.0, 'entry_price': 100},
        {'token': 'test2', 'size': 2.0, 'entry_price': 200}
    ]
    
    trades = [
        {
            'token': 'test1',
            'pnl': 0.5,
            'exit_time': datetime.now(),
            'entry_time': datetime.now() - timedelta(minutes=30)
        },
        {
            'token': 'test2',
            'pnl': -0.2,
            'exit_time': datetime.now(),
            'entry_time': datetime.now() - timedelta(minutes=45)
        }
    ]
    
    stats = dashboard._calculate_statistics(positions, trades)
    assert stats['active_positions'] == 2
    assert stats['daily_trades'] == 2
    assert stats['daily_pnl'] == 0.3
    assert stats['win_rate'] == 50.0

@pytest.mark.asyncio
async def test_risk_metrics_calculation():
    """Test risk metrics calculation"""
    mock_bot = Mock()
    dashboard = Dashboard(mock_bot)
    
    # Test with empty data
    metrics = dashboard._calculate_risk_metrics([])
    assert metrics['max_drawdown'] == 0
    assert metrics['sharpe_ratio'] == 0
    assert metrics['win_loss_ratio'] == 0
    assert metrics['avg_duration'] == '0m'
    
    # Test with sample data
    trades = [
        {
            'pnl': 1.0,
            'exit_time': datetime.now(),
            'entry_time': datetime.now() - timedelta(minutes=30)
        },
        {
            'pnl': -0.5,
            'exit_time': datetime.now(),
            'entry_time': datetime.now() - timedelta(minutes=45)
        },
        {
            'pnl': 0.8,
            'exit_time': datetime.now(),
            'entry_time': datetime.now() - timedelta(minutes=15)
        }
    ]
    
    metrics = dashboard._calculate_risk_metrics(trades)
    assert metrics['max_drawdown'] > 0
    assert metrics['sharpe_ratio'] != 0
    assert metrics['win_loss_ratio'] > 0
    assert 'm' in metrics['avg_duration']

@pytest.mark.asyncio
async def test_max_drawdown_calculation():
    """Test maximum drawdown calculation"""
    mock_bot = Mock()
    dashboard = Dashboard(mock_bot)
    
    # Test with sample PnL series
    pnl_series = [1.0, 1.5, 1.2, 0.8, 1.1, 1.4]
    max_dd = dashboard._calculate_max_drawdown(pnl_series)
    assert max_dd > 0
    assert max_dd <= 100

@pytest.mark.asyncio
async def test_sharpe_ratio_calculation():
    """Test Sharpe ratio calculation"""
    mock_bot = Mock()
    dashboard = Dashboard(mock_bot)
    
    # Test with sample PnL series
    pnl_series = [0.1, -0.05, 0.15, -0.02, 0.08]
    sharpe = dashboard._calculate_sharpe_ratio(pnl_series)
    assert isinstance(sharpe, float)
    
    # Test with empty series
    assert dashboard._calculate_sharpe_ratio([]) == 0
    
    # Test with zero volatility
    assert dashboard._calculate_sharpe_ratio([1.0, 1.0, 1.0]) == 0
