"""Integration tests for the Solana sniper bot"""
import asyncio
import pytest
import logging
from pathlib import Path
import json
import sys

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.cryptobot.sniper_bot import SniperBot
from src.cryptobot.token_scanner import TokenScanner
from src.cryptobot.risk_manager import RiskManager
from src.cryptobot.data_exporter import DataExporter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def test_config():
    """Create test configuration"""
    return {
        'helius': {
            'api_key': '74d34f4f-e88d-4da1-8178-01ef5749372c',
            'network': 'mainnet-beta',
            'timeout_ms': 30000
        },
        'risk_management': {
            'max_position_size_sol': 0.5,
            'max_daily_loss_sol': 1.0,
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
            'min_volume_24h': 10000,
            'max_slippage_percent': 10,
            'verification_sources': ['dexscreener', 'solscan']
        },
        'dex': {
            'preferred': 'jupiter',
            'backup': 'raydium',
            'max_route_splits': 3
        }
    }

@pytest.fixture
async def sniper_bot(test_config):
    """Create sniper bot instance"""
    async with SniperBot(test_config) as bot:
        yield bot

@pytest.fixture
async def token_scanner(test_config):
    """Create token scanner instance"""
    async with TokenScanner(test_config) as scanner:
        yield scanner

@pytest.fixture
def risk_manager(test_config):
    """Create risk manager instance"""
    return RiskManager(test_config.get('risk_management', {}))

@pytest.fixture
def data_exporter():
    """Create data exporter instance"""
    return DataExporter(output_dir="test_data")

@pytest.mark.asyncio
async def test_token_scanner_new_tokens(token_scanner):
    """Test scanning for new tokens"""
    try:
        new_tokens = await token_scanner.scan_new_tokens()
        assert isinstance(new_tokens, list)
        if new_tokens:
            token = new_tokens[0]
            assert 'address' in token
            assert 'creation_slot' in token
            assert 'owner' in token
    except Exception as e:
        logger.error(f"Error in token scanner test: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_sniper_bot_token_analysis(sniper_bot):
    """Test token analysis functionality"""
    try:
        # Use a known token address for testing
        test_token = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"  # SAMO token
        analysis = await sniper_bot._analyze_token(test_token)
        
        assert isinstance(analysis, dict)
        assert 'should_buy' in analysis
        assert 'market_cap' in analysis
        assert 'liquidity' in analysis
    except Exception as e:
        logger.error(f"Error in sniper bot analysis test: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_risk_manager_position_sizing(risk_manager):
    """Test risk management calculations"""
    try:
        # Test position size calculation
        token_info = {
            'liquidity_usd': 100000,
            'price_change_24h': 5.0,
            'market_cap': 1000000
        }
        wallet_balance = 10.0  # SOL
        
        position_size = risk_manager.get_position_size(token_info, wallet_balance)
        assert isinstance(position_size, float)
        assert position_size > 0
        assert position_size <= wallet_balance
        assert position_size <= risk_manager.config.max_position_size
    except Exception as e:
        logger.error(f"Error in risk manager test: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_data_export(data_exporter):
    """Test data export functionality"""
    try:
        test_tokens = [
            {
                'address': 'token1',
                'market_cap': 1000000,
                'liquidity': 50000,
                'initial_analysis': {
                    'risk_score': 0.8,
                    'holder_count': 500
                }
            },
            {
                'address': 'token2',
                'market_cap': 2000000,
                'liquidity': 100000,
                'initial_analysis': {
                    'risk_score': 0.6,
                    'holder_count': 1000
                }
            }
        ]
        
        data_exporter.export_tokens_to_csv(test_tokens, 'test_export.csv')
        assert Path('test_data/test_export.csv').exists()
        assert Path('test_data/test_export_summary.txt').exists()
    except Exception as e:
        logger.error(f"Error in data export test: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_full_integration(sniper_bot, token_scanner, risk_manager, data_exporter):
    """Test full integration of all components"""
    try:
        # 1. Scan for new tokens
        new_tokens = await token_scanner.scan_new_tokens()
        assert isinstance(new_tokens, list)
        
        # 2. Export token data
        if new_tokens:
            data_exporter.export_tokens_to_csv(new_tokens, 'integration_test.csv')
            assert Path('test_data/integration_test.csv').exists()
        
        # 3. Analyze a token if any found
        if new_tokens:
            token = new_tokens[0]
            analysis = await sniper_bot._analyze_token(token['address'])
            assert isinstance(analysis, dict)
            
            # 4. Test risk management if analysis suggests buying
            if analysis.get('should_buy'):
                position_size = risk_manager.get_position_size(
                    {'liquidity_usd': analysis.get('liquidity', 0)},
                    10.0  # Test wallet balance
                )
                assert isinstance(position_size, float)
                assert position_size >= 0
    except Exception as e:
        logger.error(f"Error in integration test: {str(e)}")
        raise

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
