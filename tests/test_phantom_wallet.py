import pytest
import pytest_asyncio
from bot.wallet.phantom_integration import PhantomWalletManager
from solders.keypair import Keypair
import win32cred

class TestPhantomIntegration:
    @pytest_asyncio.fixture
    async def wallet_manager(self):
        manager = PhantomWalletManager()
        test_keypair = Keypair.from_secret_key(b'\x00' * 32)  # Initialize with a valid secret key
        await manager.initialize_wallet(bytes(test_keypair))
        yield manager
        await manager.close()

    @pytest.mark.asyncio
    async def test_keypair_loading(self, wallet_manager):
        await wallet_manager.ensure_initialized()
        assert wallet_manager.keypair is not None

    @pytest.mark.asyncio
    async def test_keypair_storage(self, wallet_manager):
        cred = win32cred.CredRead('PhantomBotKey', win32cred.CRED_TYPE_GENERIC)
        stored_bytes = bytes(cred.CredentialBlob)
        assert stored_bytes == bytes(wallet_manager.keypair)

    @pytest.mark.asyncio
    async def test_balance_check(self, wallet_manager):
        balance = await wallet_manager.get_balance()
        assert isinstance(balance, float)
        assert balance >= 0.0

    @pytest.mark.asyncio
    async def test_connection_management(self, wallet_manager):
        await wallet_manager.close()
        assert wallet_manager.client.is_closed()
        await wallet_manager.connect()
        assert not wallet_manager.client.is_closed()
