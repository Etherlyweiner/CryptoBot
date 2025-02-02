# CryptoBot

A Solana-based cryptocurrency trading bot that integrates with Phantom wallet for automated trading on Jupiter DEX.

## Features

- Phantom wallet integration
- Solana token trading via Jupiter DEX
- Real-time market monitoring
- Technical analysis:
  - RSI
  - MACD
  - EMA crossovers
- Risk management:
  - Position sizing
  - Stop-loss
  - Take-profit
  - Maximum drawdown protection
- Web-based dashboard
- Trade history tracking
- Performance analytics
- Structured logging

## Prerequisites

- Python 3.8 or higher
- Phantom wallet browser extension
- Solana account with SOL for transaction fees

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows: `venv\Scripts\activate`
- Unix/MacOS: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and configure your settings:
```bash
cp .env.example .env
```

Key settings to configure:
- `NETWORK`: Choose between mainnet-beta, testnet, or devnet
- `RPC_URL`: Your preferred Solana RPC endpoint
- Trading parameters (POSITION_SIZE, STOP_LOSS_PERCENT, etc.)
- Risk management settings

## Usage

1. Ensure Phantom wallet extension is installed and configured in your browser

2. Start the trading dashboard:
```bash
streamlit run app.py
```

3. Connect your Phantom wallet when prompted

4. Monitor trades and performance at `http://localhost:8501`

## Components

- `wallet.py`: Phantom wallet integration
- `bot.py`: Core trading logic
- `config.py`: Configuration management
- `database.py`: Trade history and analytics
- `app.py`: Web-based dashboard

## Dashboard Features

- Wallet connection status
- Portfolio overview
- Active trades monitoring
- Historical performance
- Risk metrics
- Market analysis

## Security Notes

- Never share your Phantom wallet private key
- Use appropriate slippage settings to prevent front-running
- Start with small trade sizes while testing
- Monitor transaction fees
- Use official RPC endpoints or trusted providers

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see LICENSE file for details
