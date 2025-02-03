"""
Helius API Configuration Setup
"""

import os
from pathlib import Path
import json
from getpass import getpass
import requests

def test_api_key(api_key):
    """Test if the API key is valid."""
    url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getVersion",
        "params": []
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True, "API key is valid!"
    except Exception as e:
        return False, f"Error: {str(e)}"

def setup_helius_config():
    """Setup Helius API configuration."""
    print("\nHelius API Configuration Setup")
    print("============================")
    
    # Get API keys
    print("\nPlease enter your Helius API keys:")
    print("(You can find these in your Helius dashboard)")
    
    while True:
        api_key = getpass("\nEnter your Primary API Key: ").strip()
        if not api_key:
            print("API key cannot be empty. Please try again.")
            continue
            
        print("\nTesting API key...")
        success, message = test_api_key(api_key)
        if success:
            print("✓", message)
            break
        else:
            print("✗", message)
            retry = input("\nWould you like to try again? (y/n): ").lower()
            if retry != 'y':
                print("Setup cancelled.")
                return False
    
    # Create .env file
    env_path = Path(".env")
    env_content = f"""# Helius API Configuration
HELIUS_API_KEY={api_key}
HELIUS_BACKUP_API_KEY={api_key}  # Using same key for backup initially

# Network Configuration
SOLANA_NETWORK=mainnet
RPC_TIMEOUT_MS=30000

# Trading Parameters
MAX_TRADE_SIZE_SOL=0.1
RISK_LEVEL=medium

# Security Settings
ENABLE_2FA=true
API_REQUEST_TIMEOUT=45000

# Monitoring
ENABLE_PERFORMANCE_METRICS=true
LOG_LEVEL=info

# WebSocket Settings
USE_WEBSOCKET=true
WEBSOCKET_RECONNECT_DELAY=1000
"""
    
    # Save configuration
    with open(env_path, "w") as f:
        f.write(env_content)
    
    print("\n✓ Configuration saved successfully!")
    print("\nNext steps:")
    print("1. The bot will now use your Helius API key for RPC connections")
    print("2. Your API key is stored securely in the .env file")
    print("3. You can now start the trading bot")
    
    return True

if __name__ == "__main__":
    setup_helius_config()
