"""
Market Scanner for monitoring all Solana tokens
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
import json
import time
from ..monitoring.logger import BotLogger

class MarketScanner:
    """Scans and analyzes all available tokens on Solana."""
    
    def __init__(self):
        """Initialize market scanner."""
        self.logger = BotLogger()
        self.token_list = {}  # Cache of token information
        self.token_metrics = {}  # Cache of token metrics
        self.last_scan = 0
        self.scan_interval = 300  # 5 minutes between full scans
        
    async def get_all_tokens(self) -> Dict:
        """Get list of all tokens from Jupiter and Solscan."""
        try:
            current_time = time.time()
            if current_time - self.last_scan < self.scan_interval and self.token_list:
                return self.token_list
                
            async with aiohttp.ClientSession() as session:
                # Get tokens from Jupiter
                async with session.get('https://token.jup.ag/all') as resp:
                    if resp.status == 200:
                        jupiter_data = await resp.json()
                        for token in jupiter_data:
                            self.token_list[token['address']] = {
                                'symbol': token.get('symbol', ''),
                                'name': token.get('name', ''),
                                'decimals': token.get('decimals', 9),
                                'tags': token.get('tags', []),
                                'coingecko_id': token.get('coingeckoId', '')
                            }
                
                # Get additional token info from Solscan
                async with session.get('https://api.solscan.io/v2/market/tokens') as resp:
                    if resp.status == 200:
                        solscan_data = await resp.json()
                        for token in solscan_data.get('data', []):
                            address = token.get('address')
                            if address:
                                self.token_list[address].update({
                                    'volume_24h': token.get('volume24h', 0),
                                    'price_change_24h': token.get('priceChange24h', 0),
                                    'market_cap': token.get('marketCap', 0),
                                    'holders': token.get('holder', 0)
                                })
            
            self.last_scan = current_time
            self.logger.info(f"Updated token list with {len(self.token_list)} tokens")
            return self.token_list
            
        except Exception as e:
            self.logger.error(f"Failed to get token list: {str(e)}")
            return self.token_list
    
    async def get_token_metrics(self, address: str) -> Dict:
        """Get detailed metrics for a specific token."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.solscan.io/v2/token/meta?address={address}') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            'liquidity': data.get('liquidityUSD', 0),
                            'volume_24h': data.get('volume24hUSD', 0),
                            'holders': data.get('holdersCount', 0),
                            'transactions_24h': data.get('txns24h', 0),
                            'price_change_24h': data.get('priceChange24h', 0)
                        }
            return {}
        except Exception as e:
            self.logger.error(f"Failed to get token metrics for {address}: {str(e)}")
            return {}
    
    async def analyze_market_opportunities(self) -> List[Dict]:
        """Analyze all tokens to find potential trading opportunities."""
        opportunities = []
        tokens = await self.get_all_tokens()
        
        for address, token in tokens.items():
            try:
                # Get detailed metrics
                metrics = await self.get_token_metrics(address)
                if not metrics:
                    continue
                
                # Calculate opportunity score based on various factors
                score = self._calculate_opportunity_score(token, metrics)
                
                if score > 0.7:  # Only include high-potential opportunities
                    opportunities.append({
                        'address': address,
                        'symbol': token['symbol'],
                        'name': token['name'],
                        'score': score,
                        'metrics': metrics,
                        'reason': self._get_opportunity_reason(token, metrics)
                    })
                    
            except Exception as e:
                self.logger.warning(f"Failed to analyze token {address}: {str(e)}")
                continue
        
        # Sort opportunities by score
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        return opportunities
    
    def _calculate_opportunity_score(self, token: Dict, metrics: Dict) -> float:
        """Calculate an opportunity score for a token."""
        score = 0.0
        
        # Liquidity factor (0-0.2)
        liquidity = metrics.get('liquidity', 0)
        if liquidity > 100000:  # Minimum $100k liquidity
            score += min(0.2, (liquidity / 1000000) * 0.2)  # Scale up to $1M
        
        # Volume factor (0-0.2)
        volume = metrics.get('volume_24h', 0)
        if volume > 10000:  # Minimum $10k daily volume
            score += min(0.2, (volume / 100000) * 0.2)  # Scale up to $100k
        
        # Price momentum (0-0.2)
        price_change = metrics.get('price_change_24h', 0)
        if price_change > 0:
            score += min(0.2, price_change * 0.01)  # 20% price increase = full score
        
        # Holder growth (0-0.2)
        holders = metrics.get('holders', 0)
        if holders > 100:  # Minimum 100 holders
            score += min(0.2, (holders / 1000) * 0.2)  # Scale up to 1000 holders
        
        # Transaction activity (0-0.2)
        transactions = metrics.get('transactions_24h', 0)
        if transactions > 100:  # Minimum 100 daily transactions
            score += min(0.2, (transactions / 1000) * 0.2)  # Scale up to 1000 transactions
        
        return score
    
    def _get_opportunity_reason(self, token: Dict, metrics: Dict) -> str:
        """Generate a reason for why this token is an opportunity."""
        reasons = []
        
        if metrics.get('price_change_24h', 0) > 10:
            reasons.append("Strong price momentum")
        
        if metrics.get('volume_24h', 0) > 100000:
            reasons.append("High trading volume")
        
        if metrics.get('transactions_24h', 0) > 500:
            reasons.append("Active trading")
        
        if metrics.get('holders', 0) > 500:
            reasons.append("Growing holder base")
        
        if metrics.get('liquidity', 0) > 500000:
            reasons.append("Good liquidity")
        
        return ", ".join(reasons) if reasons else "Multiple positive indicators"
