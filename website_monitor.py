"""
Website monitoring for new token launches
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
import requests
from bs4 import BeautifulSoup
import pandas as pd
from database import Database
import random
import time
from config import config
from logging_config import get_logger, log_with_context
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from notifications import notifications

logger = get_logger('WebsiteMonitor')

class RateLimiter:
    """Rate limiter for API requests"""
    def __init__(self, calls: int, period: int = 60):
        self.calls = calls
        self.period = period
        self.timestamps = []
    
    def __call__(self):
        now = time.time()
        self.timestamps = [ts for ts in self.timestamps if now - ts < self.period]
        
        if len(self.timestamps) >= self.calls:
            sleep_time = self.timestamps[0] + self.period - now
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self.timestamps.append(now)

class WebsiteMonitor:
    def __init__(self, database: Database):
        self.database = database
        self.monitored_sites = config.MONITORED_SITES
        self.known_tokens: Set[str] = set()
        self.session = requests.Session()
        self.rate_limiters = {
            site: RateLimiter(info['rate_limit'])
            for site, info in self.monitored_sites.items()
        }
        
        # Initialize proxy list
        self.proxies = []
        if config.USE_PROXIES and config.PROXY_LIST:
            self.proxies = [
                {'http': proxy, 'https': proxy}
                for proxy in config.PROXY_LIST
                if proxy.strip()
            ]
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional user agent rotation"""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'User-Agent': random.choice(config.USER_AGENTS) if config.ROTATE_USER_AGENTS else config.USER_AGENTS[0]
        }
        return headers
    
    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration"""
        if not self.proxies or not config.USE_PROXIES:
            return None
        return random.choice(self.proxies) if config.ROTATE_PROXIES else self.proxies[0]

    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=config.RETRY_DELAY, min=1, max=30),
        reraise=True
    )
    async def _fetch_page(self, site_name: str, url: str) -> str:
        """Fetch page content with retries and rate limiting"""
        try:
            # Apply rate limiting
            self.rate_limiters[site_name]()
            
            # Prepare request
            headers = self._get_headers()
            proxy = self._get_proxy()
            
            # Log request attempt
            log_with_context(
                logger,
                logging.INFO,
                f"Fetching {site_name}",
                {
                    'site': site_name,
                    'url': url,
                    'proxy': bool(proxy),
                    'user_agent': headers['User-Agent'][:20] + '...'
                }
            )
            
            # Make request
            response = self.session.get(
                url,
                headers=headers,
                proxies=proxy,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            return response.text
            
        except requests.RequestException as e:
            log_with_context(
                logger,
                logging.ERROR,
                f"Error fetching {site_name}",
                {
                    'site': site_name,
                    'url': url,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            raise

    async def start_monitoring(self):
        """Start monitoring all configured websites"""
        while True:
            try:
                for site_name, site_info in self.monitored_sites.items():
                    if site_info['enabled']:
                        try:
                            content = await self._fetch_page(site_name, site_info['url'])
                            new_tokens = await self._parse_site(site_name, content)
                            await self._process_new_tokens(site_name, new_tokens)
                        except Exception as e:
                            log_with_context(
                                logger,
                                logging.ERROR,
                                f"Error processing {site_name}",
                                {
                                    'site': site_name,
                                    'error': str(e),
                                    'error_type': type(e).__name__
                                }
                            )
                
                await asyncio.sleep(config.MONITOR_INTERVAL)
                
            except Exception as e:
                log_with_context(
                    logger,
                    logging.ERROR,
                    "Error in monitoring loop",
                    {'error': str(e), 'error_type': type(e).__name__}
                )
                await asyncio.sleep(config.MONITOR_INTERVAL)

    async def _parse_site(self, site_name: str, content: str) -> List[Dict]:
        """Parse site content using appropriate parser"""
        parser_map = {
            'coinmarketcap': self._parse_coinmarketcap,
            'coingecko': self._parse_coingecko,
            'binance': self._parse_binance,
            'dextools': self._parse_dextools
        }
        
        parser = parser_map.get(site_name)
        if not parser:
            logger.error(f"No parser found for {site_name}")
            return []
        
        try:
            return await parser(content)
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                f"Error parsing {site_name}",
                {
                    'site': site_name,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            return []

    async def _process_new_tokens(self, site_name: str, tokens: List[Dict]):
        """Process newly discovered tokens"""
        for token in tokens:
            try:
                if token['symbol'] not in self.known_tokens:
                    self.known_tokens.add(token['symbol'])
                    
                    # Store token data
                    token_data = {
                        'timestamp': datetime.utcnow(),
                        'source': site_name,
                        'symbol': token['symbol'],
                        'name': token['name'],
                        'initial_price': token.get('price', 0.0),
                        'initial_market_cap': token.get('market_cap', 0.0),
                        'chain': token.get('chain', ''),
                        'contract_address': token.get('contract_address', ''),
                        'description': token.get('description', ''),
                        'website': token.get('website', ''),
                        'social_links': token.get('social_links', {}),
                        'launch_date': token.get('launch_date', datetime.utcnow())
                    }
                    
                    self.database.store_new_token(token_data)
                    
                    # Analyze token
                    metrics = {
                        'symbol': token['symbol'],
                        'timestamp': datetime.utcnow(),
                        'initial_momentum': self._calculate_momentum(token),
                        'social_score': self._calculate_social_score(token),
                        'risk_score': self._calculate_risk_score(token),
                        'opportunity_score': 0.0
                    }
                    
                    # Calculate opportunity score
                    metrics['opportunity_score'] = (
                        metrics['initial_momentum'] * 0.4 +
                        metrics['social_score'] * 0.3 +
                        (1 - metrics['risk_score']) * 0.3
                    )
                    
                    self.database.store_token_analysis(metrics)
                    
                    # Generate alert for high-opportunity tokens
                    if metrics['opportunity_score'] >= config.MIN_OPPORTUNITY_SCORE:
                        alert_data = {
                            'timestamp': datetime.utcnow(),
                            'symbol': token['symbol'],
                            'name': token['name'],
                            'opportunity_score': metrics['opportunity_score'],
                            'momentum_score': metrics['initial_momentum'],
                            'social_score': metrics['social_score'],
                            'risk_score': metrics['risk_score'],
                            'alert_message': (
                                f"High opportunity detected for {token['symbol']}! "
                                f"Opportunity Score: {metrics['opportunity_score']:.2f}"
                            )
                        }
                        
                        self.database.store_alert(alert_data)
                        
                        # Send notifications
                        notifications.send_notification(alert_data)
                        
                        # Log alert
                        log_with_context(
                            logger,
                            logging.INFO,
                            f"Generated alert for {token['symbol']}",
                            {
                                'symbol': token['symbol'],
                                'opportunity_score': metrics['opportunity_score'],
                                'source': site_name
                            }
                        )
                    
            except Exception as e:
                log_with_context(
                    logger,
                    logging.ERROR,
                    f"Error processing token {token.get('symbol', 'UNKNOWN')}",
                    {
                        'token': token,
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                )

    def _calculate_momentum(self, token: Dict) -> float:
        """Calculate initial momentum score"""
        try:
            price = float(token.get('price', 0))
            volume = float(token.get('volume_24h', 0))
            market_cap = float(token.get('market_cap', 0))
            
            if price == 0 or market_cap == 0:
                return 0.0
            
            volume_mc_ratio = min(volume / market_cap, 1.0) if market_cap > 0 else 0
            
            momentum_score = (
                volume_mc_ratio * 0.7 +
                (1 if token.get('listed_on_major_exchange', False) else 0) * 0.3
            )
            
            return min(max(momentum_score, 0.0), 1.0)
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                "Error calculating momentum",
                {
                    'token': token,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            return 0.0

    def _calculate_social_score(self, token: Dict) -> float:
        """Calculate social sentiment score"""
        try:
            social_links = token.get('social_links', {})
            website = token.get('website', '')
            
            has_website = bool(website)
            has_whitepaper = bool(token.get('whitepaper_url', ''))
            social_presence = len(social_links) > 0
            
            score = (
                (0.3 if has_website else 0) +
                (0.3 if has_whitepaper else 0) +
                (0.4 if social_presence else 0)
            )
            
            return min(max(score, 0.0), 1.0)
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                "Error calculating social score",
                {
                    'token': token,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            return 0.0

    def _calculate_risk_score(self, token: Dict) -> float:
        """Calculate risk score (higher score = higher risk)"""
        try:
            no_website = not bool(token.get('website', ''))
            no_social = not bool(token.get('social_links', {}))
            low_liquidity = float(token.get('liquidity', 0)) < config.MIN_LIQUIDITY
            
            risk_score = (
                (0.4 if no_website else 0) +
                (0.3 if no_social else 0) +
                (0.3 if low_liquidity else 0)
            )
            
            return min(max(risk_score, 0.0), 1.0)
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                "Error calculating risk score",
                {
                    'token': token,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            return 1.0

    async def cleanup(self):
        """Cleanup resources"""
        self.session.close()

    async def _parse_coinmarketcap(self, content: str) -> List[Dict]:
        """Parse CoinMarketCap new listings page"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            tokens = []
            
            for row in soup.select('.cmc-table tbody tr'):
                try:
                    token = {
                        'symbol': row.select_one('.coin-symbol').text.strip(),
                        'name': row.select_one('.coin-name').text.strip(),
                        'price': float(row.select_one('.price').text.strip().replace('$', '')),
                        'market_cap': float(row.select_one('.market-cap').text.strip().replace('$', '').replace(',', '')),
                        'chain': row.select_one('.chain').text.strip(),
                        'launch_date': datetime.utcnow()
                    }
                    tokens.append(token)
                except Exception as e:
                    logger.error(f"Error parsing token row: {str(e)}")
                    continue
            
            return tokens
        except Exception as e:
            logger.error(f"Error parsing CoinMarketCap: {str(e)}")
            return []

    async def _parse_coingecko(self, content: str) -> List[Dict]:
        """Parse CoinGecko new listings page"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            tokens = []
            
            for row in soup.select('.gecko-table-row'):
                try:
                    token = {
                        'symbol': row.select_one('.coin-symbol').text.strip(),
                        'name': row.select_one('.coin-name').text.strip(),
                        'price': float(row.select_one('.price').text.strip().replace('$', '')),
                        'market_cap': float(row.select_one('.market-cap').text.strip().replace('$', '').replace(',', '')),
                        'chain': row.select_one('.chain').text.strip(),
                        'launch_date': datetime.utcnow()
                    }
                    tokens.append(token)
                except Exception as e:
                    logger.error(f"Error parsing token row: {str(e)}")
                    continue
            
            return tokens
        except Exception as e:
            logger.error(f"Error parsing CoinGecko: {str(e)}")
            return []

    async def _parse_binance(self, content: str) -> List[Dict]:
        """Parse Binance new listings page"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            tokens = []
            
            for row in soup.select('.listing-table tr'):
                try:
                    token = {
                        'symbol': row.select_one('.symbol').text.strip(),
                        'name': row.select_one('.name').text.strip(),
                        'price': float(row.select_one('.price').text.strip().replace('$', '')),
                        'chain': 'BNB',
                        'launch_date': datetime.utcnow(),
                        'listed_on_major_exchange': True
                    }
                    tokens.append(token)
                except Exception as e:
                    logger.error(f"Error parsing token row: {str(e)}")
                    continue
            
            return tokens
        except Exception as e:
            logger.error(f"Error parsing Binance: {str(e)}")
            return []

    async def _parse_dextools(self, content: str) -> List[Dict]:
        """Parse DexTools new pairs page"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            tokens = []
            
            for row in soup.select('.pairs-table tr'):
                try:
                    token = {
                        'symbol': row.select_one('.token-symbol').text.strip(),
                        'name': row.select_one('.token-name').text.strip(),
                        'price': float(row.select_one('.price').text.strip().replace('$', '')),
                        'liquidity': float(row.select_one('.liquidity').text.strip().replace('$', '').replace(',', '')),
                        'chain': row.select_one('.chain').text.strip(),
                        'contract_address': row.select_one('.contract').text.strip(),
                        'launch_date': datetime.utcnow()
                    }
                    tokens.append(token)
                except Exception as e:
                    logger.error(f"Error parsing token row: {str(e)}")
                    continue
            
            return tokens
        except Exception as e:
            logger.error(f"Error parsing DexTools: {str(e)}")
            return []
