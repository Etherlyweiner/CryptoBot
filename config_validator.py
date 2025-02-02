"""Configuration validation and sanity checking for CryptoBot."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, List
import logging
from pathlib import Path
import json
import os

logger = logging.getLogger('ConfigValidator')

@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class ConfigValidator:
    """Validates trading configuration parameters."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def validate_risk_params(self,
                           max_position_size: Decimal,
                           max_total_exposure: Decimal,
                           max_drawdown: Decimal,
                           risk_per_trade: Decimal) -> ValidationResult:
        """Validate risk management parameters."""
        # Check position size limits
        if max_position_size > Decimal('0.2'):
            self.errors.append(
                f"Max position size {float(max_position_size):.1%} exceeds safe limit of 20%"
            )
        elif max_position_size > Decimal('0.1'):
            self.warnings.append(
                f"Max position size {float(max_position_size):.1%} is higher than recommended 10%"
            )
            
        # Check total exposure
        if max_total_exposure > Decimal('0.8'):
            self.errors.append(
                f"Max total exposure {float(max_total_exposure):.1%} exceeds safe limit of 80%"
            )
        elif max_total_exposure > Decimal('0.5'):
            self.warnings.append(
                f"Max total exposure {float(max_total_exposure):.1%} is higher than recommended 50%"
            )
            
        # Check drawdown limit
        if max_drawdown > Decimal('0.2'):
            self.errors.append(
                f"Max drawdown {float(max_drawdown):.1%} exceeds safe limit of 20%"
            )
        elif max_drawdown > Decimal('0.1'):
            self.warnings.append(
                f"Max drawdown {float(max_drawdown):.1%} is higher than recommended 10%"
            )
            
        # Check risk per trade
        if risk_per_trade > Decimal('0.05'):
            self.errors.append(
                f"Risk per trade {float(risk_per_trade):.1%} exceeds safe limit of 5%"
            )
        elif risk_per_trade > Decimal('0.02'):
            self.warnings.append(
                f"Risk per trade {float(risk_per_trade):.1%} is higher than recommended 2%"
            )
            
        return ValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings
        )
        
    def validate_trading_params(self,
                              min_trade_interval: int,
                              max_daily_trades: int,
                              min_win_rate: Decimal,
                              min_profit_factor: Decimal) -> ValidationResult:
        """Validate trading parameters."""
        # Check trade interval
        if min_trade_interval < 60:
            self.errors.append(
                f"Minimum trade interval {min_trade_interval}s is too low, should be at least 60s"
            )
        elif min_trade_interval < 300:
            self.warnings.append(
                f"Minimum trade interval {min_trade_interval}s is lower than recommended 300s"
            )
            
        # Check daily trade limit
        if max_daily_trades > 50:
            self.errors.append(
                f"Maximum daily trades {max_daily_trades} exceeds safe limit of 50"
            )
        elif max_daily_trades > 20:
            self.warnings.append(
                f"Maximum daily trades {max_daily_trades} is higher than recommended 20"
            )
            
        # Check win rate requirement
        if min_win_rate < Decimal('0.4'):
            self.warnings.append(
                f"Minimum win rate {float(min_win_rate):.1%} is lower than recommended 40%"
            )
            
        # Check profit factor requirement
        if min_profit_factor < Decimal('1.5'):
            self.warnings.append(
                f"Minimum profit factor {float(min_profit_factor):.1f} is lower than recommended 1.5"
            )
            
        return ValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings
        )
        
    def validate_path_permissions(self, paths: List[Path]) -> ValidationResult:
        """Validate file system permissions."""
        for path in paths:
            # Check if directory exists or can be created
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.errors.append(f"Cannot create directory {path}: {str(e)}")
                    continue
                    
            # Check write permission
            try:
                test_file = path / '.test_write'
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                self.errors.append(f"No write permission for {path}: {str(e)}")
                
        return ValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings
        )
        
    def validate_system_resources(self,
                                min_memory_mb: int = 1024,
                                min_disk_space_mb: int = 5120) -> ValidationResult:
        """Validate system resources."""
        import psutil
        
        # Check available memory
        available_memory = psutil.virtual_memory().available / (1024 * 1024)  # Convert to MB
        if available_memory < min_memory_mb:
            self.errors.append(
                f"Insufficient memory: {available_memory:.0f}MB < {min_memory_mb}MB required"
            )
            
        # Check disk space
        disk_usage = psutil.disk_usage(os.path.expanduser("~"))
        available_space = disk_usage.free / (1024 * 1024)  # Convert to MB
        if available_space < min_disk_space_mb:
            self.errors.append(
                f"Insufficient disk space: {available_space:.0f}MB < {min_disk_space_mb}MB required"
            )
            
        return ValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings
        )
