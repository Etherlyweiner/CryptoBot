import logging
import requests
import json
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_wallet():
    try:
        logger.info("Checking wallet balance...")
        
        def check_wallet_balance():
            """Check wallet balance using multiple RPC endpoints."""
            WALLET_ADDRESS = "8jqv2AKPGYwojLRHQZLokkYdtHycs8HAVGDMqZUvTByB"
            RPC_ENDPOINTS = [
                "https://api.mainnet-beta.solana.com",
                "https://solana-mainnet.g.alchemy.com/v2/demo",
                "https://rpc.ankr.com/solana"
            ]
            
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [
                    WALLET_ADDRESS,
                    {"commitment": "confirmed"}
                ]
            }
            
            for endpoint in RPC_ENDPOINTS:
                try:
                    logger.info(f"Trying RPC endpoint: {endpoint}")
                    response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "result" in data and "value" in data["result"]:
                            balance = float(data["result"]["value"]) / 10**9
                            logger.info(f"Wallet balance: {balance} SOL")
                            
                            if balance <= 0:
                                logger.warning("Wallet has zero balance. Please fund the wallet before proceeding.")
                            elif balance < 0.1:
                                logger.warning(f"Wallet balance ({balance} SOL) is below minimum required (0.1 SOL)")
                            else:
                                logger.info("Wallet has sufficient balance")
                            
                            return balance
                    
                    logger.warning(f"Failed to get balance from {endpoint}")
                    
                except Exception as e:
                    logger.error(f"Error with endpoint {endpoint}: {str(e)}")
                    continue
            
            logger.error("Failed to get balance from all endpoints")
            return 0.0
        
        balance = check_wallet_balance()
        
    except Exception as e:
        logger.error(f"Error checking wallet: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_wallet())
