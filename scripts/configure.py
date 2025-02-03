"""
Configuration script for CryptoBot
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from cryptobot.security.credential_manager import CredentialManager
from cryptobot.network.rpc_manager import RPCManager

def main():
    """Run the configuration process."""
    print("CryptoBot Configuration Wizard")
    print("=============================")
    
    # Initialize credential manager
    cred_manager = CredentialManager()
    
    # Run credential setup
    if not cred_manager.validate_credentials():
        print("\nSetting up credentials...")
        success = cred_manager.setup_wizard()
        if not success:
            print("Error: Credential setup failed!")
            return
    
    # Test RPC connection
    print("\nTesting RPC connection...")
    rpc_manager = RPCManager()
    try:
        import asyncio
        asyncio.run(rpc_manager.initialize())
        print("✓ RPC connection successful!")
    except Exception as e:
        print(f"Error: RPC connection failed: {str(e)}")
        return
    
    print("\nConfiguration complete! Your CryptoBot is ready to trade.")
    print("\nNext steps:")
    print("1. Review your trading configuration in config/trading.json")
    print("2. Start the bot with: python -m cryptobot.app")
    print("3. Monitor the logs in logs/cryptobot.log")

if __name__ == "__main__":
    main()
