"""
Helius API Configuration Setup
"""

import os
import logging
from pathlib import Path
from getpass import getpass
import json
import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def validate_solana_address(address):
    """Validate Solana wallet address format."""
    logger.info(f"Validating address: {address[:4]}...{address[-4:] if address else ''}")
    if not address:
        logger.error("Address is empty")
        return False
    # Basic format check (should be 32-44 characters)
    if not (32 <= len(address) <= 44):
        logger.error(f"Address length ({len(address)}) is invalid")
        return False
    # Should start with a valid character
    if not address[0].isalnum():
        logger.error("Address starts with invalid character")
        return False
    # Should only contain valid characters
    valid = all(c.isalnum() for c in address)
    if not valid:
        logger.error("Address contains invalid characters")
    return valid

def test_api_key(api_key):
    """Test if the API key is valid."""
    logger.info("Testing API key...")
    url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getVersion",
        "params": []
    }
    
    try:
        logger.info("Sending request to Helius...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info("API key test successful!")
        return True, "API key is valid!"
    except Exception as e:
        logger.error(f"API key test failed: {str(e)}")
        return False, f"Error: {str(e)}"

def setup_helius_config():
    """Setup Helius API configuration."""
    logger.info("Starting Helius API Configuration Setup")
    print("\nHelius API Configuration Setup")
    print("============================")
    
    # Get API key
    print("\nPlease enter your Helius API key:")
    print("(You can find this in your Helius dashboard)")
    
    while True:
        api_key = getpass("\nEnter your Primary API Key: ").strip()
        if not api_key:
            logger.error("Empty API key provided")
            print("API key cannot be empty. Please try again.")
            continue
            
        print("\nTesting API key...")
        success, message = test_api_key(api_key)
        if success:
            logger.info("API key validation successful")
            print("✓", message)
            break
        else:
            logger.error(f"API key validation failed: {message}")
            print("✗", message)
            retry = input("\nWould you like to try again? (y/n): ").lower()
            if retry != 'y':
                logger.info("Setup cancelled by user")
                print("Setup cancelled.")
                return False
    
    # Get wallet address
    print("\nPlease enter your Solana wallet address:")
    print("(This should be your Phantom wallet address)")
    
    while True:
        wallet_address = input("\nEnter your Solana wallet address: ").strip()
        if validate_solana_address(wallet_address):
            logger.info("Wallet address validation successful")
            print("✓ Wallet address format is valid")
            break
        else:
            logger.error("Invalid wallet address format")
            print("✗ Invalid wallet address format")
            retry = input("\nWould you like to try again? (y/n): ").lower()
            if retry != 'y':
                logger.info("Setup cancelled by user")
                print("Setup cancelled.")
                return False
    
    # Create .env file
    logger.info("Creating .env file...")
    env_path = Path(".env")
    env_content = f"""# Helius API Configuration
HELIUS_API_KEY={api_key}
HELIUS_BACKUP_API_KEY={api_key}  # Using same key for backup initially

# Wallet Configuration
WALLET_ADDRESS={wallet_address}

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
    
    try:
        # Save configuration
        with open(env_path, "w") as f:
            f.write(env_content)
        logger.info("Configuration saved successfully")
        
        print("\n✓ Configuration saved successfully!")
        print("\nNext steps:")
        print("1. The bot will now use your Helius API key for RPC connections")
        print("2. Your wallet address is configured for trading")
        print("3. Your API key and wallet are stored securely in the .env file")
        print("4. You can now start the trading bot")
        
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        print(f"\nError saving configuration: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        logger.info("Starting setup script")
        setup_helius_config()
    except Exception as e:
        logger.error(f"Unexpected error in setup script: {str(e)}")
        print(f"\nAn unexpected error occurred: {str(e)}")
