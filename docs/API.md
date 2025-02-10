# CryptoBot API Documentation

## Overview

The CryptoBot API provides programmatic access to the trading bot's functionality, allowing you to integrate its features into your own applications or create custom interfaces.

## Authentication

All API endpoints require authentication using an API key. Include your API key in the request header:

```http
Authorization: Bearer your_api_key_here
```

## Rate Limiting

- 60 requests per minute per IP
- 1000 requests per day per API key
- Burst limit: 10 requests per second

## Endpoints

### Trading Operations

#### Get Trading Status

```http
GET /api/v1/status
```

Returns the current trading status and system health.

**Response:**
```json
{
    "status": "active",
    "uptime": 3600,
    "last_trade": "2025-02-09T18:55:18-07:00",
    "active_positions": 2,
    "system_health": {
        "rpc_status": "healthy",
        "wallet_connected": true,
        "memory_usage": 256.5
    }
}
```

#### Execute Trade

```http
POST /api/v1/trade
```

Execute a new trade.

**Request Body:**
```json
{
    "token": "SOL",
    "amount": 1.0,
    "side": "BUY",
    "type": "MARKET"
}
```

**Response:**
```json
{
    "trade_id": "t123456",
    "status": "executed",
    "timestamp": "2025-02-09T18:55:18-07:00",
    "details": {
        "price": 100.50,
        "fee": 0.1,
        "tx_hash": "5KL..."
    }
}
```

### Market Data

#### Get Token Price

```http
GET /api/v1/price/{token}
```

Get the current price of a token.

**Parameters:**
- `token`: Token symbol (e.g., "SOL")

**Response:**
```json
{
    "token": "SOL",
    "price": 100.50,
    "timestamp": "2025-02-09T18:55:18-07:00",
    "source": "Jupiter"
}
```

#### Get Market Data

```http
GET /api/v1/market/{token}
```

Get detailed market data for a token.

**Parameters:**
- `token`: Token symbol
- `timeframe`: Optional, defaults to "1h"

**Response:**
```json
{
    "token": "SOL",
    "data": {
        "price": 100.50,
        "volume_24h": 1000000,
        "change_24h": 5.2,
        "high_24h": 102.00,
        "low_24h": 98.00
    }
}
```

### Strategy Management

#### List Strategies

```http
GET /api/v1/strategies
```

List all available trading strategies.

**Response:**
```json
{
    "strategies": [
        {
            "name": "momentum",
            "enabled": true,
            "performance": {
                "win_rate": 0.65,
                "profit": 150.25
            }
        },
        {
            "name": "meanReversion",
            "enabled": true,
            "performance": {
                "win_rate": 0.58,
                "profit": 120.75
            }
        }
    ]
}
```

#### Update Strategy

```http
PUT /api/v1/strategies/{name}
```

Update strategy configuration.

**Request Body:**
```json
{
    "enabled": true,
    "parameters": {
        "timeframe": "5m",
        "indicators": {
            "rsi": {
                "period": 14,
                "overbought": 70,
                "oversold": 30
            }
        }
    }
}
```

**Response:**
```json
{
    "status": "updated",
    "strategy": "momentum",
    "timestamp": "2025-02-09T18:55:18-07:00"
}
```

### Performance Analytics

#### Get Performance Stats

```http
GET /api/v1/performance
```

Get trading performance statistics.

**Parameters:**
- `period`: Optional, defaults to "1d"
- `strategy`: Optional, filter by strategy

**Response:**
```json
{
    "period": "1d",
    "stats": {
        "total_trades": 24,
        "win_rate": 0.625,
        "profit_loss": 250.75,
        "max_drawdown": -50.25,
        "sharpe_ratio": 1.5
    },
    "by_strategy": {
        "momentum": {
            "trades": 14,
            "win_rate": 0.65,
            "profit": 150.25
        },
        "meanReversion": {
            "trades": 10,
            "win_rate": 0.58,
            "profit": 100.50
        }
    }
}
```

