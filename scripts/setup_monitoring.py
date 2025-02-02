"""
Script to help set up monitoring configuration for CryptoBot.
"""
import os
import json
from pathlib import Path

def setup_monitoring():
    """Set up monitoring configuration."""
    # Create config directory if it doesn't exist
    Path("config").mkdir(exist_ok=True)
    
    # Base monitoring configuration
    monitoring_config = {
        "alert_thresholds": {
            "error_rate": 0.1,
            "response_time": 2.0,
            "memory_usage": 0.9
        },
        "email_settings": {
            "smtp_server": os.getenv("SMTP_SERVER", "REPLACE_WITH_SMTP_SERVER"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "sender_email": os.getenv("ALERT_EMAIL", "REPLACE_WITH_EMAIL"),
            "sender_password": os.getenv("ALERT_EMAIL_PASSWORD", "REPLACE_WITH_PASSWORD")
        },
        "slack_webhook": os.getenv("SLACK_WEBHOOK", "REPLACE_WITH_WEBHOOK_URL"),
        "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN", "REPLACE_WITH_BOT_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", "REPLACE_WITH_CHAT_ID"),
        "log_levels": {
            "trade_execution": "INFO",
            "market_data": "INFO",
            "authentication": "WARNING",
            "system": "WARNING"
        },
        "metrics_collection": {
            "trade_metrics": True,
            "system_metrics": True,
            "ml_metrics": True,
            "cache_metrics": True
        },
        "alert_rules": {
            "high_error_rate": {
                "threshold": 0.2,
                "window": 300,
                "severity": "critical"
            },
            "slow_response": {
                "threshold": 5.0,
                "window": 60,
                "severity": "warning"
            },
            "memory_usage": {
                "threshold": 0.9,
                "window": 60,
                "severity": "warning"
            },
            "failed_trades": {
                "threshold": 3,
                "window": 300,
                "severity": "error"
            }
        }
    }
    
    # Write monitoring configuration
    with open("config/monitoring.json", "w") as f:
        json.dump(monitoring_config, f, indent=4)
    
    print("Created monitoring.json with default configuration.")
    print("Please update any sensitive values as needed.")

if __name__ == "__main__":
    setup_monitoring()
