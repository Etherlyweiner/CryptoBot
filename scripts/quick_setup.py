"""
Quick Setup Script for CryptoBot
"""
import os
from pathlib import Path

def main():
    print("Starting CryptoBot Quick Setup...")
    
    # Create .env file
    env_content = """# Helius API Configuration
HELIUS_API_KEY=your_api_key_here
WALLET_ADDRESS=your_wallet_address_here
SOLANA_NETWORK=mainnet
"""
    
    env_path = Path(".env")
    with open(env_path, "w") as f:
        f.write(env_content)
    
    print("\nCreated .env file!")
    print("Please edit the .env file with your actual values.")

if __name__ == "__main__":
    main()
