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
                "api_key": os.getenv("HELIUS_API_KEY"),
                "backup_key": os.getenv("HELIUS_BACKUP_API_KEY")
            },
            "wallet": {
                "address": os.getenv("WALLET_ADDRESS")
            },
            "network": {
                "type": os.getenv("SOLANA_NETWORK", "mainnet"),
                "rpc_timeout": int(os.getenv("RPC_TIMEOUT_MS", "30000"))
            }
        }
        
        # Load encrypted credentials if they exist
        cred_file = self.config_dir / "credentials.enc"
        if cred_file.exists():
            with open(cred_file, "rb") as f:
                encrypted_data = f.read()
                decrypted_data = self.cipher_suite.decrypt(encrypted_data)
                stored_creds = json.loads(decrypted_data)
                # Update any missing credentials from encrypted storage
                self._update_missing_credentials(stored_creds)
    
    def _update_missing_credentials(self, stored_creds: Dict):
        """Update missing credentials from stored encrypted data."""
        for category, values in stored_creds.items():
            if category not in self.credentials:
                self.credentials[category] = {}
            for key, value in values.items():
                if not self.credentials[category].get(key):
                    self.credentials[category][key] = value
    
    def save_credentials(self):
        """Save credentials to encrypted storage."""
        encrypted_data = self.cipher_suite.encrypt(
            json.dumps(self.credentials).encode()
        )
        with open(self.config_dir / "credentials.enc", "wb") as f:
            f.write(encrypted_data)
    
    def get_credential(self, key: str) -> Optional[str]:
        """Get a credential by key."""
        if key == "HELIUS_API_KEY":
            return self.credentials["helius"]["api_key"]
        elif key == "HELIUS_BACKUP_API_KEY":
            return self.credentials["helius"]["backup_key"]
        elif key == "WALLET_ADDRESS":
            return self.credentials["wallet"]["address"]
        elif key == "SOLANA_NETWORK":
            return self.credentials["network"]["type"]
        return None
    
    def set_credential(self, key: str, value: str):
        """Set a credential value."""
        if key.startswith("HELIUS_"):
            category = "helius"
            subkey = "api_key" if key == "HELIUS_API_KEY" else "backup_key"
        elif key == "WALLET_ADDRESS":
            category = "wallet"
            subkey = "address"
        elif key == "SOLANA_NETWORK":
            category = "network"
            subkey = "type"
        else:
            return
        
        self.credentials[category][subkey] = value
        self.save_credentials()
    
    def validate_credentials(self) -> bool:
        """Validate that all required credentials are present."""
        required = [
            "HELIUS_API_KEY",
            "HELIUS_BACKUP_API_KEY",
            "WALLET_ADDRESS",
            "SOLANA_NETWORK"
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
        self.set_credential("HELIUS_API_KEY", primary_key)
        self.set_credential("HELIUS_BACKUP_API_KEY", backup_key)
        
        # Wallet Configuration
        print("\nWallet Configuration:")
        wallet_address = input("Enter your Phantom Wallet Address: ").strip()
        self.set_credential("WALLET_ADDRESS", wallet_address)
        
        # Network Configuration
        print("\nNetwork Configuration:")
        network = input("Enter network type (mainnet/devnet) [mainnet]: ").strip() or "mainnet"
        self.set_credential("SOLANA_NETWORK", network)
        
        print("\nCredential setup complete!")
        return self.validate_credentials()
