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
        st.session_state.bot = TradingBot()
    except Exception as e:
        st.error(f"Failed to initialize Trading Bot: {str(e)}")
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
    """Render wallet information section"""
    st.subheader("Wallet Information")
    
    try:
        col1, col2 = st.columns(2)
        
        with col1:
            sol_balance = await st.session_state.bot.wallet.get_balance()
            st.metric(
                "SOL Balance",
                f"{sol_balance:.4f} SOL",
                help="Your current SOL balance"
            )
        
        with col2:
            portfolio_value = await st.session_state.bot.get_portfolio_value()
            st.metric(
                "Portfolio Value",
                f"{portfolio_value:.4f} SOL",
                help="Total portfolio value in SOL"
            )
        
        # Token accounts
        st.subheader("Token Accounts")
        token_accounts = await st.session_state.bot.wallet.get_token_accounts()
        
        if token_accounts:
            df = pd.DataFrame(token_accounts)
            df['amount'] = pd.to_numeric(df['amount'])
            df['value'] = df['amount'] / (10 ** df['decimals'])
            st.dataframe(
                df[['mint', 'value', 'decimals']].rename(columns={
                    'mint': 'Token',
                    'value': 'Balance',
                    'decimals': 'Decimals'
                })
            )
        else:
            st.info("No token accounts found")
            
    except Exception as e:
        st.error(f"Error loading wallet info: {str(e)}")

def render_trading_settings():
    """Render trading settings section"""
    st.subheader("Trading Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Position Settings")
        st.markdown(f"""
        - Max Trades: **{st.session_state.bot.max_trades}**
        - Position Size: **{st.session_state.bot.position_size * 100}%**
        - Stop Loss: **{st.session_state.bot.stop_loss_percent}%**
        - Take Profit: **{st.session_state.bot.take_profit_percent}%**
        """)
    
    with col2:
        st.markdown("### Technical Analysis")
        st.markdown(f"""
        - RSI Period: **{st.session_state.bot.rsi_period}**
        - RSI Overbought: **{st.session_state.bot.rsi_overbought}**
        - RSI Oversold: **{st.session_state.bot.rsi_oversold}**
        - EMA Fast: **{st.session_state.bot.ema_fast}**
        - EMA Slow: **{st.session_state.bot.ema_slow}**
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
