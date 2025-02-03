"""
CryptoBot Dashboard Application
"""

import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import logging
from pathlib import Path
import json
import sys
from spl_governance import PublicKey  # Import PublicKey from spl_governance

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
                PublicKey(st.session_state.wallet_address)
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
            asyncio.create_task(bot.start())
            st.success("Bot started successfully!")
    
    with col2:
        if st.button("Stop Bot", disabled=not st.session_state.get('bot_running', False)):
            st.session_state.bot_running = False
            asyncio.create_task(bot.stop())
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

async def update_wallet_balance(bot):
    """Update wallet balance."""
    try:
        logger.info("Starting wallet balance update...")
        
        # Validate wallet address
        try:
            wallet_address = st.session_state.wallet_address
            PublicKey(wallet_address)
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
        balance = await bot.check_balance()
        
        if balance is not None:
            sol_balance = balance / 1e9
            logger.info(f"Setting session state balance to {sol_balance:.4f} SOL")
            st.session_state.wallet_balance = sol_balance
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
            asyncio.run(update_wallet_balance(bot))
        
        # Update balance every 30 seconds if bot is running
        if st.session_state.get('bot_running', False):
            now = datetime.now()
            last_update = st.session_state.get('last_balance_update', now - timedelta(minutes=1))
            if (now - last_update).total_seconds() > 30:
                logger.info("Updating wallet balance (30s refresh)...")
                asyncio.run(update_wallet_balance(bot))
    
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
