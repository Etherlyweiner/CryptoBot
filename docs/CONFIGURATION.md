# CryptoBot Configuration Guide

## Overview

This guide covers the configuration options and best practices for setting up and customizing your CryptoBot installation.

## Configuration Files

### 1. Environment Configuration (.env)

```env
# RPC Configuration
HELIUS_RPC=https://mainnet.helius-rpc.com
HELIUS_KEY=your_helius_api_key
QUICKNODE_RPC=your_quicknode_endpoint
QUICKNODE_KEY=your_quicknode_api_key

# API Configuration
JUPITER_API=https://quote-api.jup.ag/v6
BIRDEYE_API=https://public-api.birdeye.so/public

# Security Settings
WHITELISTED_IPS=127.0.0.1,your_ip_address
MAX_REQUESTS_PER_MINUTE=60
KEY_ROTATION_DAYS=30

# Trading Parameters
MAX_POSITION_SIZE=1000  # in USD
DAILY_LOSS_LIMIT=100    # in USD
MAX_TRADES_PER_DAY=10
```

### 2. Trading Strategy Configuration (config.js)

```javascript
{
  "strategies": {
    "momentum": {
      "enabled": true,
      "timeframe": "5m",
      "indicators": {
        "rsi": {
          "period": 14,
          "overbought": 70,
          "oversold": 30
        },
        "ema": {
          "fast": 12,
          "slow": 26
        }
      },
      "filters": {
        "volume_24h": 100000,
        "price_min": 0.1,
        "market_cap": 1000000
      }
    },
    "meanReversion": {
      "enabled": true,
      "timeframe": "15m",
      "indicators": {
        "bollinger": {
          "period": 20,
          "stdDev": 2
        }
      },
      "filters": {
        "volume_24h": 100000,
        "price_min": 0.1,
        "market_cap": 1000000
      }
    }
  }
}
```

### 3. Risk Management Configuration (risk.js)

```javascript
{
  "risk": {
    "position_sizing": {
      "max_position_size": 1000,      // USD
      "max_portfolio_size": 10000,    // USD
      "position_sizing_model": "fixed" // fixed, kelly, dynamic
    },
    "stop_loss": {
      "enabled": true,
      "type": "trailing",             // fixed, trailing
      "initial_percentage": 5,        // %
      "trailing_percentage": 2        // %
    },
    "take_profit": {
      "enabled": true,
      "type": "fixed",               // fixed, trailing
      "percentage": 10               // %
    },
    "exposure_limits": {
      "max_trades_per_day": 10,
      "max_concurrent_trades": 3,
      "max_exposure_per_token": 20,  // % of portfolio
      "max_daily_drawdown": 5        // %
    },
    "correlation": {
      "max_correlation": 0.7,
      "lookback_period": "30d"
    }
  }
}
```

### 4. Network Configuration (network.js)

```javascript
{
  "network": {
    "primary_rpc": {
      "url": "https://mainnet.helius-rpc.com",
      "weight": 1
    },
    "backup_rpcs": [
      {
        "url": "https://your-quicknode-endpoint",
        "weight": 0.5
      },
      {
        "url": "https://your-alchemy-endpoint",
        "weight": 0.3
      }
    ],
    "health_check": {
      "interval": 30000,           // ms
      "timeout": 5000,            // ms
      "threshold": 3              // failures before failover
    },
    "retry": {
      "max_attempts": 3,
      "backoff": {
        "initial": 1000,          // ms
        "max": 10000,            // ms
        "factor": 2
      }
    }
  }
}
```

### 5. Wallet Security Configuration (wallet.js)

```javascript
{
  "wallet": {
    "type": "hardware",              // hardware, software
    "auto_disconnect": {
      "enabled": true,
      "timeout": 3600               // seconds
    },
    "transaction_signing": {
      "max_retries": 3,
      "timeout": 30000,            // ms
      "confirmation_blocks": 2
    },
    "whitelist": {
      "enabled": true,
      "addresses": [
        "your_whitelisted_address_1",
        "your_whitelisted_address_2"
      ]
    }
  }
}
```

## Configuration Categories

### 1. Trading Parameters

#### Position Sizing
- `MAX_POSITION_SIZE`: Maximum size of any single position
- `MAX_PORTFOLIO_SIZE`: Maximum total portfolio exposure
- `POSITION_SIZING_MODEL`: Algorithm for calculating position sizes

