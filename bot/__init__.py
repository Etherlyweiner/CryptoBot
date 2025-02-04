"""Bot package initialization."""

from .trading_bot import TradingBot
from .wallet.phantom_integration import PhantomWalletManager
from .api.helius_client import HeliusClient
from .api.solscan_client import SolscanClient
from .api.token_program_client import TokenProgramClient

__all__ = [
    'TradingBot',
    'PhantomWalletManager',
    'HeliusClient',
    'SolscanClient',
    'TokenProgramClient'
]
