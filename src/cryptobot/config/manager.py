"""
Configuration Manager for CryptoBot
"""

import os
import json
from typing import Any, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

class ConfigurationManager:
    """Manages all configuration settings for the trading bot."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._load_env()
        self._load_configs()
    
    def _load_env(self):
        """Load environment variables."""
        env_path = self.config_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    
    def _load_configs(self):
        """Load all configuration files."""
        self.trading_config = self._load_json("trading.json", {
            "POSITION_SIZE_SOL": 0.1,
            "STOP_LOSS_PERCENT": 5,
            "TAKE_PROFIT_PERCENT": 10,
            "MAX_POSITIONS": 3,
            "MAX_TRADES_PER_DAY": 20,
            "ORDER_TIMEOUT": 45
        })
        
        self.network_config = self._load_json("network.json", {
            "SOLANA_NETWORK": os.getenv("SOLANA_NETWORK", "mainnet-beta"),
            "SOLANA_RPC_URL": os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
            "BACKUP_RPC_URLS": [
                "https://solana-mainnet.g.alchemy.com/v2/demo",
                "https://rpc.ankr.com/solana"
            ]
        })
        
        self.monitoring_config = self._load_json("monitoring.json", {
            "LOG_LEVEL": "INFO",
            "METRICS_ENABLED": True,
            "ALERT_EMAIL": None
        })
    
    def _load_json(self, filename: str, defaults: Dict) -> Dict:
        """Load a JSON configuration file with defaults."""
        try:
            with open(self.config_dir / filename) as f:
                return {**defaults, **json.load(f)}
        except FileNotFoundError:
            self._save_json(filename, defaults)
            return defaults
    
    def _save_json(self, filename: str, data: Dict):
        """Save configuration to JSON file."""
        with open(self.config_dir / filename, 'w') as f:
            json.dump(data, f, indent=4)
    
    def update_trading_config(self, updates: Dict[str, Any]):
        """Update trading configuration."""
        self.trading_config.update(updates)
        self._save_json("trading.json", self.trading_config)
    
    def update_network_config(self, updates: Dict[str, Any]):
        """Update network configuration."""
        self.network_config.update(updates)
        self._save_json("network.json", self.network_config)
    
    def update_monitoring_config(self, updates: Dict[str, Any]):
        """Update monitoring configuration."""
        self.monitoring_config.update(updates)
        self._save_json("monitoring.json", self.monitoring_config)
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration settings."""
        return {
            "trading": self.trading_config,
            "network": self.network_config,
            "monitoring": self.monitoring_config
        }
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate all configuration settings."""
        errors = []
        
        # Validate trading config
        if self.trading_config["POSITION_SIZE_SOL"] <= 0:
            errors.append("Position size must be greater than 0")
        
        if not (0 < self.trading_config["STOP_LOSS_PERCENT"] < 100):
            errors.append("Stop loss must be between 0 and 100")
        
        if not (0 < self.trading_config["TAKE_PROFIT_PERCENT"] < 100):
            errors.append("Take profit must be between 0 and 100")
        
        # Validate network config
        if not self.network_config["SOLANA_RPC_URL"]:
            errors.append("Solana RPC URL is required")
        
        if self.network_config["SOLANA_NETWORK"] not in ["mainnet-beta", "devnet"]:
            errors.append("Invalid Solana network")
        
        return len(errors) == 0, errors