#### Risk Limits
- `DAILY_LOSS_LIMIT`: Maximum allowed loss per day
- `MAX_TRADES_PER_DAY`: Maximum number of trades per day
- `MAX_CONCURRENT_TRADES`: Maximum number of open positions

#### Stop Loss/Take Profit
- `STOP_LOSS_TYPE`: Fixed or trailing stop loss
- `STOP_LOSS_PERCENTAGE`: Initial stop loss percentage
- `TAKE_PROFIT_TYPE`: Fixed or trailing take profit
- `TAKE_PROFIT_PERCENTAGE`: Take profit percentage

### 2. Network Configuration

#### RPC Settings
- `PRIMARY_RPC`: Primary RPC endpoint
- `BACKUP_RPCS`: List of backup RPC endpoints
- `HEALTH_CHECK_INTERVAL`: Frequency of health checks

#### API Configuration
- `JUPITER_API`: Jupiter API endpoint
- `BIRDEYE_API`: Birdeye API endpoint
- `API_TIMEOUT`: API request timeout

### 3. Security Settings

#### Access Control
- `WHITELISTED_IPS`: List of allowed IP addresses
- `MAX_REQUESTS_PER_MINUTE`: Rate limiting
- `KEY_ROTATION_DAYS`: API key rotation interval

#### Wallet Security
- `WALLET_TYPE`: Hardware or software wallet
- `AUTO_DISCONNECT`: Automatic wallet disconnection
- `TRANSACTION_TIMEOUT`: Transaction signing timeout

### 4. Performance Monitoring

#### Metrics
- `PERFORMANCE_METRICS`: List of tracked metrics
- `ALERT_THRESHOLDS`: Alert trigger thresholds
- `LOG_LEVEL`: Logging verbosity

#### Alerts
- `ALERT_CHANNELS`: Alert notification channels
- `ALERT_FREQUENCY`: Alert check frequency
- `ALERT_RETENTION`: Alert history retention

## Best Practices

### 1. Security

#### API Key Management
- Use environment variables for sensitive data
- Rotate API keys regularly
- Never commit API keys to version control

#### Access Control
- Enable IP whitelisting
- Implement rate limiting
- Use strong authentication

### 2. Performance

#### RPC Configuration
- Use multiple RPC providers
- Enable automatic failover
- Monitor RPC health

#### Resource Usage
- Optimize memory usage
- Implement caching
- Use connection pooling

### 3. Risk Management

#### Position Sizing
- Start with small positions
- Use dynamic position sizing
- Implement portfolio limits

#### Stop Loss
- Always use stop losses
- Consider using trailing stops
- Monitor slippage

## Troubleshooting

### 1. Common Issues

#### RPC Connection
```bash
# Check RPC status
curl -X POST -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}' \
     $RPC_ENDPOINT
```

#### API Rate Limits
```bash
# Check rate limit status
curl -I -H "Authorization: Bearer $API_KEY" $API_ENDPOINT
```

### 2. Configuration Validation

```bash
# Validate configuration
python tools/validate_config.py

# Test configuration
python tools/test_config.py
```

## Configuration Examples

### 1. Conservative Trading

```javascript
{
  "risk": {
    "position_sizing": {
      "max_position_size": 500,
      "position_sizing_model": "fixed"
    },
    "stop_loss": {
      "enabled": true,
      "type": "fixed",
      "percentage": 2
    },
    "take_profit": {
      "enabled": true,
      "percentage": 5
    }
  }
}
```

### 2. Aggressive Trading

```javascript
{
  "risk": {
    "position_sizing": {
      "max_position_size": 2000,
      "position_sizing_model": "kelly"
    },
    "stop_loss": {
      "enabled": true,
      "type": "trailing",
      "percentage": 5
    },
    "take_profit": {
      "enabled": true,
      "percentage": 15
    }
  }
}
```

## Configuration Management

### 1. Version Control

```bash
# Save current configuration
python tools/save_config.py

# Load configuration
python tools/load_config.py version_1
```

### 2. Backup

```bash
# Backup configuration
python tools/backup_config.py

# Restore configuration
python tools/restore_config.py backup_20250209
```

### 3. Validation

```bash
# Validate configuration
python tools/validate_config.py

# Test configuration
python tools/test_config.py
```
