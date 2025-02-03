"""
Test Helius RPC Connection
"""

import asyncio
import json
from pathlib import Path
from solana.rpc.async_api import AsyncClient

async def test_connection():
    print("Testing Helius RPC Connection...")
    
    # Load RPC config
    config_path = Path(__file__).parent.parent / "config" / "rpc.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Get primary endpoint
    endpoint = config["primary"]["url"]
    print(f"\nUsing endpoint: {endpoint}")
    
    try:
        # Initialize client
        client = AsyncClient(endpoint)
        
        # Test basic connection
        print("\nTesting basic connection...")
        version = await client.get_version()
        print(f"Solana version: {version}")
        
        # Get recent blockhash
        print("\nGetting recent blockhash...")
        blockhash = await client.get_recent_blockhash()
        print(f"Recent blockhash: {blockhash}")
        
        # Get slot
        print("\nGetting current slot...")
        slot = await client.get_slot()
        print(f"Current slot: {slot}")
        
        # Get block height
        print("\nGetting block height...")
        height = await client.get_block_height()
        print(f"Block height: {height}")
        
        print("\nConnection test successful!")
        return True
        
    except Exception as e:
        print(f"\nError testing connection: {str(e)}")
        return False
    finally:
        await client.close()

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
