import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import aiohttp
import asyncio
from config import *
import json
import telegram
import logging

class RiskMonitor:
    def __init__(self):
        self.last_notification = {}
        self.bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    async def check_dex_screener(self, token_address):
        """Check DEX Screener for token information using API"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if 'pairs' in data and len(data['pairs']) > 0:
                pair = data['pairs'][0]  # Get the most liquid pair
                return {
                    "price": float(pair.get('priceUsd', 0)),
                    "volume_24h": float(pair.get('volume24h', 0)),
                    "liquidity": float(pair.get('liquidity', 0))
                }
            return None
            
        except Exception as e:
            logging.error(f"Error checking DEX Screener: {str(e)}")
            return None

    async def check_pump_signals(self):
        """Check various sources for pump signals using API endpoints"""
        signals = []
        try:
            # Example: Check CoinGecko trending
            url = "https://api.coingecko.com/api/v3/search/trending"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            for coin in data.get('coins', []):
                signals.append({
                    'symbol': coin['item']['symbol'],
                    'score': coin['item']['score']
                })
                
        except Exception as e:
            logging.error(f"Error checking pump signals: {str(e)}")
        return signals

    async def send_notification(self, message):
        """Send notification via Telegram"""
        try:
            current_time = datetime.now()
            if (message not in self.last_notification or 
                (current_time - self.last_notification[message]).total_seconds() > NOTIFICATION_COOLDOWN):
                await self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                self.last_notification[message] = current_time
        except Exception as e:
            logging.error(f"Error sending notification: {str(e)}")

    async def analyze_risk(self, token_data):
        """Analyze risk based on various factors"""
        try:
            if not token_data:
                return 1.0  # Maximum risk if no data available
                
            risk_score = 0.0
            
            # Volume analysis
            if token_data['volume_24h'] > 0:
                volume_ratio = token_data['volume_24h'] / token_data['liquidity']
                if volume_ratio > VOLUME_SPIKE_THRESHOLD:
                    risk_score += 0.3
                    await self.send_notification(f"⚠️ High volume detected! Volume/Liquidity ratio: {volume_ratio:.2f}")
            
            # Liquidity check
            if token_data['liquidity'] < LIQUIDITY_THRESHOLD:
                risk_score += 0.3
                await self.send_notification(f"⚠️ Low liquidity warning! Current liquidity: ${token_data['liquidity']:,.2f}")
            
            # Price impact
            price_impact = 1000 / token_data['liquidity']  # Simplified calculation
            if price_impact > MAX_PRICE_IMPACT:
                risk_score += 0.4
                await self.send_notification(f"⚠️ High price impact warning! Estimated impact: {price_impact:.2%}")
            
            return risk_score
        except Exception as e:
            logging.error(f"Error analyzing risk: {str(e)}")
            return 1.0  # Return maximum risk score on error

    async def monitor_new_launches(self):
        """Monitor for new token launches"""
        try:
            # Monitor DEX Screener for new listings
            url = "https://api.dexscreener.com/latest/dex/tokens/new"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            for token in data.get('tokens', []):
                token_data = {
                    "address": token.get('id'),
                    "name": token.get('name'),
                    "time": token.get('time')
                }
                
                # Get detailed token data
                details = await self.check_dex_screener(token_data["address"])
                if details:
                    token_data.update(details)
                    
                    # Analyze risk
                    risk_score = await self.analyze_risk(token_data)
                    
                    if risk_score >= RISK_SCORE_THRESHOLD:
                        notification = (
                            f"🚀 *New Token Launch Alert*\n"
                            f"Name: {token_data['name']}\n"
                            f"Address: `{token_data['address']}`\n"
                            f"Price: ${token_data['price']:.6f}\n"
                            f"Liquidity: ${token_data['liquidity']:,.2f}\n"
                            f"Risk Score: {risk_score:.2f}\n"
                            f"Time: {token_data['time']}"
                        )
                        await self.send_notification(notification)
                        
        except Exception as e:
            logging.error(f"Error monitoring new launches: {str(e)}")
