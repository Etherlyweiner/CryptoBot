"""Market monitoring module for tracking token prices and generating trading signals."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import aiohttp
import requests

logger = logging.getLogger(__name__)

class MarketMonitor:
    """Monitors market data for trading opportunities and generates signals.
    
    This class handles market data collection, analysis, and alert generation
    for potential trading opportunities in the Solana ecosystem.
    """
    
    DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"
    BIRDEYE_API = "https://public-api.birdeye.so/public"
    
    def __init__(self, pair_address: str, birdeye_api_key: str):
        """Initialize the market monitor.
        
        Args:
            pair_address: The DEX pair address to monitor
            birdeye_api_key: API key for Birdeye API access
        """
        self.pair_address = pair_address
        self.headers = {
            'X-API-KEY': birdeye_api_key,
            'Accept': 'application/json'
        }
        
    async def get_token_metadata(self, token_address: str) -> Dict[str, Any]:
        """Fetch token metadata from Birdeye API.
        
        Args:
            token_address: The token address to fetch metadata for
            
        Returns:
            Dict containing token metadata or empty dict on error
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BIRDEYE_API}/token_metadata/{token_address}"
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("Successfully fetched token metadata for %s", token_address)
                        return data
                    logger.error("Failed to fetch token metadata: %s", await response.text())
                    return {}
        except Exception as e:
            logger.error("Error fetching token metadata: %s", str(e))
            return {}

    def fetch_market_data(self) -> Dict[str, Any]:
        """Fetch market data from DexScreener API.
        
        Returns:
            Dict containing market data or empty dict on error
        """
        try:
            response = requests.get(
                f"{self.DEXSCREENER_API}/pairs/solana/{self.pair_address}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            logger.info("Successfully fetched market data for pair %s", self.pair_address)
            return response.json()
        except requests.RequestException as e:
            logger.error("Failed to fetch market data: %s", str(e))
            return {}

    async def get_price_impact(self, token_address: str, amount_usd: float) -> Dict[str, Any]:
        """Calculate price impact for a given trade amount.
        
        Args:
            token_address: The token address to check
            amount_usd: The trade amount in USD
            
        Returns:
            Dict containing price impact data or empty dict on error
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BIRDEYE_API}/price_impact/{token_address}"
                params = {'amount': str(amount_usd)}
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("Successfully calculated price impact for %s", token_address)
                        return data
                    logger.error("Failed to get price impact: %s", await response.text())
                    return {}
        except Exception as e:
            logger.error("Error calculating price impact: %s", str(e))
            return {}

    def analyze_token(self, token_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze token data for trading signals.
        
        Args:
            token_data: Dict containing token market data
            
        Returns:
            Dict containing analysis results
        """
        try:
            # Extract relevant metrics
            price = float(token_data.get('priceUsd', 0))
            volume_24h = float(token_data.get('volume24h', 0))
            liquidity_usd = float(token_data.get('liquidityUsd', 0))
            price_change_24h = float(token_data.get('priceChange24h', 0))
            
            # Calculate metrics
            volume_to_liquidity = volume_24h / liquidity_usd if liquidity_usd > 0 else 0
            momentum_score = price_change_24h * volume_to_liquidity
            liquidity_score = min(1.0, liquidity_usd / 1000000)  # Normalize to 1M USD
            opportunity_score = momentum_score * liquidity_score
            
            return {
                'price': price,
                'volume_24h': volume_24h,
                'liquidity_usd': liquidity_usd,
                'price_change_24h': price_change_24h,
                'volume_to_liquidity': volume_to_liquidity,
                'momentum_score': momentum_score,
                'liquidity_score': liquidity_score,
                'opportunity_score': opportunity_score
            }
        except Exception as e:
            logger.error("Error analyzing token data: %s", str(e))
            return {}

    def generate_alerts(self, token_data: Dict[str, Any], analysis: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate alerts based on token analysis.
        
        Args:
            token_data: Dict containing token market data
            analysis: Dict containing analysis results
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        try:
            # Price movement alerts
            if analysis['price_change_24h'] > 10:
                alerts.append({
                    'type': 'PRICE_SURGE',
                    'message': f"Price surged {analysis['price_change_24h']}% in 24h",
                    'severity': 'high',
                    'timestamp': datetime.now().isoformat()
                })
            elif analysis['price_change_24h'] < -10:
                alerts.append({
                    'type': 'PRICE_DROP',
                    'message': f"Price dropped {abs(analysis['price_change_24h'])}% in 24h",
                    'severity': 'high',
                    'timestamp': datetime.now().isoformat()
                })
                
            # Volume alerts
            if analysis['volume_to_liquidity'] > 2:
                alerts.append({
                    'type': 'HIGH_VOLUME',
                    'message': f"High volume relative to liquidity: {analysis['volume_to_liquidity']:.2f}x",
                    'severity': 'medium',
                    'timestamp': datetime.now().isoformat()
                })
                
            # Opportunity score alerts
            if analysis['opportunity_score'] > 0.5:
                alerts.append({
                    'type': 'TRADING_OPPORTUNITY',
                    'message': f"High opportunity score: {analysis['opportunity_score']:.2f}",
                    'severity': 'high',
                    'timestamp': datetime.now().isoformat()
                })
                
            return alerts
        except Exception as e:
            logger.error("Error generating alerts: %s", str(e))
            return []
