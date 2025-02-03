"""
Configuration Manager for CryptoBot
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

class ConfigurationManager:
    """Manages configuration settings for CryptoBot."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        load_dotenv()
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
            "ORDER_TIMEOUT": 45,
            "CYCLE_INTERVAL": int(os.getenv('TRADING_CYCLE_INTERVAL', '60')),
            "MAX_SLIPPAGE": float(os.getenv('MAX_SLIPPAGE', '0.01')),
            "MIN_TRADE_SIZE": float(os.getenv('MIN_TRADE_SIZE', '0.1')),
            "MAX_TRADE_SIZE": float(os.getenv('MAX_TRADE_SIZE', '10')),
            "PROFIT_TARGET": float(os.getenv('PROFIT_TARGET', '0.10')),
            "STOP_LOSS": float(os.getenv('STOP_LOSS', '0.05')),
        })
        
        self.network_config = self._load_json("network.json", {
            "SOLANA_NETWORK": os.getenv("SOLANA_NETWORK", "mainnet-beta"),
            "SOLANA_RPC_URL": os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
            "BACKUP_RPC_URLS": [
                "https://solana-mainnet.g.alchemy.com/v2/demo",
                "https://rpc.ankr.com/solana"
            ],
            "PHANTOM_WALLET_ADDRESS": os.getenv("PHANTOM_WALLET_ADDRESS"),
            "PHANTOM_API_KEY": os.getenv("PHANTOM_API_KEY"),
            "RPC_ENDPOINT": os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
        })
        
        self.monitoring_config = self._load_json("monitoring.json", {
            "LOG_LEVEL": "INFO",
            "METRICS_ENABLED": True,
            "ALERT_EMAIL": None,
            "PROMETHEUS_PORT": int(os.getenv('PROMETHEUS_PORT', '8000')),
            "METRICS_PREFIX": os.getenv('METRICS_PREFIX', 'cryptobot'),
        })
        
        self.memecoin_config = self._load_json("memecoin.json", {
            "ENABLE_MEMECOIN_TRADING": True,
            "TRACKED_TOKENS": ["BONK", "WIF", "MYRO"],
            "MAX_ALLOCATION_PER_TOKEN": 0.2,
            "MIN_TOKEN_LIQUIDITY": 100000,
            "ENABLE_TRADING": os.getenv('ENABLE_MEMECOIN_TRADING', 'true').lower() == 'true',
            "TRACKED_TOKENS": os.getenv('TRACKED_TOKENS', 'BONK,WIF,MYRO').split(','),
            "MAX_ALLOCATION_PER_TOKEN": float(os.getenv('MAX_ALLOCATION_PER_TOKEN', '0.2')),
            "MIN_LIQUIDITY": float(os.getenv('MIN_TOKEN_LIQUIDITY', '100000'))
        })
        
        self.prometheus_config = self._load_json("prometheus.json", {
            "PROMETHEUS_PORT": 8000,
            "METRICS_PREFIX": "cryptobot",
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
    
    def update_memecoin_config(self, updates: Dict[str, Any]):
        """Update memecoin configuration."""
        self.memecoin_config.update(updates)
        self._save_json("memecoin.json", self.memecoin_config)
    
    def update_prometheus_config(self, updates: Dict[str, Any]):
        """Update prometheus configuration."""
        self.prometheus_config.update(updates)
        self._save_json("prometheus.json", self.prometheus_config)
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration settings."""
        return {
            "trading": self.trading_config,
            "network": self.network_config,
            "monitoring": self.monitoring_config,
            "memecoin": self.memecoin_config,
            "prometheus": self.prometheus_config
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
        
        if not self.network_config["PHANTOM_WALLET_ADDRESS"]:
            errors.append("Phantom wallet address is required")
        
        if not self.network_config["PHANTOM_API_KEY"]:
            errors.append("Phantom API key is required")
        
        # Validate memecoin config
        if not self.memecoin_config["TRACKED_TOKENS"]:
            errors.append("No tokens configured for tracking")
        
        if self.memecoin_config["MAX_ALLOCATION_PER_TOKEN"] <= 0 or self.memecoin_config["MAX_ALLOCATION_PER_TOKEN"] > 1:
            errors.append("Invalid max allocation per token (should be between 0 and 1)")
        
        return len(errors) == 0, errors
    
    def get_network_config(self) -> Dict[str, Any]:
        """Get network configuration."""
        return self.network_config
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration."""
        return self.trading_config
    
    def get_memecoin_config(self) -> Dict[str, Any]:
        """Get memecoin configuration."""
        return self.memecoin_config
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration."""
        return self.monitoring_config
    
    def get_prometheus_config(self) -> Dict[str, Any]:
        """Get prometheus configuration."""
        return self.prometheus_config
