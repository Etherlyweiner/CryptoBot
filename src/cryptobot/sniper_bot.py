import logging
import asyncio
from typing import Dict, List, Optional
import aiohttp
import time
from datetime import datetime, timedelta
from .token_scanner import TokenScanner
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)

class SniperBot:
    def __init__(self, config: Dict):
        self.config = config
        self.birdeye_api_key = config.get('birdeye_api_key')
        self.scanner = TokenScanner(config)
        self.risk_manager = RiskManager(config.get('risk_management', {}))
        self.min_liquidity = config.get('token_validation', {}).get('min_liquidity_usd', 50000)
        self.min_holders = config.get('token_validation', {}).get('min_holders', 100)
        self.min_volume = config.get('token_validation', {}).get('min_volume_24h', 10000)
        self.session = None
        self.headers = {
            'X-API-KEY': self.birdeye_api_key,
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        self.active_tokens = set()
        self.last_scan_time = time.time()
        
    async def __aenter__(self):
        await self._get_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session
        
    async def start(self):
        """Start the sniper bot"""
        try:
            logger.info("Starting Solana Sniper Bot...")
            while True:
                await self._scan_cycle()
                await asyncio.sleep(3)  # Scan every 3 seconds as shown in video
                
        except Exception as e:
            logger.error(f"Error in sniper bot: {str(e)}")
            
    async def _scan_cycle(self):
        """Perform a single scan cycle"""
        try:
            # Get new token launches
            new_tokens = await self.scanner.scan_new_tokens()
            
            # Filter and analyze tokens
            for token in new_tokens:
                if token['address'] not in self.active_tokens:
                    analysis = await self._analyze_token(token['address'])
                    if analysis['should_buy']:
                        await self._execute_snipe(token['address'], analysis)
                        self.active_tokens.add(token['address'])
                        
        except Exception as e:
            logger.error(f"Error in scan cycle: {str(e)}")
            
    async def _analyze_token(self, token_address: str) -> Dict:
        """Analyze a token for trading opportunity"""
        try:
            session = await self._get_session()
            
            # Get token info from Birdeye API
            birdeye_url = f"https://public-api.birdeye.so/public/token_info?address={token_address}"
            async with session.get(birdeye_url) as response:
                if response.status != 200:
                    return {
                        'should_buy': False,
                        'reason': f'Failed to fetch token info: {response.status}',
                        'market_cap': 0,
                        'liquidity': 0
                    }
                
                data = await response.json()
                if not data.get('success'):
                    return {
                        'should_buy': False,
                        'reason': 'Failed to get token data from Birdeye',
                        'market_cap': 0,
                        'liquidity': 0
                    }
                
                token_data = data.get('data', {})
                
                # Extract key metrics
                market_cap = float(token_data.get('mc', 0))
                liquidity = float(token_data.get('liquidity', 0))
                holder_count = int(token_data.get('holderCount', 0))
                volume_24h = float(token_data.get('volume24h', 0))
                
                # Basic validation
                if liquidity < self.min_liquidity:
                    return {
                        'should_buy': False,
                        'reason': f'Insufficient liquidity: ${liquidity:,.2f}',
                        'liquidity': liquidity,
                        'market_cap': market_cap
                    }
                
                if holder_count < self.min_holders:
                    return {
                        'should_buy': False,
                        'reason': f'Too few holders: {holder_count}',
                        'holder_count': holder_count,
                        'market_cap': market_cap,
                        'liquidity': liquidity
                    }
                
                if volume_24h < self.min_volume:
                    return {
                        'should_buy': False,
                        'reason': f'Low 24h volume: ${volume_24h:,.2f}',
                        'volume_24h': volume_24h,
                        'market_cap': market_cap,
                        'liquidity': liquidity
                    }
                
                # Check for potential rug pull indicators
                if liquidity > 0 and market_cap / liquidity > 50:
                    return {
                        'should_buy': False,
                        'reason': 'High market cap to liquidity ratio',
                        'mc_liq_ratio': market_cap / liquidity,
                        'market_cap': market_cap,
                        'liquidity': liquidity
                    }
                
                # If all checks pass, return positive analysis
                return {
                    'should_buy': True,
                    'market_cap': market_cap,
                    'liquidity': liquidity,
                    'holder_count': holder_count,
                    'volume_24h': volume_24h,
                    'mc_liq_ratio': market_cap / liquidity if liquidity > 0 else float('inf')
                }
                
        except Exception as e:
            logger.error(f"Error analyzing token: {str(e)}")
            return {
                'should_buy': False,
                'reason': str(e),
                'market_cap': 0,
                'liquidity': 0
            }

    async def _get_recent_trades(self, token_address: str) -> List[Dict]:
        """Get recent trades from BirdEye"""
        try:
            session = await self._get_session()
            url = f"https://public-api.birdeye.so/public/trade_history?address={token_address}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                    
                data = await response.json()
                return data.get('data', [])
                
        except Exception as e:
            logger.error(f"Error getting recent trades: {str(e)}")
            return []
            
    async def _check_rug_pull_signals(self, token_address: str, token_info: Dict) -> bool:
        """Check for potential rug pull signals"""
        try:
            # Check token contract
            if not token_info.get('decimals'):
                return True
                
            # Check ownership concentration
            if float(token_info.get('ownershipPercentage', 0)) > 50:
                return True
                
            # Check suspicious transfers
            transfers = await self._get_recent_transfers(token_address)
            if self._detect_suspicious_transfers(transfers):
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking rug pull signals: {str(e)}")
            return True
            
    def _calculate_buy_pressure(self, trades: List[Dict]) -> float:
        """Calculate buy pressure from recent trades"""
        if not trades:
            return 0
            
        buy_volume = sum(float(t['volume']) for t in trades if t.get('side') == 'buy')
        total_volume = sum(float(t['volume']) for t in trades)
        
        return buy_volume / total_volume if total_volume > 0 else 0
        
    def _calculate_entry_score(self, analysis: Dict) -> float:
        """Calculate entry score based on multiple factors"""
        try:
            # Weight factors
            weights = {
                'liquidity': 0.3,
                'holder_count': 0.2,
                'trade_count': 0.2,
                'buy_pressure': 0.3
            }
            
            # Normalize metrics
            liquidity_score = min(1.0, analysis['liquidity'] / 100000)
            holder_score = min(1.0, analysis['holder_count'] / 1000)
            trade_score = min(1.0, analysis['trade_count'] / 100)
            
            # Calculate weighted score
            score = (
                liquidity_score * weights['liquidity'] +
                holder_score * weights['holder_count'] +
                trade_score * weights['trade_count'] +
                analysis['buy_pressure'] * weights['buy_pressure']
            )
            
            return round(score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating entry score: {str(e)}")
            return 0
            
    def _calculate_position_size(self, analysis: Dict) -> float:
        """Calculate position size based on risk parameters"""
        try:
            # Base size on liquidity
            max_size = min(
                analysis['liquidity'] * 0.01,  # 1% of liquidity
                self.config.get('max_position_size', 1.0)
            )
            
            # Adjust based on entry score
            score_factor = analysis['entry_score']
            
            # Calculate final size
            position_size = max_size * score_factor
            
            return round(position_size, 3)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0
            
    async def _execute_snipe(self, token_address: str, analysis: Dict):
        """Execute snipe trade"""
        try:
            logger.info(f"Executing snipe for token {token_address}")
            logger.info(f"Analysis: {analysis}")
            
            # Implement actual trade execution here
            # This would connect to your preferred DEX (Jupiter, Raydium, etc.)
            
        except Exception as e:
            logger.error(f"Error executing snipe: {str(e)}")
            
    async def close(self):
        """Close the bot and cleanup"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        await self.scanner.close()
