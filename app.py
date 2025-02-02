"""
CryptoBot Dashboard Application
"""

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import asyncio
from bot import TradingBot
from dotenv import load_dotenv

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Solana Trading Bot",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'bot' not in st.session_state:
    try:
        from bot.trading_bot import TradingConfig
        from bot.wallet.phantom_integration import PhantomWalletManager
        from bot.security.win_credentials import WindowsCredManager
        import base64
        import os
        import logging
        
        # Set up logging
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        
        logger.debug("Starting bot initialization...")
        
        # Initialize Phantom Wallet
        wallet_manager = PhantomWalletManager()
        logger.debug("Created wallet manager")
        
        # Generate new keypair
        from solders.keypair import Keypair
        
        # Create a new Solana keypair
        keypair = Keypair()
        secret_bytes = keypair.secret()
        logger.debug(f"Generated new Solana keypair with public key: {keypair.pubkey()}")
            
        # Initialize wallet with keypair secret
        try:
            asyncio.run(wallet_manager.initialize_wallet(secret_bytes))
            logger.debug("Initialized wallet with keypair")
        except Exception as e:
            logger.error(f"Failed to initialize wallet: {str(e)}")
            raise
        
        # Create trading config for Solana memecoin trading
        config = TradingConfig(
            base_currency='SOL',
            quote_currency='USDC',
            position_size=0.1,     # 10% of available balance
            stop_loss=0.02,        # 2% stop loss
            take_profit=0.05,      # 5% take profit
            max_slippage=0.01,     # 1% max slippage
            network='mainnet-beta', # Solana network
            max_positions=5,        # Maximum number of concurrent positions
            max_trades_per_day=10   # Maximum number of trades per day
        )
        logger.debug("Created trading config")
        
        try:
            st.session_state.bot = TradingBot(wallet=wallet_manager, config=config)
            logger.debug("Created trading bot instance")
            
            # Show wallet address
            wallet_address = wallet_manager.keypair.pubkey()
            st.sidebar.success(f"Connected to wallet: {wallet_address}")
            logger.debug(f"Connected to wallet address: {wallet_address}")
            
        except Exception as e:
            logger.error(f"Failed to create trading bot: {str(e)}")
            raise
            
    except Exception as e:
        st.error(f"Failed to initialize Trading Bot: {str(e)}")
        logger.exception("Bot initialization failed")
        st.stop()

def render_header():
    """Render dashboard header"""
    st.title("Solana Trading Bot Dashboard")
    st.markdown("Powered by Phantom Wallet & Jupiter DEX")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("""
        - Connected to: **{}**
        - RPC Endpoint: **{}**
        """.format(
            os.getenv('NETWORK', 'mainnet-beta'),
            os.getenv('RPC_URL', 'https://api.mainnet-beta.solana.com')
        ))
    
    with col2:
        if st.button("🔄 Refresh Data"):
            st.rerun()

async def render_wallet_info():
    """Render wallet information section."""
    try:
        st.subheader("📊 Wallet Information")
        
        # Get wallet info
        balance = await st.session_state.bot.get_balance()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("SOL Balance", f"{balance:.4f} SOL")
        with col2:
            st.metric("Connected Network", st.session_state.bot.config.network)
            
    except Exception as e:
        st.error(f"Error loading wallet info: {str(e)}")

def render_trading_settings():
    """Render trading settings section."""
    st.subheader("⚙️ Trading Settings")
    
    config = st.session_state.bot.config
    
    st.markdown(f"""
    - Base Currency: **{config.base_currency}**
    - Quote Currency: **{config.quote_currency}**
    - Position Size: **{config.position_size * 100}%** of available balance
    - Stop Loss: **{config.stop_loss * 100}%**
    - Take Profit: **{config.take_profit * 100}%**
    - Max Slippage: **{config.max_slippage * 100}%**
    - Max Positions: **{config.max_positions}**
    - Max Trades Per Day: **{config.max_trades_per_day}**
    """)

def render_active_trades():
    """Render active trades section"""
    st.subheader("Active Trades")
    
    if st.session_state.bot.active_trades:
        trades_df = pd.DataFrame.from_dict(
            st.session_state.bot.active_trades,
            orient='index'
        ).reset_index()
        
        trades_df.columns = ['Token', 'Entry Price', 'Amount', 'Stop Loss', 'Take Profit']
        st.dataframe(trades_df)
    else:
        st.info("No active trades")

def render_trade_history():
    """Render trade history section"""
    st.subheader("Trade History")
    st.info("Trade history will be implemented in a future update")

async def main():
    """Main dashboard function"""
    render_header()
    
    # Connect wallet button
    if st.button("Connect Phantom Wallet"):
        with st.spinner("Connecting to Phantom wallet..."):
            connected = await st.session_state.bot.wallet.connect()
            if connected:
                st.success("Successfully connected to Phantom wallet!")
            else:
                st.error("Failed to connect to Phantom wallet")
    
    # Main dashboard sections
    await render_wallet_info()
    render_trading_settings()
    render_active_trades()
    render_trade_history()
    
    # Start/Stop bot
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Trading Bot"):
            st.session_state.bot_running = True
            st.success("Trading bot started!")
            asyncio.create_task(st.session_state.bot.start())
    
    with col2:
        if st.button("Stop Trading Bot"):
            st.session_state.bot_running = False
            st.info("Trading bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
