"""
Market monitoring module for tracking new coin launches and market data
"""

import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
from database import Database, NewToken
from logging_config import get_logger

logger = get_logger('MarketMonitor')

class MarketMonitor:
    def __init__(self, db: Database):
        """Initialize market monitor"""
        self.db = db
        self.session = None
        self.sources = {
            'pump_fun': 'https://pump.fun/board',
            'dexscreener_solana': 'https://api.dexscreener.com/latest/dex/tokens/solana/',
        }

    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_pump_fun_data(self) -> List[Dict[str, Any]]:
        """Fetch data from pump.fun"""
        try:
            await self.init_session()
            async with self.session.get(self.sources['pump_fun']) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch pump.fun data: {response.status}")
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                tokens = []
                # Parse the board data
                board_items = soup.find_all('div', class_='board-item')
                for item in board_items:
                    try:
                        token_data = {
                            'source': 'pump_fun',
                            'timestamp': datetime.utcnow(),
                            'symbol': item.find('div', class_='token-symbol').text.strip(),
                            'name': item.find('div', class_='token-name').text.strip(),
                            'chain': item.find('div', class_='chain').text.strip(),
                            'launch_date': datetime.strptime(
                                item.find('div', class_='launch-date').text.strip(),
                                '%Y-%m-%d %H:%M:%S'
                            ),
                            'description': item.find('div', class_='description').text.strip(),
                            'website': item.find('a', class_='website-link')['href'],
                            'social_links': {
                                'telegram': item.find('a', class_='telegram-link')['href'],
                                'twitter': item.find('a', class_='twitter-link')['href']
                            }
                        }
                        tokens.append(token_data)
                    except Exception as e:
                        logger.error(f"Error parsing pump.fun token data: {str(e)}")
                        continue

                return tokens

        except Exception as e:
            logger.error(f"Error fetching pump.fun data: {str(e)}")
            return []

    async def fetch_dexscreener_data(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Fetch data from DexScreener"""
        try:
            await self.init_session()
            url = f"{self.sources['dexscreener_solana']}{token_address}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch DexScreener data: {response.status}")
                    return None

                data = await response.json()
                if not data.get('pairs'):
                    return None

                pair = data['pairs'][0]  # Get the first trading pair
                return {
                    'source': 'dexscreener',
                    'timestamp': datetime.utcnow(),
                    'symbol': pair['baseToken']['symbol'],
                    'name': pair['baseToken']['name'],
                    'chain': 'Solana',
                    'contract_address': token_address,
                    'initial_price': float(pair['priceUsd']),
                    'initial_market_cap': float(pair['fdv']),
                    'social_links': {
                        'website': pair.get('url'),
                        'telegram': pair.get('telegram'),
                        'twitter': pair.get('twitter')
                    }
                }

        except Exception as e:
            logger.error(f"Error fetching DexScreener data: {str(e)}")
            return None

    async def monitor_markets(self):
        """Monitor markets for new tokens and updates"""
        try:
            # Fetch data from pump.fun
            pump_fun_tokens = await self.fetch_pump_fun_data()
            for token in pump_fun_tokens:
                self.db.store_new_token(token)
                logger.info(f"Stored new token from pump.fun: {token['symbol']}")

            # Fetch data from DexScreener for the specified token
            dex_token = await self.fetch_dexscreener_data(
                "9ctxeyrstwtklfvts6c7rfqc7ptxy42ypdqcrhtv53ao"
            )
            if dex_token:
                self.db.store_new_token(dex_token)
                logger.info(f"Stored new token from DexScreener: {dex_token['symbol']}")

        except Exception as e:
            logger.error(f"Error in market monitoring: {str(e)}")

    def analyze_token(self, token_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze token data and generate scores"""
        try:
            # Initial momentum score based on price and volume
            momentum_score = 0.0
            if token_data.get('initial_price') and token_data.get('initial_market_cap'):
                # Add your momentum calculation logic here
                pass

            # Social score based on social media presence
            social_score = 0.0
            if token_data.get('social_links'):
                social_links = token_data['social_links']
                social_score += 0.3 if social_links.get('website') else 0
                social_score += 0.4 if social_links.get('telegram') else 0
                social_score += 0.3 if social_links.get('twitter') else 0

            # Risk score based on various factors
            risk_score = 0.0
            # Add your risk calculation logic here

            # Overall opportunity score
            opportunity_score = (
                0.4 * momentum_score +
                0.3 * social_score +
                0.3 * (1 - risk_score)  # Inverse of risk score
            )

            return {
                'momentum_score': momentum_score,
                'social_score': social_score,
                'risk_score': risk_score,
                'opportunity_score': opportunity_score
            }

    def generate_alerts(self, token_data: Dict[str, Any], analysis: Dict[str, float]):
        """Generate alerts based on token analysis"""
        alerts = []

        # High opportunity score alert
        if analysis['opportunity_score'] >= 0.8:
            alerts.append({
                'timestamp': datetime.utcnow(),
                'symbol': token_data['symbol'],
                'name': token_data['name'],
                'opportunity_score': analysis['opportunity_score'],
                'momentum_score': analysis['momentum_score'],
                'social_score': analysis['social_score'],
                'risk_score': analysis['risk_score'],
                'alert_message': f"High opportunity token detected: {token_data['symbol']}"
            })

        # Strong momentum alert
        if analysis['momentum_score'] >= 0.8:
            alerts.append({
                'timestamp': datetime.utcnow(),
                'symbol': token_data['symbol'],
                'name': token_data['name'],
                'opportunity_score': analysis['opportunity_score'],
                'momentum_score': analysis['momentum_score'],
                'social_score': analysis['social_score'],
                'risk_score': analysis['risk_score'],
                'alert_message': f"Strong momentum detected: {token_data['symbol']}"
            })

        return alerts

    async def run_monitoring_loop(self):
        """Run continuous market monitoring"""
        try:
            while True:
                await self.monitor_markets()
                # Sleep for 5 minutes before next check
                await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Error in monitoring loop: {str(e)}")
        finally:
            await self.close_session()
