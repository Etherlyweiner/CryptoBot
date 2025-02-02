"""
Technical analysis module for CryptoBot
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional, List
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
import asyncio
from decimal import Decimal

logger = logging.getLogger('CryptoBot.Analysis')

@dataclass
class PriceData:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class AnalysisResult:
    price: float
    rsi: float
    macd: float
    macd_signal: float
    macd_hist: float
    ema_fast: float
    ema_slow: float
    atr: float
    volatility: float
    support: float
    resistance: float
    trend: str
    timestamp: datetime

class TechnicalAnalyzer:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {
            'rsi_period': 14,
            'ema_fast': 12,
            'ema_slow': 26,
            'macd_signal': 9,
            'atr_period': 14,
            'volatility_period': 20,
            'price_api': 'https://api.coingecko.com/api/v3'
        }
        self._session: Optional[aiohttp.ClientSession] = None
        self._price_cache = {}
        self._cache_expiry = {}
        self.CACHE_DURATION = timedelta(minutes=5)
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
        
    async def get_historical_prices(self, token_address: str, days: int = 30) -> Optional[List[PriceData]]:
        """Fetch historical price data from CoinGecko"""
        try:
            # Check cache first
            cache_key = f"{token_address}_{days}"
            if cache_key in self._price_cache:
                if datetime.utcnow() < self._cache_expiry[cache_key]:
                    return self._price_cache[cache_key]
                    
            session = await self._get_session()
            params = {
                'vs_currency': 'usd',
                'days': str(days),
                'interval': 'hourly'
            }
            
            async with session.get(
                f"{self.config['price_api']}/coins/solana/contract/{token_address}/market_chart",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = []
                    
                    for timestamp, price, volume in zip(
                        data['prices'],
                        data['prices'],
                        data['total_volumes']
                    ):
                        prices.append(PriceData(
                            timestamp=datetime.fromtimestamp(timestamp[0]/1000),
                            open=float(price[1]),
                            high=float(price[1]),
                            low=float(price[1]),
                            close=float(price[1]),
                            volume=float(volume[1])
                        ))
                        
                    # Cache the results
                    self._price_cache[cache_key] = prices
                    self._cache_expiry[cache_key] = datetime.utcnow() + self.CACHE_DURATION
                    return prices
                    
                logger.error(f"Failed to get price data: {response.status}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching historical prices: {str(e)}")
            return None
            
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        try:
            deltas = np.diff(prices)
            seed = deltas[:period+1]
            up = seed[seed >= 0].sum()/period
            down = -seed[seed < 0].sum()/period
            rs = up/down if down != 0 else float('inf')
            rsi = np.zeros_like(prices)
            rsi[:period] = 100. - 100./(1.+rs)
            
            for i in range(period, len(prices)):
                delta = deltas[i-1]
                if delta > 0:
                    upval = delta
                    downval = 0.
                else:
                    upval = 0.
                    downval = -delta
                    
                up = (up*(period-1) + upval)/period
                down = (down*(period-1) + downval)/period
                rs = up/down if down != 0 else float('inf')
                rsi[i] = 100. - 100./(1.+rs)
                
            return rsi[-1]
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            return 50.0
            
    def calculate_macd(self, prices: List[float]) -> tuple[float, float, float]:
        """Calculate MACD, Signal, and Histogram"""
        try:
            ema_fast = pd.Series(prices).ewm(span=self.config['ema_fast']).mean()
            ema_slow = pd.Series(prices).ewm(span=self.config['ema_slow']).mean()
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=self.config['macd_signal']).mean()
            hist = macd - signal
            
            return macd.iloc[-1], signal.iloc[-1], hist.iloc[-1]
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            return 0.0, 0.0, 0.0
            
    def calculate_atr(self, price_data: List[PriceData], period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            high = np.array([p.high for p in price_data])
            low = np.array([p.low for p in price_data])
            close = np.array([p.close for p in price_data])
            
            tr1 = np.abs(high - low)
            tr2 = np.abs(high - np.roll(close, 1))
            tr3 = np.abs(low - np.roll(close, 1))
            
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            atr = pd.Series(tr).rolling(window=period).mean().iloc[-1]
            
            return float(atr)
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {str(e)}")
            return 0.0
            
    def calculate_volatility(self, prices: List[float], period: int = 20) -> float:
        """Calculate price volatility (standard deviation of returns)"""
        try:
            returns = np.diff(np.log(prices))
            volatility = np.std(returns[-period:]) * np.sqrt(365)
            return float(volatility)
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {str(e)}")
            return 0.0
            
    def find_support_resistance(self, price_data: List[PriceData]) -> tuple[float, float]:
        """Find support and resistance levels using price action"""
        try:
            prices = np.array([p.close for p in price_data])
            window = min(20, len(prices))
            
            # Simple moving average as baseline
            sma = pd.Series(prices).rolling(window=window).mean().iloc[-1]
            
            # Find local minima and maxima
            peaks = []
            troughs = []
            
            for i in range(1, len(prices)-1):
                if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                    peaks.append(prices[i])
                if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                    troughs.append(prices[i])
                    
            # Calculate support and resistance
            support = np.mean(troughs[-3:]) if troughs else sma * 0.95
            resistance = np.mean(peaks[-3:]) if peaks else sma * 1.05
            
            return float(support), float(resistance)
            
        except Exception as e:
            logger.error(f"Error finding support/resistance: {str(e)}")
            return 0.0, float('inf')
            
    def determine_trend(self, prices: List[float]) -> str:
        """Determine price trend using moving averages"""
        try:
            ema_fast = pd.Series(prices).ewm(span=self.config['ema_fast']).mean()
            ema_slow = pd.Series(prices).ewm(span=self.config['ema_slow']).mean()
            
            if ema_fast.iloc[-1] > ema_slow.iloc[-1]:
                if ema_fast.iloc[-1] > ema_fast.iloc[-2]:
                    return "strong_uptrend"
                return "weak_uptrend"
            else:
                if ema_fast.iloc[-1] < ema_fast.iloc[-2]:
                    return "strong_downtrend"
                return "weak_downtrend"
                
        except Exception as e:
            logger.error(f"Error determining trend: {str(e)}")
            return "neutral"
            
    async def analyze_token(self, token_address: str) -> Optional[AnalysisResult]:
        """Perform complete technical analysis on a token"""
        try:
            # Get historical price data
            price_data = await self.get_historical_prices(token_address)
            if not price_data:
                return None
                
            # Extract close prices
            closes = [p.close for p in price_data]
            
            # Calculate all indicators
            rsi = self.calculate_rsi(closes)
            macd, signal, hist = self.calculate_macd(closes)
            atr = self.calculate_atr(price_data)
            volatility = self.calculate_volatility(closes)
            support, resistance = self.find_support_resistance(price_data)
            trend = self.determine_trend(closes)
            
            # Calculate EMAs
            ema_fast = pd.Series(closes).ewm(span=self.config['ema_fast']).mean().iloc[-1]
            ema_slow = pd.Series(closes).ewm(span=self.config['ema_slow']).mean().iloc[-1]
            
            return AnalysisResult(
                price=closes[-1],
                rsi=rsi,
                macd=macd,
                macd_signal=signal,
                macd_hist=hist,
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                atr=atr,
                volatility=volatility,
                support=support,
                resistance=resistance,
                trend=trend,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing token: {str(e)}")
            return None
            
    async def close(self):
        """Clean up resources"""
        if self._session and not self._session.closed:
            await self._session.close()
