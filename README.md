# CryptoBot - Conservative Trading Bot

A sophisticated cryptocurrency trading bot focused on conservative trading strategies with robust risk management.

## Features

### Conservative Trading Strategy
- Dynamic position sizing based on market conditions
- Advanced risk management with multiple safety checks
- Support/resistance level detection
- Volume profile analysis
- Market volatility monitoring

### Risk Management
- Maximum drawdown protection
- Position size limits
- Total exposure control
- Win rate monitoring
- Correlation analysis
- Daily trade limits

### Real-time Monitoring
- Performance dashboard
- Risk metrics visualization
- Trading activity tracking
- Historical analysis tools
- Alert system

### Data Storage
- SQLite database for trade history
- Risk metrics tracking
- Market condition analysis
- Performance statistics

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/CryptoBot.git
cd CryptoBot
```

2. Create and activate virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
python -m alembic upgrade head
```

## Usage

1. Start the trading bot:
```bash
python bot.py
```

2. Launch monitoring dashboard:
```bash
streamlit run monitoring_dashboard.py
```

## Solana Trading Setup

### Prerequisites
1. Install [Phantom Wallet](https://phantom.app/) browser extension
2. Create a Solana wallet and fund it with SOL
3. Ensure you have Python 3.8+ installed

### Solana Configuration
1. Get a Solana RPC URL (you can use public endpoints or get a dedicated one from [QuickNode](https://www.quicknode.com/))
2. Configure your `.env` file with:
```bash
# Solana Configuration
SOLANA_RPC_URL=your_rpc_url_here
NETWORK=mainnet  # or devnet for testing

# Trading Parameters
POSITION_SIZE=0.1  # SOL per trade
MAX_POSITIONS=1
STOP_LOSS_PCT=0.05
TAKE_PROFIT_PCT=0.2
MAX_SLIPPAGE_BPS=100
MIN_LIQUIDITY=1000
```

### Running Solana Bot
1. Start the Solana trading bot:
```bash
python test_solana_trade.py
```

2. When prompted:
   - Connect your Phantom Wallet
   - Approve the connection
   - Review and approve transactions

### Supported Features
- Memecoin trading on Solana
- Integration with Jupiter DEX for best prices
- Real-time price monitoring
- Technical analysis
- Social sentiment analysis
- Risk management
- Performance tracking

### Safety Features
- Slippage protection
- Liquidity validation
- Transaction simulation
- Error handling
- Automatic stop-loss
- Position size limits

## Warning
This bot is for personal use only. Trading cryptocurrencies involves significant risk. Only trade with funds you can afford to lose.

## Configuration

The bot can be configured through:
1. Environment variables (`.env` file)
2. Configuration files in `config/`
3. Command line arguments

Key configuration parameters:
- `MAX_POSITION_SIZE`: Maximum single position size (default: 10%)
- `MAX_TOTAL_EXPOSURE`: Maximum total exposure (default: 50%)
- `MAX_DRAWDOWN`: Maximum allowed drawdown (default: 15%)
- `RISK_PER_TRADE`: Risk per trade (default: 2%)
- `MIN_WIN_RATE`: Minimum required win rate (default: 40%)

## Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

## Monitoring

The monitoring dashboard provides:
1. Real-time performance metrics
2. Risk analytics
3. Trading activity visualization
4. Historical analysis
5. Alert monitoring

Access the dashboard at `http://localhost:8501` after starting with Streamlit.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This is a private, proprietary software project intended for personal use only.
All rights reserved. Unauthorized copying, modification, distribution, or use of this software is strictly prohibited.

See the PRIVATE_LICENSE file for details.

## Disclaimer

This bot is for educational purposes only. Cryptocurrency trading carries significant risks. Always test thoroughly with small amounts first.
