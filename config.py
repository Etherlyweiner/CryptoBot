from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
PHANTOM_WALLET = os.getenv('PHANTOM_WALLET_ADDRESS')
TELEGRAM_BOT_TOKEN = "7862793413:AAEOthxs6uSmce3-lx-lQOqBeV5cnYjL74c"

# Trading Parameters
TRADING_PAIRS = ['SOL/USDT']
TIMEFRAME = '1m'  # 1-minute timeframe for faster reactions
TARGET_POSITION_SIZE = 5.0  # Target position size in USD

# Risk Management
STOP_LOSS_PERCENTAGE = 0.015  # Tighter 1.5% stop loss
TAKE_PROFIT_PERCENTAGE = 0.05  # 5% take profit
MAX_TRADES_PER_DAY = 10  # Increased for more opportunities
RISK_SCORE_THRESHOLD = 0.7  # Minimum risk score to execute trade
VOLUME_SPIKE_THRESHOLD = 3.0  # Volume increase factor to detect pumps
LIQUIDITY_THRESHOLD = 50000  # Minimum liquidity in USD
MAX_PRICE_IMPACT = 0.02  # Maximum allowable price impact

# Machine Learning Parameters
MODEL_UPDATE_INTERVAL = 6  # Hours between model updates
LEARNING_RATE = 0.001
HISTORICAL_DATA_DAYS = 30

# Monitoring Sources
DEX_SCREENER_URL = "https://dexscreener.com"
PUMP_DETECTION_SOURCES = [
    "https://pumpfun.com",
    "https://dextools.io",
    "https://poocoin.app"
]

# Notification Settings
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
NOTIFICATION_COOLDOWN = 300  # seconds between notifications

# UI Settings
UI_REFRESH_RATE = 5  # seconds
UI_PORT = 8501  # Streamlit port
DARK_MODE = True
