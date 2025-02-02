"""
Test script to verify .env configuration
"""

import os
import sys
import requests
from dotenv import load_dotenv
from binance.client import Client
from datetime import datetime

def test_env_loading():
    """Test if .env file is loaded correctly"""
    load_dotenv()
    required_vars = [
        'BINANCE_API_KEY',
        'BINANCE_API_SECRET',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print("[X] Missing environment variables:", ", ".join(missing))
        return False
    
    print("[+] Environment variables loaded successfully")
    return True

def test_telegram():
    """Test Telegram bot configuration"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    test_message = f"CryptoBot Test Message\nTimestamp: {datetime.now()}"
    
    try:
        response = requests.post(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': test_message,
                'parse_mode': 'HTML'
            },
            timeout=10
        )
        response.raise_for_status()
        print("[+] Telegram notification sent successfully")
        return True
    except Exception as e:
        print("[X] Telegram test failed:", str(e))
        return False

def test_binance():
    """Test Binance.US API connection"""
    try:
        # Use Binance.US API endpoint
        client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'), 
                       tld='us')  # This sets the API to use Binance.US
        
        # Test API connection with a simple request
        server_time = client.get_server_time()
        
        # Test getting account information
        account = client.get_account()
        print("[+] Successfully connected to Binance.US API")
        print("[+] Account status:", account.get('status', 'active'))
        
        # Test getting BTC/USD price
        btc_price = client.get_symbol_ticker(symbol="BTCUSD")
        print(f"[+] Current BTC/USD price: ${float(btc_price['price']):.2f}")
        
        return True
    except Exception as e:
        print("[X] Binance.US API test failed:", str(e))
        return False

def main():
    print("\nTesting Configuration...")
    print("-" * 50)
    
    # Test 1: Environment Variables
    if not test_env_loading():
        print("\n[X] Configuration test failed: Missing environment variables")
        sys.exit(1)
    
    # Test 2: Telegram
    print("\nTesting Telegram notifications...")
    telegram_ok = test_telegram()
    
    # Test 3: Binance
    print("\nTesting Binance.US API connection...")
    binance_ok = test_binance()
    
    print("\n" + "-" * 50)
    if telegram_ok and binance_ok:
        print("[+] All tests passed! Configuration is correct.")
    else:
        print("[X] Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
