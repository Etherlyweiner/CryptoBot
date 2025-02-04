"""SniperBot class for quickly capitalizing on new token opportunities"""
import logging
import asyncio
from typing import Dict, Optional, List
import aiohttp
from datetime import datetime, timedelta

from .token_scanner import TokenScanner
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)

class SniperBot:
    def __init__(self, config: Dict):
        """Initialize SniperBot with configuration"""
        self.config = config
        self.scanner = TokenScanner(config)
        self.risk_manager = RiskManager(config.get('risk_management', {}))
        self.min_liquidity = config.get('token_validation', {}).get('min_liquidity_usd', 50000)
        self.min_holders = config.get('token_validation', {}).get('min_holders', 100)
        self.min_volume = config.get('token_validation', {}).get('min_volume_24h', 10000)
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Origin': 'https://birdeye.so',
            'Referer': 'https://birdeye.so/'
        }
        if config.get('birdeye', {}).get('api_key'):
            api_key = config['birdeye']['api_key']
            if not api_key.startswith('Bearer '):
                api_key = f"Bearer {api_key}"
            self.headers['Authorization'] = api_key
        
    async def __aenter__(self):
        """Async context manager enter"""
        await self._get_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session

    async def _retry_request(self, url: str, method: str = 'GET', data: Dict = None, max_retries: int = 3, delay: float = 2.0) -> Optional[Dict]:
        """Make a request with retry logic"""
        session = await self._get_session()
        
        for attempt in range(max_retries):
            try:
                # Add delay between requests to avoid rate limiting
                if attempt > 0:
                    await asyncio.sleep(delay * (attempt + 1))
                
                if method == 'GET':
                    async with session.get(url) as response:
                        if response.status == 429:  # Rate limit
                            wait_time = float(response.headers.get('Retry-After', delay * 2))
                            logger.warning(f"Rate limited, waiting {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                            
                        if response.status == 521 or response.status == 403:  # Cloudflare error
                            logger.warning(f"Cloudflare error (status {response.status}), retrying...")
                            await asyncio.sleep(delay * (attempt + 2))
                            continue
                            
                        if response.status != 200:
                            logger.error(f"Request failed with status {response.status}")
                            return None
                            
                        try:
                            return await response.json()
                        except Exception as e:
                            logger.error(f"Failed to parse JSON response: {str(e)}")
                            return None
                            
                else:  # POST
                    async with session.post(url, json=data) as response:
                        if response.status == 429:  # Rate limit
                            wait_time = float(response.headers.get('Retry-After', delay * 2))
                            logger.warning(f"Rate limited, waiting {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                            
                        if response.status == 521 or response.status == 403:  # Cloudflare error
                            logger.warning(f"Cloudflare error (status {response.status}), retrying...")
                            await asyncio.sleep(delay * (attempt + 2))
                            continue
                            
                        if response.status != 200:
                            logger.error(f"Request failed with status {response.status}")
                            return None
                            
                        try:
                            return await response.json()
                        except Exception as e:
                            logger.error(f"Failed to parse JSON response: {str(e)}")
                            return None
                    
            except aiohttp.ClientError as e:
                logger.error(f"Request error: {str(e)}")
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(delay * (attempt + 1))
        
        return None

    async def _analyze_token(self, token_address: str) -> Dict:
        """Analyze a token for trading opportunity"""
        try:
            # Get token info from Birdeye API
            token_info_url = f"https://public-api.birdeye.so/defi/v2/token/info?address={token_address}&network=solana"
            token_data = await self._retry_request(token_info_url)
            
            if not token_data or not token_data.get('success'):
                return {
                    'should_buy': False,
                    'reason': 'Failed to get token data from Birdeye',
                    'market_cap': 0,
                    'liquidity': 0
                }
            
            token_info = token_data.get('data', {})
            if not token_info:
                return {
                    'should_buy': False,
                    'reason': 'No token data available',
                    'market_cap': 0,
                    'liquidity': 0
                }
            
            # Get price and liquidity data
            price_url = f"https://public-api.birdeye.so/defi/v2/token/price?address={token_address}&network=solana"
            price_data = await self._retry_request(price_url)
            
            if not price_data or not price_data.get('success'):
                return {
                    'should_buy': False,
                    'reason': 'Failed to get price data from Birdeye',
                    'market_cap': 0,
                    'liquidity': 0
                }
            
            price_info = price_data.get('data', {})
            
            # Extract key metrics with safe type conversion
            try:
                supply = float(token_info.get('totalSupply', 0))
                decimals = int(token_info.get('decimals', 0))
                price = float(price_info.get('value', 0))
                liquidity = float(price_info.get('liquidity', 0))
                volume_24h = float(price_info.get('volume24h', 0))
                holder_count = int(token_info.get('holderCount', 0))
                
                # Calculate market cap
                market_cap = supply * price / (10 ** decimals) if decimals > 0 else 0
                
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting token metrics: {str(e)}")
                return {
                    'should_buy': False,
                    'reason': 'Invalid token metrics',
                    'market_cap': 0,
                    'liquidity': 0
                }
            
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
                'price': price,
                'supply': supply,
                'decimals': decimals,
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

    async def scan_and_analyze(self) -> List[Dict]:
        """Scan for new tokens and analyze them"""
        try:
            new_tokens = await self.scanner.scan_new_tokens()
            analyzed_tokens = []
            
            for token in new_tokens:
                analysis = await self._analyze_token(token['address'])
                if analysis['should_buy']:
                    analyzed_tokens.append({
                        **token,
                        'analysis': analysis
                    })
            
            return analyzed_tokens
            
        except Exception as e:
            logger.error(f"Error in scan and analyze: {str(e)}")
            return []

    async def monitor_position(self, token_address: str, position_id: str, entry_price: float, size: float):
        """Monitor an open position and manage it according to risk parameters"""
        try:
            stop_loss = self.risk_manager.calculate_stop_loss(entry_price, await self.get_token_info(token_address))
            take_profit = self.risk_manager.calculate_take_profit(entry_price, stop_loss)
            highest_price = entry_price
            
            while True:
                try:
                    # Get current price and token info
                    token_info = await self.get_token_info(token_address)
                    if not token_info:
                        logger.error(f"Failed to get token info for {token_address}")
                        continue
                        
                    current_price = token_info.get('price', 0)
                    if current_price == 0:
                        logger.error("Invalid price received")
                        continue
                        
                    # Update position tracking
                    if current_price > highest_price:
                        highest_price = current_price
                        # Update trailing stop
                        new_stop = highest_price * (1 - self.risk_manager.config.trailing_stop_distance)
                        stop_loss = max(stop_loss, new_stop)
                        
                    # Check stop loss
                    if current_price <= stop_loss:
                        await self.close_position(token_address, position_id, "Stop loss hit")
                        break
                        
                    # Check take profit
                    if current_price >= take_profit:
                        await self.close_position(token_address, position_id, "Take profit hit")
                        break
                        
                    # Add delay between checks
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error in position monitoring loop: {str(e)}")
                    await asyncio.sleep(5)  # Longer delay on error
                    
        except Exception as e:
            logger.error(f"Fatal error in position monitoring: {str(e)}")
            await self.close_position(token_address, position_id, "Error in monitoring")

    async def get_token_info(self, token_address: str) -> Optional[Dict]:
        """Get token information with caching and retry logic"""
        cache_key = f"token_info_{token_address}"
        
        # Check cache first
        if hasattr(self, '_cache') and cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=30):
                return cached_data['data']
                
        # Fetch new data
        url = f"https://public-api.birdeye.so/public/token_data?address={token_address}"
        response = await self._retry_request(url)
        
        if response and 'data' in response:
            # Cache the result
            if not hasattr(self, '_cache'):
                self._cache = {}
            self._cache[cache_key] = {
                'data': response['data'],
                'timestamp': datetime.now()
            }
            return response['data']
            
        return None

    async def close_position(self, token_address: str, position_id: str, reason: str):
        """Close an open position"""
        # Implement position closing logic here
        logger.info(f"Closing position {position_id} for {token_address} due to {reason}")

    async def close(self):
        """Close resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
