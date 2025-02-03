"""
Interactive Setup Script for CryptoBot
"""
import os
from pathlib import Path
import requests
import sys
from getpass import getpass

def test_helius_key(api_key):
    """Test if the Helius API key is valid."""
    url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getVersion",
        "params": []
    }
    
    try:
        sys.stdout.write("Testing Helius API key...\n")
        sys.stdout.flush()
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        if "result" in result:
            sys.stdout.write("✓ API key is valid!\n")
            sys.stdout.flush()
            return True
    except Exception as e:
        sys.stdout.write(f"✗ API key test failed: {str(e)}\n")
        sys.stdout.flush()
    return False

def validate_wallet(address):
    """Basic validation of Solana wallet address."""
    if not address:
        return False
    if not (32 <= len(address) <= 44):
        return False
    if not address[0].isalnum():
        return False
    return all(c.isalnum() for c in address)

def get_input(prompt, secret=False):
    """Get input from user with proper flushing."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    if secret:
        return getpass("")
    return input()

def main():
    sys.stdout.write("\nCryptoBot Interactive Setup\n")
    sys.stdout.write("=========================\n")
    sys.stdout.flush()
    
    # Get Helius API Key
    while True:
        sys.stdout.write("\nEnter your Helius API key\n")
        sys.stdout.write("(Find this in your Helius dashboard: https://dashboard.helius.dev/)\n")
        sys.stdout.flush()
        
        try:
            api_key = get_input("API Key: ", secret=True)
            
            if test_helius_key(api_key):
                break
            
            retry = get_input("\nWould you like to try again? (y/n): ")
            if retry.lower() != 'y':
                sys.stdout.write("Setup cancelled.\n")
                sys.stdout.flush()
                return
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write("\nSetup cancelled by user.\n")
            sys.stdout.flush()
            return
    
    # Get Wallet Address
    while True:
        sys.stdout.write("\nEnter your Solana wallet address\n")
        sys.stdout.write("(This should be your Phantom wallet address)\n")
        sys.stdout.flush()
        
        try:
            wallet = get_input("Wallet Address: ")
            
            if validate_wallet(wallet):
                sys.stdout.write("✓ Wallet address format is valid\n")
                sys.stdout.flush()
                break
            else:
                sys.stdout.write("✗ Invalid wallet address format\n")
                sys.stdout.flush()
                retry = get_input("\nWould you like to try again? (y/n): ")
                if retry.lower() != 'y':
                    sys.stdout.write("Setup cancelled.\n")
                    sys.stdout.flush()
                    return
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write("\nSetup cancelled by user.\n")
            sys.stdout.flush()
            return
    
    # Create configuration
    env_content = f"""# Helius API Configuration
HELIUS_API_KEY={api_key}
HELIUS_BACKUP_API_KEY={api_key}  # Using same key for backup initially

# Wallet Configuration
WALLET_ADDRESS={wallet}

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
    try:
        env_path = Path(".env")
        with open(env_path, "w") as f:
            f.write(env_content)
        
        sys.stdout.write("\n✓ Configuration saved successfully!\n")
        sys.stdout.write("\nNext steps:\n")
        sys.stdout.write("1. Your Helius API key is configured\n")
        sys.stdout.write("2. Your wallet address is configured\n")
        sys.stdout.write("3. You can now start the trading bot\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"\nError saving configuration: {str(e)}\n")
        sys.stdout.flush()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stdout.write(f"\nAn unexpected error occurred: {str(e)}\n")
        sys.stdout.flush()
