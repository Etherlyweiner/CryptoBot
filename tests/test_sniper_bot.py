"""Tests for the sniper bot functionality"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from cryptobot.sniper_bot import SniperBot
from cryptobot.monitoring.logger import BotLogger

@pytest.fixture
def test_config():
    """Test configuration"""
    return {
        'helius': {
            'api_key': 'test_api_key',
            'rpc_url': 'https://rpc.helius.xyz/?api-key=test_api_key'
        },
        'birdeye': {
            'api_key': 'test_api_key',
            'base_url': 'https://public-api.birdeye.so'
        },
        'cache_duration': 300,
        'max_retries': 3,
        'retry_delay': 1,
        'rpc_endpoints': ['https://api.mainnet-beta.solana.com'],
        'min_liquidity': 100000,
        'min_market_cap': 1000000,
        'max_position_size': 1.0,
        'take_profit': 0.1,
        'stop_loss': 0.05,
        'trailing_stop': 0.1  # 10% trailing stop
    }

@pytest.fixture
def mock_token_scanner():
    """Create a mock token scanner"""
    scanner = AsyncMock()
    scanner.get_token_info = AsyncMock()
    scanner.__aenter__ = AsyncMock(return_value=scanner)
    scanner.__aexit__ = AsyncMock()
    return scanner

@pytest.mark.asyncio
async def test_sniper_bot_initialization(test_config):
    """Test sniper bot initialization"""
    async with SniperBot(test_config) as bot:
        assert bot.scanner is not None
        assert bot.config is not None

@pytest.mark.asyncio
async def test_token_info_caching(test_config, mock_token_scanner):
    """Test token information caching"""
    mock_info = {
        'price': 100.0,
        'liquidity_usd': 200000,
        'market_cap': 2000000
    }
    
    mock_token_scanner.get_token_info.return_value = mock_info
    
    with patch('cryptobot.sniper_bot.TokenScanner', return_value=mock_token_scanner):
        async with SniperBot(test_config) as bot:
            token_address = "So11111111111111111111111111111111111111112"  # Wrapped SOL
            
            # First call should cache
            info1 = await bot.get_token_info(token_address)
            assert info1 == mock_info
            
            # Second call should use cache
            info2 = await bot.get_token_info(token_address)
            assert info2 == mock_info
            
            # Verify scanner was called only once
            assert mock_token_scanner.get_token_info.call_count == 1

@pytest.mark.asyncio
async def test_position_monitoring(test_config):
    """Test position monitoring"""
    async with SniperBot(test_config) as bot:
        token_address = "So11111111111111111111111111111111111111112"
        entry_price = 100.0
        
        # Test take profit
        current_price = 120.0  # 20% up
        action = await bot.check_position(token_address, entry_price, current_price)
        assert action == 'sell'
        
        # Reset position tracking for next test
        bot.active_positions = {}
        
        # Test stop loss
        current_price = 90.0  # 10% down
        action = await bot.check_position(token_address, entry_price, current_price)
        assert action == 'sell'
        
        # Reset position tracking for next test
        bot.active_positions = {}
        
        # Test hold
        current_price = 102.0  # 2% up
        action = await bot.check_position(token_address, entry_price, current_price)
        assert action == 'hold'
        
        # Reset position tracking for next test
        bot.active_positions = {}
        
        # Test trailing stop sequence
        # First update to set initial price
        current_price = 103.0  # 3% up
        action = await bot.check_position(token_address, entry_price, current_price)
        assert action == 'hold'
        
        # Move price up further
        current_price = 105.0  # 5% up
        action = await bot.check_position(token_address, entry_price, current_price)
        assert action == 'hold'
        
        # Drop price to trigger trailing stop
        current_price = 94.0  # Drop from 105 to 94 (10.5% drop)
        action = await bot.check_position(token_address, entry_price, current_price)
        assert action == 'sell'

@pytest.mark.asyncio
async def test_error_handling(test_config, mock_token_scanner):
    """Test error handling and retries"""
    mock_token_scanner.get_token_info.side_effect = Exception("RPC Error")
    
    with patch('cryptobot.sniper_bot.TokenScanner', return_value=mock_token_scanner):
        async with SniperBot(test_config) as bot:
            token_address = "So11111111111111111111111111111111111111112"
            info = await bot.get_token_info(token_address)
            assert info is None

@pytest.mark.asyncio
async def test_position_validation(test_config, mock_token_scanner):
    """Test position validation"""
    mock_info = {
        'liquidity_usd': 200000,
        'market_cap': 2000000,
        'price': 100.0
    }
    
    mock_token_scanner.get_token_info.return_value = mock_info
    
    with patch('cryptobot.sniper_bot.TokenScanner', return_value=mock_token_scanner):
        async with SniperBot(test_config) as bot:
            token_address = "So11111111111111111111111111111111111111112"
            
            # Test valid position
            is_valid = await bot.validate_position(token_address, 0.1)
            assert is_valid is True
            
            # Test invalid position (insufficient liquidity)
            mock_info['liquidity_usd'] = 50000
            is_valid = await bot.validate_position(token_address, 0.1)
            assert is_valid is False
            
            # Test invalid position (insufficient market cap)
            mock_info['liquidity_usd'] = 200000
            mock_info['market_cap'] = 500000
            is_valid = await bot.validate_position(token_address, 0.1)
            assert is_valid is False
            
            # Test invalid position (position size too large)
            mock_info['market_cap'] = 2000000
            is_valid = await bot.validate_position(token_address, 2.0)
            assert is_valid is False
