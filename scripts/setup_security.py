"""
Script to help set up security configuration for CryptoBot.
"""
import os
import json
from pathlib import Path

def setup_security():
    """Set up security configuration."""
    # Create config directory if it doesn't exist
    Path("config").mkdir(exist_ok=True)
    
    # Base security configuration
    security_config = {
        "jwt_secret": os.getenv("JWT_SECRET", "REPLACE_WITH_SECURE_SECRET"),
        "jwt_expiry": 3600,
        "rate_limits": {
            "default": {
                "requests_per_second": 5,
                "burst_size": 10
            },
            "/api/trade": {
                "requests_per_second": 2,
                "burst_size": 5
            },
            "/api/market": {
                "requests_per_second": 10,
                "burst_size": 20
            }
        },
        "allowed_ips": [],
        "blocked_ips": [],
        "api_keys": {},
        "input_validation": {
            "trade": {
                "token_address": {
                    "type": "str",
                    "required": True,
                    "pattern": "^0x[a-fA-F0-9]{40}$"
                },
                "amount": {
                    "type": "float",
                    "required": True,
                    "min": 0
                },
                "price": {
                    "type": "float",
                    "required": True,
                    "min": 0
                },
                "type": {
                    "type": "str",
                    "required": True,
                    "pattern": "^(buy|sell)$"
                }
            }
        }
    }
    
    # Write security configuration
    with open("config/security.json", "w") as f:
        json.dump(security_config, f, indent=4)
    
    print("Created security.json with default configuration.")
    print("Please update any sensitive values as needed.")

if __name__ == "__main__":
    setup_security()
