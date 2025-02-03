"""
Apply and validate CryptoBot configuration
"""

import json
import os
from pathlib import Path
import requests
import shutil
import sys

def test_helius_key(api_key):
    """Test if the Helius API key is valid."""
    print(f"Testing Helius API key...")
    
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
        print("[OK] API key is valid!")
        return True
    except Exception as e:
        print(f"[ERROR] API key test failed: {str(e)}")
        return False

def validate_wallet(address):
    """Basic validation of Solana wallet address."""
    if not address or not isinstance(address, str):
        print("[ERROR] Wallet address is empty or invalid type")
        return False
    
    # Allow for longer addresses that might include additional encoding
    if len(address) < 32:
        print(f"[ERROR] Wallet address too short: {len(address)} chars (min 32)")
        return False
    
    if not address[0].isalnum():
        print("[ERROR] Wallet address must start with alphanumeric character")
        return False
    
    if not all(c.isalnum() for c in address):
        print("[ERROR] Wallet address contains invalid characters")
        return False
    
    return True

def main():
    print("\nCryptoBot Configuration Validator")
    print("===============================")
    
    config_dir = Path("config")
    template_path = config_dir / "config.template.json"
    config_path = config_dir / "config.json"
    
    # Check if config exists, if not copy template
    if not config_path.exists():
        if not template_path.exists():
            print("Error: config.template.json not found!")
            return False
        
        print("\nNo configuration found. Creating from template...")
        shutil.copy(template_path, config_path)
        print("Created config.json from template.")
        print("Please edit config.json with your settings and run this script again.")
        return True
    
    # Load configuration
    try:
        with open(config_path) as f:
            config = json.load(f)
        
        # Validate Helius API key
        api_key = config.get("helius", {}).get("api_key")
        if api_key == "YOUR_HELIUS_API_KEY_HERE":
            print("\nError: Please set your Helius API key in config.json")
            return False
        
        if not test_helius_key(api_key):
            return False
        
        # Validate wallet address
        wallet = config.get("wallet", {}).get("address")
        if wallet == "YOUR_PHANTOM_WALLET_ADDRESS_HERE":
            print("\nError: Please set your wallet address in config.json")
            return False
        
        if not validate_wallet(wallet):
            return False
        print("[OK] Wallet address format is valid")
        
        # Create .env file
        env_content = f"""# Helius API Configuration
HELIUS_API_KEY={api_key}
HELIUS_BACKUP_API_KEY={api_key}  # Using same key for backup initially

# Wallet Configuration
WALLET_ADDRESS={wallet}

# Network Configuration
SOLANA_NETWORK={config.get("helius", {}).get("network", "mainnet")}
RPC_TIMEOUT_MS={config.get("helius", {}).get("timeout_ms", 30000)}

# Trading Parameters
MAX_TRADE_SIZE_SOL={config.get("trading", {}).get("max_trade_size_sol", 0.1)}
RISK_LEVEL={config.get("trading", {}).get("risk_level", "medium")}

# Security Settings
ENABLE_2FA=true
API_REQUEST_TIMEOUT=45000

# Monitoring
ENABLE_PERFORMANCE_METRICS={str(config.get("monitoring", {}).get("enable_performance_metrics", True)).lower()}
LOG_LEVEL={config.get("monitoring", {}).get("log_level", "info")}

# WebSocket Settings
USE_WEBSOCKET={str(config.get("websocket", {}).get("enabled", True)).lower()}
WEBSOCKET_RECONNECT_DELAY={config.get("websocket", {}).get("reconnect_delay_ms", 1000)}
"""
        
        # Save .env file
        with open(".env", "w") as f:
            f.write(env_content)
        
        print("\n[OK] Configuration validated and applied successfully!")
        print("\nNext steps:")
        print("1. Your Helius API key is configured")
        print("2. Your wallet address is configured")
        print("3. You can now start the trading bot")
        return True
        
    except json.JSONDecodeError:
        print("\nError: Invalid JSON in config.json")
        return False
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
