"""
Script to help set up environment variables for CryptoBot.
"""
import os
import json
import secrets
from pathlib import Path

def read_jwt_secret():
    """Read JWT secret from file."""
    try:
        with open("config/jwt_secret.txt") as f:
            return f.read().strip()
    except FileNotFoundError:
        return secrets.token_hex(32)

def setup_env():
    """Set up environment variables."""
    # Create config directory if it doesn't exist
    Path("config").mkdir(exist_ok=True)
    
    # Base configuration
    config = {
        "SERVER_HOST": "localhost",
        "SERVER_PORT": "8080",
        "METRICS_PORT": "9090",
        "JWT_SECRET": read_jwt_secret(),
        "REDIS_URL": "redis://localhost:6379",
        "LOG_LEVEL": "DEBUG",
        "LOG_FILE": "cryptobot.log",
        # Solana/Phantom specific configuration
        "SOLANA_NETWORK": "mainnet-beta",
        "SOLANA_RPC_URLS": "https://api.mainnet-beta.solana.com,https://solana-api.projectserum.com",  # Multiple RPCs for fallback
        "WALLET_ADDRESS": "8jqv2AKPGYwojLRHQZLokkYdtHycs8HAVGDMqZUvTByB",
        "MAX_POSITIONS": "5",
        "MAX_TRADES_PER_DAY": "10",
        "ORDER_TIMEOUT": "30",
        "POSITION_SIZE_SOL": "0.1",
        "STOP_LOSS_PERCENT": "5",
        "TAKE_PROFIT_PERCENT": "10",
        "MAX_SLIPPAGE_PERCENT": "1",
        "SOLSCAN_API_KEY": "",  # Optional, for enhanced market data
    }
    
    # Write to .env file
    with open(".env", "w") as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    
    print("Environment configuration created successfully!")

if __name__ == "__main__":
    setup_env()