#### Get Trade History

```http
GET /api/v1/trades
```

Get historical trade data.

**Parameters:**
- `start_date`: Optional
- `end_date`: Optional
- `limit`: Optional, defaults to 100
- `strategy`: Optional, filter by strategy

**Response:**
```json
{
    "trades": [
        {
            "id": "t123456",
            "token": "SOL",
            "side": "BUY",
            "amount": 1.0,
            "price": 100.50,
            "timestamp": "2025-02-09T18:55:18-07:00",
            "strategy": "momentum",
            "profit_loss": 5.25
        }
    ],
    "pagination": {
        "total": 245,
        "page": 1,
        "limit": 100
    }
}
```

### Risk Management

#### Get Risk Metrics

```http
GET /api/v1/risk
```

Get current risk metrics.

**Response:**
```json
{
    "metrics": {
        "total_exposure": 5000.75,
        "largest_position": 1000.50,
        "daily_drawdown": -100.25,
        "risk_score": 0.65
    },
    "limits": {
        "max_position_size": 2000.00,
        "daily_loss_limit": 500.00,
        "max_trades_per_day": 50
    }
}
```

#### Update Risk Parameters

```http
PUT /api/v1/risk
```

Update risk management parameters.

**Request Body:**
```json
{
    "max_position_size": 2000.00,
    "daily_loss_limit": 500.00,
    "max_trades_per_day": 50
}
```

**Response:**
```json
{
    "status": "updated",
    "timestamp": "2025-02-09T18:55:18-07:00"
}
```

## WebSocket API

### Real-time Updates

Connect to the WebSocket endpoint:

```
ws://your-server/ws
```

#### Subscribe to Updates

```json
{
    "action": "subscribe",
    "channels": ["trades", "performance", "alerts"]
}
```

#### Trade Updates

```json
{
    "channel": "trades",
    "data": {
        "id": "t123456",
        "token": "SOL",
        "side": "BUY",
        "amount": 1.0,
        "price": 100.50,
        "timestamp": "2025-02-09T18:55:18-07:00"
    }
}
```

#### Performance Updates

```json
{
    "channel": "performance",
    "data": {
        "profit_loss": 250.75,
        "win_rate": 0.625,
        "active_positions": 2
    }
}
```

#### Alert Updates

```json
{
    "channel": "alerts",
    "data": {
        "type": "RISK",
        "severity": "HIGH",
        "message": "Daily loss limit reached",
        "timestamp": "2025-02-09T18:55:18-07:00"
    }
}
```

## Error Handling

### Error Response Format

```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable error message",
        "details": {
            "field": "Additional error context"
        }
    }
}
```

### Common Error Codes

- `AUTH_ERROR`: Authentication failed
- `RATE_LIMIT`: Rate limit exceeded
- `INVALID_PARAMS`: Invalid parameters
- `TRADE_FAILED`: Trade execution failed
- `SYSTEM_ERROR`: Internal system error

## SDK Examples

### Python

```python
from cryptobot_sdk import CryptoBot

# Initialize client
bot = CryptoBot(api_key='your_api_key')

# Get trading status
status = bot.get_status()

# Execute trade
trade = bot.execute_trade(
    token='SOL',
    amount=1.0,
    side='BUY'
)

# Get performance stats
stats = bot.get_performance(period='1d')
```

### JavaScript

```javascript
const CryptoBot = require('cryptobot-sdk');

// Initialize client
const bot = new CryptoBot('your_api_key');

// Get trading status
bot.getStatus()
   .then(status => console.log(status))
   .catch(error => console.error(error));

// Execute trade
bot.executeTrade({
    token: 'SOL',
    amount: 1.0,
    side: 'BUY'
}).then(trade => console.log(trade));

// Get performance stats
bot.getPerformance({ period: '1d' })
   .then(stats => console.log(stats));
```
