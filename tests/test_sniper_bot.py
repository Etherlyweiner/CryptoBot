"""Tests for the sniper bot functionality"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from cryptobot.sniper_bot import SniperBot

@pytest.mark.asyncio
async def test_sniper_bot_initialization(test_config):
    """Test sniper bot initialization"""
    async with SniperBot(test_config) as bot:
        assert bot.min_liquidity == test_config['token_validation']['min_liquidity_usd']
        assert bot.min_holders == test_config['token_validation']['min_holders']
        assert bot.min_volume == test_config['token_validation']['min_volume_24h']
        assert bot.headers['Authorization'].startswith('Bearer ')

@pytest.mark.asyncio
async def test_token_info_caching(test_config, mock_token_info):
    """Test token information caching"""
    async with SniperBot(test_config) as bot:
        with patch.object(bot, '_retry_request') as mock_request:
            mock_request.return_value = {'data': mock_token_info}
            
            # First call should make the request
            info1 = await bot.get_token_info('test_token')
            assert info1 == mock_token_info
            mock_request.assert_called_once()
            
            # Second call should use cache
            info2 = await bot.get_token_info('test_token')
            assert info2 == mock_token_info
            assert mock_request.call_count == 1

@pytest.mark.asyncio
async def test_retry_request_with_rate_limit(test_config):
    """Test request retry logic with rate limiting"""
    async with SniperBot(test_config) as bot:
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock rate limit response followed by success
            mock_get.side_effect = [
                Mock(status=429, headers={'Retry-After': '1'}),
                Mock(status=200, json=asyncio.coroutine(lambda: {'data': 'success'}))
            ]
            
            result = await bot._retry_request('test_url')
            assert result == {'data': 'success'}
            assert mock_get.call_count == 2

@pytest.mark.asyncio
async def test_position_monitoring(test_config, mock_token_info):
    """Test position monitoring"""
    async with SniperBot(test_config) as bot:
        with patch.object(bot, 'get_token_info') as mock_get_info:
            mock_get_info.return_value = mock_token_info
            
            # Mock close_position
            bot.close_position = asyncio.coroutine(lambda *args: None)
            
            # Start monitoring in background
            monitor_task = asyncio.create_task(
                bot.monitor_position('test_token', 'test_position', 1.0, 1.0)
            )
            
            # Wait a bit and cancel
            await asyncio.sleep(2)
            monitor_task.cancel()
            
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
            
            # Verify monitoring was active
            assert mock_get_info.call_count > 0

@pytest.mark.asyncio
async def test_error_handling(test_config):
    """Test error handling in requests"""
    async with SniperBot(test_config) as bot:
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Simulate various error conditions
            mock_get.side_effect = Exception('Test error')
            
            result = await bot._retry_request('test_url')
            assert result is None  # Should handle error gracefully

@pytest.mark.asyncio
async def test_position_closing(test_config):
    """Test position closing logic"""
    async with SniperBot(test_config) as bot:
        # Mock necessary methods
        bot._retry_request = asyncio.coroutine(lambda *args, **kwargs: {'success': True})
        
        # Test normal closing
        await bot.close_position('test_token', 'test_position', 'take profit hit')
        
        # Test error handling in closing
        bot._retry_request = asyncio.coroutine(lambda *args, **kwargs: None)
        await bot.close_position('test_token', 'test_position', 'error case')
