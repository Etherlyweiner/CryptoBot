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
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "cryptobot.log"
    }
    
    # Create .env file
    env_content = []
    for key, value in config.items():
        env_content.append(f"{key}={value}")
    
    # Add placeholders for sensitive data
    env_content.extend([
        "# Alert Configuration",
        "SMTP_SERVER=smtp.example.com",
        "SMTP_PORT=587",
        "ALERT_EMAIL=your_email@example.com",
        "ALERT_EMAIL_PASSWORD=your_email_password",
        "SLACK_WEBHOOK=your_slack_webhook_url",
        "TELEGRAM_BOT_TOKEN=your_telegram_bot_token",
        "TELEGRAM_CHAT_ID=your_telegram_chat_id",
        "",
        "# Solana Configuration",
        "SOLANA_RPC_URL=your_solana_rpc_url",
        "WALLET_PRIVATE_KEY=your_wallet_private_key"
    ])
    
    # Write to .env file
    with open(".env", "w") as f:
        f.write("\n".join(env_content))
    
    print("Created .env file with default configuration.")
    print("Please update sensitive values in .env with your actual credentials.")

if __name__ == "__main__":
    setup_env()
