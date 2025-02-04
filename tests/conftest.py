"""Test configuration and fixtures"""
import pytest
import asyncio
import json
from pathlib import Path
from typing import Dict
from unittest.mock import AsyncMock, Mock

@pytest.fixture
def test_config() -> Dict:
    """Load test configuration"""
    return {
        'birdeye': {
            'api_key': 'test_api_key',
            'base_url': 'https://public-api.birdeye.so'
        },
        'risk_management': {
            'max_position_size': 1.0,
            'max_daily_loss': 2.0,
            'max_trades_per_day': 10,
            'min_liquidity': 50000,
            'max_slippage': 0.01,
            'emergency_stop_loss': 0.20,
            'profit_lock_threshold': 0.50,
            'trailing_stop': 0.10
        },
        'token_validation': {
            'min_liquidity_usd': 50000,
            'min_holders': 100,
            'min_volume_24h': 10000
        },
        'rpc_endpoints': [
            'https://api.mainnet-beta.solana.com'
        ],
        'cache_duration': 300,
        'max_retries': 3,
        'retry_delay': 1
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
        'atr_24h': 0.1,
        'address': 'test_token',
        'timestamp': asyncio.get_event_loop().time()
    }

@pytest.fixture
def mock_wallet():
    """Mock wallet for testing"""
    wallet = Mock()
    wallet.address = 'test_wallet_address'
    wallet.get_balance = AsyncMock(return_value=10.0)
    wallet.sign_transaction = AsyncMock(return_value='signed_transaction')
    wallet.send_transaction = AsyncMock(return_value='tx_signature')
    return wallet

@pytest.fixture
def mock_rpc_client():
    """Mock RPC client for testing"""
    client = AsyncMock()
    client.get_token_accounts_by_owner = AsyncMock(return_value={
        'result': {
            'value': [
                {
                    'pubkey': 'test_token_account',
                    'account': {
                        'data': {
                            'parsed': {
                                'info': {
                                    'tokenAmount': {
                                        'amount': '1000000000',
                                        'decimals': 9,
                                        'uiAmount': 1.0
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }
    })
    return client

@pytest.fixture(scope='function')
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
