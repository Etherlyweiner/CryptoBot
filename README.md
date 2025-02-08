# CryptoBot - Professional Solana Trading Bot

A sophisticated cryptocurrency trading bot focused on conservative trading strategies with robust risk management, built for the Solana blockchain.

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

### Technical Features

- Prometheus metrics integration
- Advanced error handling and logging
- Secure credential storage
- RPC connection fallback system
- Professional UI with Streamlit

## Installation

### Prerequisites

- Python 3.10
- Git
- Phantom Wallet
- Solana CLI (optional)

### Quick Start

1. Clone the repository:

   ```bash
   git clone https://github.com/Etherlyweiner/CryptoBot.git
   cd CryptoBot
   ```

2. Create and activate a virtual environment:

   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Linux/Mac
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -e .
   ```

4. Configure your environment:

   ```bash
   cp config/env_template.txt .env
   # Edit .env with your settings
   ```

5. Start the bot:

   ```bash
   streamlit run src/cryptobot/app.py
   ```

## Quick Start

### First-Time Setup

1. Install Redis for Windows (if not already installed)
2. Install Node.js (if not already installed)
3. Run the following command to create a desktop shortcut:

   ```powershell
   powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
   ```

### Starting the Bot

1. **Using the Desktop Shortcut**

   - Double-click the "CryptoBot Dashboard" shortcut on your desktop
   - The dashboard will open automatically in your default browser
   - All components (Redis, Trading Bot, Dashboard) will start automatically

2. **Manual Start**

   - Run `start_all.bat` from the project directory
   - The dashboard will open automatically at http://localhost:8000

### Components

The startup script ensures all components start in the correct order:

1. Redis server (if not running)
2. Node.js dashboard server
3. Python trading bot
4. Web browser with dashboard

### Troubleshooting

If you encounter any issues:

1. Ensure Redis is installed and running (`net start Redis` as Administrator)
2. Verify Node.js is installed (`node --version`)
3. Check the logs in the `logs` directory for detailed error messages

## Configuration

### Environment Variables

- `SOLANA_NETWORK`: Network to connect to (mainnet-beta/devnet)
- `SOLANA_RPC_URL`: Your Solana RPC URL
- `PHANTOM_WALLET_ADDRESS`: Your Phantom wallet address
- `SOLSCAN_API_KEY`: Your Solscan API key

### Trading Parameters

Edit `config/trading.json`:

```json
{
    "POSITION_SIZE_SOL": 0.1,
    "STOP_LOSS_PERCENT": 5,
    "TAKE_PROFIT_PERCENT": 10,
    "MAX_POSITIONS": 3,
    "MAX_TRADES_PER_DAY": 20,
    "ORDER_TIMEOUT": 45
}
```

### Network Configuration

Edit `config/network.json`:

```json
{
    "SOLANA_NETWORK": "mainnet-beta",
    "SOLANA_RPC_URL": "https://api.mainnet-beta.solana.com",
    "BACKUP_RPC_URLS": [
        "https://solana-mainnet.g.alchemy.com/v2/demo",
        "https://rpc.ankr.com/solana"
    ]
}
```

## Usage

### Starting the Bot

1. Ensure your Phantom wallet is connected
2. Start the Streamlit dashboard:

   ```bash
   streamlit run src/cryptobot/app.py
   ```

3. Navigate to the dashboard (default: http://localhost:8501)
4. Configure your trading parameters
5. Start trading!

### Monitoring

- View real-time metrics at http://localhost:8501
- Check logs in the `logs` directory
- Monitor Prometheus metrics at http://localhost:9090

### Backup and Recovery

- Daily log rotation
- Automatic state backup
- Transaction history export

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black src/

# Sort imports
isort src/

# Lint code
flake8 src/
```

### Building Documentation

```bash
cd docs/
make html
```

## Support and Contributing

- Report issues on GitHub
- Join our Discord community
- Submit pull requests
- Read our contribution guidelines

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Security

Please report security issues directly to security@example.com
