import asyncio
import logging
import os
from dotenv import load_dotenv
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('WalletDiagnostic')

async def run_diagnostics():
    """Run wallet connection diagnostics"""
    try:
        # 1. Load and verify environment variables
        load_dotenv()
        logger.info("Checking environment variables...")
        
        required_vars = ['HELIUS_API_KEY', 'NETWORK', 'WALLET_ADDRESS']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return
            
        # 2. Test RPC connection
        helius_key = os.getenv('HELIUS_API_KEY')
        network = os.getenv('NETWORK', 'mainnet-beta')
        rpc_url = f"https://rpc.helius.xyz/?api-key={helius_key}"
        
        logger.info(f"Testing RPC connection to {network}...")
        client = AsyncClient(rpc_url)
        
        try:
            version = await client.get_version()
            logger.info(f"Connected to Solana {version['solana-core']}")
        except Exception as e:
            logger.error(f"RPC connection failed: {str(e)}")
            return
            
        # 3. Check wallet balance
        wallet_address = os.getenv('WALLET_ADDRESS')
        try:
            pubkey = Pubkey.from_string(wallet_address)
            balance = await client.get_balance(pubkey)
            sol_balance = balance.value / 1e9  # Convert lamports to SOL
            logger.info(f"Wallet balance: {sol_balance:.4f} SOL")
        except Exception as e:
            logger.error(f"Failed to get wallet balance: {str(e)}")
            return
            
        # 4. Check recent blockhash
        try:
            blockhash = await client.get_latest_blockhash()
            logger.info("Successfully retrieved latest blockhash")
        except Exception as e:
            logger.error(f"Failed to get latest blockhash: {str(e)}")
            
    except Exception as e:
        logger.error(f"Diagnostic failed: {str(e)}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
