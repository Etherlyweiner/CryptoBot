"""
CryptoBot Dashboard Application
"""

import os
import streamlit as st
import logging
from datetime import datetime
from pathlib import Path
import json
import sys
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.cryptobot.main import CryptoBot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Solana Trading Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def render_header():
    """Render the dashboard header."""
    st.title("🤖 Solana Trading Bot")
    st.markdown("---")

def render_wallet_info(bot):
    """Render wallet information section."""
    st.header("💰 Wallet Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'wallet_address' in st.session_state:
            try:
                # Validate wallet address format
                Pubkey(st.session_state.wallet_address)
                st.info(f"Connected Wallet: {st.session_state.wallet_address[:8]}...{st.session_state.wallet_address[-8:]}")
            except ValueError:
                st.error("Invalid wallet address format")
        else:
            st.warning("No wallet connected")
    
    with col2:
        if 'wallet_balance' in st.session_state:
            st.metric("Wallet Balance", f"{st.session_state.wallet_balance:.4f} SOL")
        else:
            st.warning("Balance not available")

def render_bot_controls(bot):
    """Render bot control section."""
    st.header("🎮 Bot Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Start Bot", disabled=st.session_state.get('bot_running', False)):
            st.session_state.bot_running = True
            bot.start()
            st.success("Bot started successfully!")
    
    with col2:
        if st.button("Stop Bot", disabled=not st.session_state.get('bot_running', False)):
            st.session_state.bot_running = False
            bot.stop()
            st.info("Bot stopped successfully!")

def render_market_info():
    """Render market information section."""
    st.header("📊 Market Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("SOL Price", "$100.00", "2.5%")
    with col2:
        st.metric("24h Volume", "$1.2B", "-5%")
    with col3:
        st.metric("Market Cap", "$42.5B", "1.2%")

async def get_wallet_balance():
    """Get wallet balance with retries and proper error handling"""
    try:
        # Use environment variables with fallbacks
        network = os.getenv('NETWORK', 'mainnet-beta')
        helius_key = os.getenv('HELIUS_API_KEY')
        wallet_address = os.getenv('WALLET_ADDRESS')
        
        if not all([network, helius_key, wallet_address]):
            st.error("Missing required configuration. Please check your environment variables.")
            return None
            
        # Initialize RPC client with retry logic
        rpc_url = f"https://rpc.helius.xyz/?api-key={helius_key}"
        client = AsyncClient(rpc_url, commitment="confirmed")
        
        # Get wallet balance
        pubkey = Pubkey.from_string(wallet_address)
        balance = await client.get_balance(pubkey)
        return balance.value / 1e9  # Convert lamports to SOL
    except Exception as e:
        st.error(f"Failed to get wallet balance: {str(e)}")
        return None
    finally:
        await client.close()

async def update_wallet_balance(bot):
    """Update wallet balance."""
    try:
        logger.info("Starting wallet balance update...")
        
        # Validate wallet address
        try:
            wallet_address = st.session_state.wallet_address
            Pubkey(wallet_address)
            logger.info(f"Wallet address format valid: {wallet_address}")
        except ValueError as ve:
            error_msg = f"Invalid wallet address format: {str(ve)}"
            logger.error(error_msg)
            st.error(error_msg)
            return
        
        # Ensure connection is established
        if bot.client is None:
            logger.info("No client connection, attempting to connect...")
            connected = await bot.connect()
            if not connected:
                error_msg = "Failed to connect to Helius RPC"
                logger.error(error_msg)
                st.error(error_msg)
                return
            logger.info("Connection established successfully")
        
        logger.info("Checking wallet balance...")
        balance = await get_wallet_balance()
        
        if balance is not None:
            logger.info(f"Setting session state balance to {balance:.4f} SOL")
            st.session_state.wallet_balance = balance
            st.session_state.last_balance_update = datetime.now()
            # Force Streamlit to update
            st.experimental_rerun()
        else:
            logger.error("Balance returned None")
            st.error("Unable to retrieve wallet balance")
            
    except Exception as e:
        error_msg = f"Failed to update wallet balance: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full stack trace:")
        st.error(error_msg)

def initialize_bot():
    """Initialize the trading bot."""
    if 'bot' not in st.session_state:
        try:
            logger.info("Initializing new bot instance...")
            st.session_state.bot = CryptoBot()
            st.session_state.bot_running = False
            
            # Load config
            config_path = Path(project_root) / "config" / "config.json"
            with open(config_path) as f:
                config = json.load(f)
            
            # Store wallet address
            st.session_state.wallet_address = config['wallet']['address']
            logger.info(f"Bot initialized with wallet: {st.session_state.wallet_address}")
            
            return st.session_state.bot
            
        except Exception as e:
            error_msg = f"Failed to initialize bot: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full stack trace:")
            st.error(error_msg)
            return None
    
    return st.session_state.bot

def main():
    """Main dashboard function."""
    try:
        render_header()
        
        # Initialize bot
        bot = initialize_bot()
        if bot is None:
            st.error("Failed to initialize bot. Please check the configuration and try again.")
            return
        
        # Create layout
        render_wallet_info(bot)
        render_bot_controls(bot)
        render_market_info()
        
        # Initial balance check
        if 'wallet_balance' not in st.session_state:
            logger.info("No wallet balance in session, performing initial check...")
            bot.update_wallet_balance()
        
        # Update balance every 30 seconds if bot is running
        if st.session_state.get('bot_running', False):
            now = datetime.now()
            last_update = st.session_state.get('last_balance_update', now - datetime.timedelta(minutes=1))
            if (now - last_update).total_seconds() > 30:
                logger.info("Updating wallet balance (30s refresh)...")
                bot.update_wallet_balance()
    
    except Exception as e:
        error_msg = f"Main loop error: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full stack trace:")
        st.error(error_msg)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logger.error(f"Application error: {str(e)}")

# Flask application for CryptoBot dashboard.

import os
import logging
from typing import Optional
import asyncio
from flask import Flask, jsonify, render_template, request
from bot import CryptoBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Initialize bot
bot: Optional[CryptoBot] = None

@app.route('/')
def index():
    """Render main dashboard."""
    return render_template('index.html')

@app.route('/api/bot/status')
def get_bot_status():
    """Get bot status."""
    if not bot:
        return jsonify({'error': 'Bot not initialized'}), 500
    return jsonify(bot.get_status())

@app.route('/api/bot/start', methods=['POST'])
async def start_bot():
    """Start the bot."""
    global bot
    try:
        if not bot:
            bot = CryptoBot('config/config.yaml')
            await bot.initialize()
        await bot.start()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/stop', methods=['POST'])
async def stop_bot():
    """Stop the bot."""
    global bot
    try:
        if bot:
            await bot.stop()
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Bot not initialized'}), 500
    except Exception as e:
        logger.error(f"Failed to stop bot: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
def get_performance():
    """Get performance metrics."""
    if not bot or not bot.analytics:
        return jsonify({'error': 'Bot not initialized'}), 500
    return jsonify(bot.analytics.get_summary())

@app.route('/api/positions')
def get_positions():
    """Get open positions."""
    if not bot or not bot.strategy:
        return jsonify({'error': 'Bot not initialized'}), 500
    return jsonify(bot.strategy.get_positions())

def run_app():
    """Run the Flask app with asyncio support."""
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    run_app()
