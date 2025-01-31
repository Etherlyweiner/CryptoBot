# CryptoBot

A cryptocurrency trading bot that uses technical analysis and machine learning to make trading decisions on Binance.

## Features

- Real-time market analysis
- Technical indicators (RSI, MACD, Bollinger Bands)
- Machine learning-based predictions
- Risk management system
- Telegram notifications
- Web-based dashboard
- Automated trading execution
- Configurable trading parameters

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

4. Configure your API keys in `.env`:
```
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
```

5. Adjust trading parameters in `config.py`

## Usage

1. Start the bot and dashboard:
```bash
streamlit run app.py
```

2. Or use the provided shortcut:
- Double-click `start_cryptobot.bat`

## Files

- `app.py`: Streamlit dashboard
- `bot.py`: Trading bot implementation
- `config.py`: Configuration settings
- `ml_strategy.py`: Machine learning strategy
- `risk_monitor.py`: Risk management system
- `requirements.txt`: Project dependencies
