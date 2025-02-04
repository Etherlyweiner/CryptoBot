"""
Tests for Phantom wallet integration
"""

import pytest
import pytest_asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cryptobot.trading.phantom import PhantomWallet
import os

class TestPhantomIntegration:
    @pytest_asyncio.fixture
    async def wallet(self):
        """Create a test wallet instance."""
        os.environ['PHANTOM_WALLET_ADDRESS'] = 'DummyWalletAddress'
        os.environ['SOLANA_RPC_URL'] = 'https://api.devnet.solana.com'
        
        wallet = PhantomWallet()
        await wallet.initialize()
        yield wallet
        
    @pytest.mark.asyncio
    async def test_initialization(self, wallet):
        """Test wallet initialization."""
        assert wallet is not None
        assert isinstance(wallet, PhantomWallet)
        
    @pytest.mark.asyncio
    async def test_token_accounts(self, wallet):
        """Test getting token accounts."""
        accounts = await wallet.get_token_accounts()
        assert isinstance(accounts, list)
        
    @pytest.mark.asyncio
    async def test_memecoin_balances(self, wallet):
        """Test getting memecoin balances."""
        balances = await wallet.get_memecoin_balances()
        assert isinstance(balances, dict)
        
    @pytest.mark.asyncio
    async def test_memecoin_prices(self, wallet):
        """Test getting memecoin prices."""
        prices = await wallet.get_memecoin_prices()
        assert isinstance(prices, dict)
