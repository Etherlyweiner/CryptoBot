"""Test configuration and fixtures"""
import pytest
import asyncio
import json
from pathlib import Path
from typing import Dict

@pytest.fixture
def test_config() -> Dict:
    """Load test configuration"""
    return {
        'birdeye': {
            'api_key': 'test_api_key',
            'base_url': 'https://public-api.birdeye.so'
        },
        'risk_management': {
            'max_position_size_sol': 1.0,
            'max_daily_loss_sol': 2.0,
            'max_trades_per_day': 10,
            'min_liquidity_usd': 50000,
            'max_slippage_percent': 10,
            'emergency_stop_loss': 20,
            'profit_lock_threshold': 50,
            'trailing_stop_percent': 10
        },
        'token_validation': {
            'min_liquidity_usd': 50000,
            'min_holders': 100,
            'min_volume_24h': 10000
        }
    }

@pytest.fixture
def mock_token_info() -> Dict:
    """Mock token information"""
    return {
        'price': 1.0,
        'liquidity_usd': 100000,
        'volume_24h': 50000,
        'holders': 500,
        'market_cap': 1000000,
        'volatility_24h': 0.5,
        'atr_24h': 0.1
    }

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()
