"""
CryptoBot Dashboard Application
"""

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from bot import TradingBot
from dotenv import load_dotenv
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Solana Trading Bot",
    page_icon="",
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
        
        # Initialize with wallet address
        success, message = wallet_manager.initialize_with_address("8jqv2AKPGYwojLRHQZLokkYdtHycs8HAVGDMqZUvTByB")
        if not success:
            logger.error(f"Failed to initialize wallet: {message}")
            raise RuntimeError(f"Failed to initialize wallet: {message}")
        
        logger.debug("Wallet initialized successfully")
        
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
        
        # Initialize trading bot
        st.session_state.bot = TradingBot(wallet=wallet_manager, config=config)
        logger.debug("Created trading bot instance")
        
        # Show wallet address
        wallet_address = wallet_manager.pubkey
        st.sidebar.success(f"Connected to wallet: {wallet_address}")
        logger.debug(f"Connected to wallet address: {wallet_address}")
            
    except Exception as e:
        logger.error(f"Failed during wallet/bot initialization: {str(e)}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Failed to initialize Trading Bot: {str(e)}")
            
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
        if st.button(" Refresh Data"):
            st.experimental_rerun()

def render_wallet_info():
    """Render wallet information section."""
    try:
        st.subheader("📊 Wallet Information")
        
        # Get wallet info
        wallet = st.session_state.bot.wallet
        balance = wallet.get_balance()
        token_balances = wallet.get_token_balances()
        
        # Create columns for wallet info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="SOL Balance",
                value=f"{balance:.4f} SOL",
                delta=None
            )
            
            # Add Solscan link
            explorer_url = wallet.get_explorer_url()
            st.markdown(f"[View on Solscan]({explorer_url})")
        
        with col2:
            # Show token balances
            st.markdown("**Token Balances**")
            if token_balances:
                for symbol, amount in token_balances.items():
                    st.write(f"{symbol}: {amount:.4f}")
            else:
                st.write("No tokens found")
        
        with col3:
            if st.button("🔄 Refresh Balance"):
                st.experimental_rerun()
                
    except Exception as e:
        logger.error(f"Error loading wallet info: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Error loading wallet info: {str(e)}")

def render_trading_settings():
    """Render trading settings section."""
    st.subheader(" Trading Settings")
    
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
    """Render active trades section."""
    st.subheader("Active Trades")
    
    try:
        active_trades = st.session_state.bot.get_active_trades()
        if active_trades:
            # Create a DataFrame for better display
            trades_data = []
            for trade in active_trades:
                trades_data.append({
                    'Symbol': trade.symbol,
                    'Side': trade.side.upper(),
                    'Entry Price': f"${trade.entry_price:.4f}",
                    'Quantity': f"{trade.quantity:.4f}",
                    'Stop Loss': f"${trade.stop_loss:.4f}",
                    'Take Profit': f"${trade.take_profit:.4f}",
                    'Time': trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            if trades_data:
                st.dataframe(pd.DataFrame(trades_data))
            else:
                st.info("No active trades")
        else:
            st.info("No active trades")
            
    except Exception as e:
        logger.error(f"Error loading active trades: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Error loading active trades: {str(e)}")

def render_trade_history():
    """Render trade history section."""
    st.subheader("Trade History")
    
    try:
        trade_history = st.session_state.bot.get_trade_history()
        if trade_history:
            # Create a DataFrame for better display
            history_data = []
            for trade in trade_history:
                history_data.append({
                    'Symbol': trade.symbol,
                    'Side': trade.side.upper(),
                    'Entry Price': f"${trade.entry_price:.4f}",
                    'Quantity': f"{trade.quantity:.4f}",
                    'Status': trade.status.upper(),
                    'Time': trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            if history_data:
                st.dataframe(pd.DataFrame(history_data))
            else:
                st.info("No trade history")
        else:
            st.info("No trade history")
            
    except Exception as e:
        logger.error(f"Error loading trade history: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Error loading trade history: {str(e)}")

def render_trading_stats():
    """Render trading statistics."""
    st.subheader("Trading Statistics")
    
    try:
        stats = st.session_state.bot.get_trading_stats()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Trades", stats['total_trades'])
            st.metric("Active Trades", stats['active_trades'])
            
        with col2:
            st.metric("Closed Trades", stats['closed_trades'])
            st.metric("Cancelled Trades", stats['cancelled_trades'])
            
        with col3:
            st.metric("Trades Today", stats['trades_today'])
            
    except Exception as e:
        logger.error(f"Error loading trading stats: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Error loading trading stats: {str(e)}")

def initialize_bot():
    """Initialize the trading bot."""
    try:
        from bot.trading_bot import TradingConfig
        from bot.wallet.phantom_integration import PhantomWalletManager
        
        logger.debug("Starting bot initialization...")
        
        # Initialize Phantom Wallet
        wallet_manager = PhantomWalletManager()
        logger.debug("Created wallet manager")
        
        # Initialize with wallet address
        success, message = wallet_manager.initialize_with_address("8jqv2AKPGYwojLRHQZLokkYdtHycs8HAVGDMqZUvTByB")
        if not success:
            logger.error(f"Failed to initialize wallet: {message}")
            return False, f"Failed to initialize wallet: {message}"
        
        logger.debug("Wallet initialized successfully")
        
        # Create trading config
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
        
        # Initialize trading bot
        st.session_state.bot = TradingBot(wallet=wallet_manager, config=config)
        logger.debug("Created trading bot instance")
        return True, "Bot initialized successfully"
        
    except Exception as e:
        error_msg = f"Failed to initialize Trading Bot: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, error_msg

def main():
    """Main dashboard function"""
    render_header()
    
    # Initialize bot if not already done
    if 'bot' not in st.session_state:
        success, message = initialize_bot()
        if not success:
            st.error(message)
            st.stop()
    
    # Wallet connection status
    wallet = st.session_state.bot.wallet
    if wallet.is_connected():
        wallet_address = str(wallet.pubkey)
        st.sidebar.success(f"Connected to wallet: {wallet_address}")
        
        # Add Solscan link
        explorer_url = wallet.get_explorer_url()
        st.sidebar.markdown(f"[View on Solscan]({explorer_url})")
    else:
        st.sidebar.warning("Wallet not connected")
    
    # Wallet connection button
    if not wallet.is_connected():
        if st.button("Connect Phantom Wallet"):
            with st.spinner("Connecting to Phantom wallet..."):
                try:
                    success, message = wallet.connect()
                    if success:
                        wallet_address = str(wallet.pubkey)
                        st.sidebar.success(f"Connected to wallet: {wallet_address}")
                        st.experimental_rerun()
                    else:
                        st.error(f"Failed to connect: {message}")
                except Exception as e:
                    logger.error(f"Wallet connection error: {str(e)}")
                    logger.error(traceback.format_exc())
                    st.error(f"Connection error: {str(e)}")
    
    # Main dashboard sections
    if wallet.is_connected():
        render_wallet_info()
        render_trading_settings()
        render_active_trades()
        render_trade_history()
        render_trading_stats()
        
        # Start/Stop bot
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Start Trading Bot"):
                st.session_state.bot_running = True
                st.success("Trading bot started!")
                st.session_state.bot.start()
        
        with col2:
            if st.button("Stop Trading Bot"):
                st.session_state.bot_running = False
                st.session_state.bot.stop()
                st.info("Trading bot stopped")
    else:
        st.warning("Please connect your Phantom wallet to access the trading dashboard.")

if __name__ == "__main__":
    main()
