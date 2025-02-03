"""
Secure Credential Manager for CryptoBot
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
from cryptography.fernet import Fernet
from dotenv import load_dotenv

class CredentialManager:
    """Manages secure storage and retrieval of credentials."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize credential manager."""
        self.config_dir = Path(config_dir) if config_dir else Path("secure_config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_encryption()
        self._load_credentials()
    
    def _initialize_encryption(self):
        """Initialize encryption key."""
        key_file = self.config_dir / ".key"
        if not key_file.exists():
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
        else:
            with open(key_file, "rb") as f:
                key = f.read()
        self.cipher_suite = Fernet(key)
    
    def _load_credentials(self):
        """Load credentials from environment and encrypted storage."""
        # Load from .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
        
        # Initialize credentials dictionary
        self.credentials = {
            "helius": {
                "primary_key": os.getenv("HELIUS_PRIMARY_API_KEY"),
                "backup_key": os.getenv("HELIUS_BACKUP_API_KEY")
            },
            "wallet": {
                "address": os.getenv("PHANTOM_WALLET_ADDRESS")
            },
            "network": {
                "type": os.getenv("SOLANA_NETWORK", "mainnet"),
                "timeout": int(os.getenv("RPC_TIMEOUT_MS", "30000"))
            }
        }
    
    def get_credential(self, key: str) -> str:
        """Get a credential value."""
        parts = key.split(".")
        value = self.credentials
        for part in parts:
            value = value.get(part)
            if value is None:
                return None
        return value
    
    def set_credential(self, key: str, value: str):
        """Set a credential value."""
        parts = key.split(".")
        target = self.credentials
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
        self._save_credentials()
    
    def _save_credentials(self):
        """Save credentials to encrypted storage."""
        # Save non-sensitive config to JSON
        config = {
            "network": self.credentials["network"]
        }
        with open(self.config_dir / "config.json", "w") as f:
            json.dump(config, f, indent=4)
        
        # Save sensitive data to encrypted storage
        sensitive = {
            "helius": self.credentials["helius"],
            "wallet": self.credentials["wallet"]
        }
        encrypted = self.cipher_suite.encrypt(json.dumps(sensitive).encode())
        with open(self.config_dir / ".credentials", "wb") as f:
            f.write(encrypted)
    
    def validate_credentials(self) -> bool:
        """Validate that all required credentials are present."""
        required = [
            "helius.primary_key",
            "helius.backup_key",
            "wallet.address",
            "network.type"
        ]
        
        for key in required:
            if not self.get_credential(key):
                return False
        return True
    
    def setup_wizard(self):
        """Interactive setup wizard for credentials."""
        print("CryptoBot Credential Setup Wizard")
        print("=================================")
        
        # Helius API Keys
        print("\nHelius API Configuration:")
        primary_key = input("Enter your Primary Helius API Key: ").strip()
        backup_key = input("Enter your Backup Helius API Key: ").strip()
        self.set_credential("helius.primary_key", primary_key)
        self.set_credential("helius.backup_key", backup_key)
        
        # Wallet Configuration
        print("\nWallet Configuration:")
        wallet_address = input("Enter your Phantom Wallet Address: ").strip()
        self.set_credential("wallet.address", wallet_address)
        
        # Network Configuration
        print("\nNetwork Configuration:")
        network = input("Enter network type (mainnet/devnet) [mainnet]: ").strip() or "mainnet"
        self.set_credential("network.type", network)
        
        print("\nCredential setup complete!")
        return self.validate_credentials()
