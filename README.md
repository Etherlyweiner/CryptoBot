# CryptoBot

A cryptocurrency trading bot that uses technical analysis to make trading decisions on Binance.

## Features

- Supports multiple trading pairs
- Technical analysis using RSI, MACD, and Bollinger Bands
- Automated trading execution
- Configurable trading parameters
- Scheduled trading strategy execution

## Setup

1. Create a virtual environment (already done):
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

4. Configure your API keys:
- Rename `.env` file
- Add your Binance API key and secret

5. Adjust trading parameters in `config.py`:
- Trading pairs
- Timeframe
- Trading quantity
- Stop loss and take profit percentages

## Usage

Run the bot:
```bash
python bot.py
```

## Files

- `bot.py`: Main trading bot implementation
- `config.py`: Configuration settings
- `requirements.txt`: Project dependencies
- `.env`: API credentials (keep this secure!)

## Warning

This is a basic trading bot for educational purposes. Always test with small amounts first and understand the risks of automated trading.
