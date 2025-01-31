import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import aiohttp
import asyncio
from config import *
import json
import telegram
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskMonitor:
    def __init__(self):
        self.last_notification = {}
        self.bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def start(self):
        """Initialize the aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self
    
    async def stop(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def check_dex_screener(self, token_address):
        """Check DEX Screener for token information using API"""
        try:
            if not self.session:
                await self.start()
                
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            async with self.session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                data = await response.json()
                
                if 'pairs' in data and len(data['pairs']) > 0:
                    pair = data['pairs'][0]  # Get the most liquid pair
                    return {
                        "price": float(pair.get('priceUsd', 0)),
                        "volume_24h": float(pair.get('volume24h', 0)),
                        "liquidity": float(pair.get('liquidity', 0))
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error checking DEX Screener: {str(e)}")
            return None

    async def check_pump_signals(self):
        """Check various sources for pump signals using API endpoints"""
        signals = []
        try:
            if not self.session:
                await self.start()
                
            # Check CoinGecko trending
            url = "https://api.coingecko.com/api/v3/search/trending"
            async with self.session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                data = await response.json()
                
                if 'coins' in data:
                    for coin in data['coins'][:5]:  # Top 5 trending
                        signals.append({
                            'source': 'CoinGecko Trending',
                            'symbol': coin['item']['symbol'].upper(),
                            'name': coin['item']['name'],
                            'score': coin['item'].get('score', 0)
                        })
            
        except Exception as e:
            logger.error(f"Error checking pump signals: {str(e)}")
        
        return signals

    def calculate_risk_score(self, metrics, signals):
        """Calculate a risk score based on various metrics"""
        try:
            # Base score starts at 0.5
            score = 0.5
            
            # Adjust based on liquidity
            if metrics.get('liquidity', 0) > LIQUIDITY_THRESHOLD:
                score += 0.1
            
            # Adjust based on volume
            if metrics.get('volume_24h', 0) > VOLUME_SPIKE_THRESHOLD:
                score += 0.1
            
            # Adjust based on price stability
            if metrics.get('price_change_24h', 0) < 0.2:  # Less than 20% change
                score += 0.1
            
            # Adjust based on signals
            if len(signals) > 0:
                score += 0.1 * min(len(signals), 3)  # Max bonus of 0.3 from signals
            
            return min(score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 0.0

    async def check_token_metrics(self, token_address):
        """Get comprehensive token metrics from various APIs"""
        metrics = {}
        
        # Get DEX Screener data
        dex_data = await self.check_dex_screener(token_address)
        if dex_data:
            metrics.update(dex_data)
            
        return metrics

    async def monitor_token(self, token_address):
        """Monitor a token's metrics and send alerts if necessary"""
        try:
            metrics = await self.check_token_metrics(token_address)
            
            if not metrics:
                return
            
            # Check for significant changes
            alerts = []
            
            # Price change alert
            if token_address in self.last_notification:
                last_price = self.last_notification[token_address].get('price', 0)
                if last_price > 0:
                    price_change = ((metrics['price'] - last_price) / last_price) * 100
                    if abs(price_change) >= PRICE_CHANGE_THRESHOLD:
                        alerts.append(f"Price {'increased' if price_change > 0 else 'decreased'} by {abs(price_change):.2f}%")
            
            # Volume spike alert
            if metrics['volume_24h'] > VOLUME_THRESHOLD:
                alerts.append(f"High 24h volume: ${metrics['volume_24h']:,.2f}")
            
            # Liquidity change alert
            if token_address in self.last_notification:
                last_liquidity = self.last_notification[token_address].get('liquidity', 0)
                if last_liquidity > 0:
                    liq_change = ((metrics['liquidity'] - last_liquidity) / last_liquidity) * 100
                    if abs(liq_change) >= LIQUIDITY_CHANGE_THRESHOLD:
                        alerts.append(f"Liquidity {'increased' if liq_change > 0 else 'decreased'} by {abs(liq_change):.2f}%")
            
            # Send alerts if any
            if alerts and TELEGRAM_ALERTS_ENABLED:
                message = f"🚨 Alert for {token_address}:\n" + "\n".join(f"• {alert}" for alert in alerts)
                await self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            
            # Update last notification data
            self.last_notification[token_address] = metrics
            
        except Exception as e:
            logger.error(f"Error monitoring token {token_address}: {str(e)}")

    async def run(self, token_addresses):
        """Main monitoring loop"""
        try:
            await self.start()
            
            while True:
                try:
                    for address in token_addresses:
                        await self.monitor_token(address)
                    
                    # Check for pump signals
                    signals = await self.check_pump_signals()
                    if signals and TELEGRAM_ALERTS_ENABLED:
                        message = "🔥 Trending Tokens:\n" + "\n".join(
                            f"• {signal['name']} ({signal['symbol']}) - {signal['source']}"
                            for signal in signals
                        )
                        await self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {str(e)}")
                
                await asyncio.sleep(MONITORING_INTERVAL)
                
        finally:
            await self.stop()
