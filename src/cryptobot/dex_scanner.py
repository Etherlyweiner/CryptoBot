import aiohttp
import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DexScanner:
    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest/dex"
        self.session = None
        self.cache = {}
        self.cache_duration = timedelta(minutes=5)
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def get_trending_pairs(self, chain: str = "solana") -> List[Dict]:
        """Get trending pairs from DexScreener"""
        try:
            # Check cache first
            cache_key = f"trending_{chain}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                    return cached_data['data']
            
            session = await self.get_session()
            url = f"{self.base_url}/pairs/{chain}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"DexScreener API error: {response.status}")
                    return []
                    
                data = await response.json()
                pairs = data.get('pairs', [])
                
                # Filter and sort pairs
                filtered_pairs = self._filter_pairs(pairs)
                
                # Cache the results
                self.cache[cache_key] = {
                    'timestamp': datetime.now(),
                    'data': filtered_pairs
                }
                
                return filtered_pairs
                
        except Exception as e:
            logger.error(f"Error fetching trending pairs: {str(e)}")
            return []
            
    def _filter_pairs(self, pairs: List[Dict]) -> List[Dict]:
        """Filter and sort pairs based on criteria"""
        try:
            # Filter out pairs with low liquidity
            min_liquidity_usd = 10000  # $10k minimum liquidity
            filtered = [
                p for p in pairs
                if float(p.get('liquidity', {}).get('usd', 0)) > min_liquidity_usd
                and p.get('volume', {}).get('h24', 0) > 1000  # $1k minimum 24h volume
            ]
            
            # Sort by volume and price change
            sorted_pairs = sorted(
                filtered,
                key=lambda x: (
                    float(x.get('volume', {}).get('h24', 0)),  # Volume
                    float(x.get('priceChange', {}).get('h24', 0)),  # Price change
                    float(x.get('liquidity', {}).get('usd', 0))  # Liquidity
                ),
                reverse=True
            )
            
            return sorted_pairs[:20]  # Return top 20 pairs
            
        except Exception as e:
            logger.error(f"Error filtering pairs: {str(e)}")
            return []
            
    async def get_pair_info(self, token_address: str) -> Optional[Dict]:
        """Get detailed information about a specific pair"""
        try:
            session = await self.get_session()
            url = f"{self.base_url}/tokens/{token_address}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error fetching pair info: {response.status}")
                    return None
                    
                data = await response.json()
                pairs = data.get('pairs', [])
                
                if not pairs:
                    return None
                    
                # Get the most liquid pair
                best_pair = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)))
                
                return {
                    'price_usd': float(best_pair.get('priceUsd', 0)),
                    'price_change_24h': float(best_pair.get('priceChange', {}).get('h24', 0)),
                    'volume_24h': float(best_pair.get('volume', {}).get('h24', 0)),
                    'liquidity_usd': float(best_pair.get('liquidity', {}).get('usd', 0)),
                    'fdv': float(best_pair.get('fdv', 0)),
                    'pair_address': best_pair.get('pairAddress'),
                    'dex_id': best_pair.get('dexId'),
                    'url': best_pair.get('url')
                }
                
        except Exception as e:
            logger.error(f"Error fetching pair info: {str(e)}")
            return None
            
    async def analyze_momentum(self, token_address: str) -> Dict:
        """Analyze token momentum based on price and volume"""
        try:
            pair_info = await self.get_pair_info(token_address)
            if not pair_info:
                return {'score': 0, 'reason': 'No pair info available'}
                
            # Calculate momentum score
            price_change_weight = 0.4
            volume_weight = 0.3
            liquidity_weight = 0.3
            
            # Normalize metrics
            price_score = min(1.0, max(0, pair_info['price_change_24h'] / 100))
            volume_score = min(1.0, pair_info['volume_24h'] / 100000)  # Normalize to 100k volume
            liquidity_score = min(1.0, pair_info['liquidity_usd'] / 1000000)  # Normalize to 1M liquidity
            
            momentum_score = (
                price_score * price_change_weight +
                volume_score * volume_weight +
                liquidity_score * liquidity_weight
            )
            
            return {
                'score': momentum_score,
                'metrics': {
                    'price_change': pair_info['price_change_24h'],
                    'volume': pair_info['volume_24h'],
                    'liquidity': pair_info['liquidity_usd']
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing momentum: {str(e)}")
            return {'score': 0, 'reason': str(e)}
            
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
