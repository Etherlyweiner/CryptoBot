"""
Validate CryptoBot Configuration
"""

import os
import sys
from pathlib import Path
import asyncio
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def validate_env_variables():
    """Validate environment variables."""
    required_vars = [
        'HELIUS_PRIMARY_API_KEY',
        'HELIUS_BACKUP_API_KEY',
        'PHANTOM_WALLET_ADDRESS',
        'SOLANA_NETWORK'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    return missing

async def test_rpc_connection():
    """Test RPC connection."""
    from cryptobot.network.rpc_manager import RPCManager
    
    rpc = RPCManager()
    try:
        await rpc.initialize()
        return True, "RPC connection successful!"
    except Exception as e:
        return False, f"RPC connection failed: {str(e)}"

def main():
    """Run validation checks."""
    print("CryptoBot Configuration Validator")
    print("================================")
    
    # Load environment variables
    load_dotenv()
    
    # Check environment variables
    print("\nChecking environment variables...")
    missing_vars = validate_env_variables()
    if missing_vars:
        print("[X] Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        return False
    print("[+] All required environment variables are set")
    
    # Test RPC connection
    print("\nTesting RPC connection...")
    success, message = asyncio.run(test_rpc_connection())
    if not success:
        print(f"[X] {message}")
        return False
    print(f"[+] {message}")
    
    print("\nConfiguration validation complete!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
