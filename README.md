# CryptoBot - Autonomous Trading System

An advanced cryptocurrency trading bot built on the Solana blockchain, featuring real-time market analysis, multiple trading strategies, and comprehensive risk management.

## Features

- **Multi-Strategy Trading**
  - Momentum-based strategy
  - Mean reversion strategy
  - Custom strategy framework
  - Strategy performance analytics

- **Risk Management**
  - Dynamic position sizing
  - Stop-loss automation
  - Risk factor analysis
  - Exposure limits
  - Correlation monitoring

- **Performance Analytics**
  - Real-time P&L tracking
  - Strategy performance metrics
  - Risk-adjusted returns
  - Trade analytics
  - Custom alerts

- **System Security**
  - Wallet security measures
  - Transaction validation
  - API key management
  - Rate limiting
  - IP whitelisting

## Prerequisites

- Node.js >= 16.0.0
- Python >= 3.8
- Solana CLI tools
- Hardware wallet (recommended)

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/CryptoBot.git
   cd CryptoBot
   ```

2. **Install Dependencies**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt

   # Install Node.js dependencies
   npm install
   ```

3. **Configure Environment**
   ```bash
   # Copy example environment file
   cp .env.example .env

   # Edit .env with your settings
   nano .env
   ```

4. **Initialize Configuration**
   ```bash
   # Generate configuration files
   python init_config.py
   ```

## Configuration

### Environment Variables

```env
# RPC Endpoints
HELIUS_RPC=https://mainnet.helius-rpc.com
HELIUS_KEY=your_helius_api_key
QUICKNODE_RPC=your_quicknode_endpoint
QUICKNODE_KEY=your_quicknode_api_key

# API Keys
JUPITER_API=https://quote-api.jup.ag/v6
BIRDEYE_API=https://public-api.birdeye.so/public

# Security
WHITELISTED_IPS=127.0.0.1,your_ip_address
MAX_REQUESTS_PER_MINUTE=60
KEY_ROTATION_DAYS=30

# Trading Parameters
MAX_POSITION_SIZE=1000  # in USD
DAILY_LOSS_LIMIT=100    # in USD
MAX_TRADES_PER_DAY=10
```

### Trading Strategies

Configure trading strategies in `config.js`:

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
      }
    }
  }
}
```

## Usage

### Starting the Bot

1. **Start the Server**
   ```bash
   # Start the Python server
   python run_server.py

   # Or use the Node.js server
   node https-server.js
   ```

2. **Access the Dashboard**
   - Open `http://localhost:3000` in your browser
   - Connect your wallet
   - Configure trading parameters
   - Start trading

### Running Tests

```bash
# Run all tests
node tests/run_tests.js

# Or use the browser interface
open tests/test.html
```

## Monitoring & Maintenance

### Performance Dashboard

Access the performance dashboard at `http://localhost:3000/dashboard` to monitor:
- Real-time P&L
- Trade history
- Strategy performance
- Risk metrics
- System alerts

### Logs

Logs are stored in the `logs` directory:
```
logs/
├── trading.log    # Trading activity
├── system.log     # System events
├── error.log      # Error messages
└── security.log   # Security events
```

### Backups

Automatic backups are stored in `backups/`:
```
backups/
├── config/        # Configuration backups
├── trades/        # Trade history
└── analytics/     # Performance data
```

## Security Best Practices

1. **API Key Management**
   - Rotate API keys regularly
   - Use environment variables
   - Never commit keys to repository

2. **Wallet Security**
   - Use hardware wallets
   - Enable transaction signing
   - Set trade limits

3. **Network Security**
   - Enable IP whitelisting
   - Use rate limiting
   - Monitor for suspicious activity

## Troubleshooting

### Common Issues

1. **RPC Connection Failures**
   ```bash
   # Check RPC status
   python tools/check_rpc.py

   # Switch RPC endpoint
   python tools/switch_rpc.py
   ```

2. **Transaction Errors**
   ```bash
   # Verify transaction
   python tools/verify_tx.py <tx_id>

   # Check account balance
   python tools/check_balance.py
   ```

3. **Performance Issues**
   ```bash
   # Run diagnostics
   python tools/diagnostics.py

   # Clear cache
   python tools/clear_cache.py
   ```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please:
1. Check the [documentation](docs/)
2. Search [existing issues](issues/)
3. Create a new issue

## Acknowledgments

- Solana Foundation
- Jupiter Exchange
- Helius
- QuickNode
