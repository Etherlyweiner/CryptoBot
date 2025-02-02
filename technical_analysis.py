"""
Technical analysis module for CryptoBot.
Implements various technical indicators and trading signals.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
from logging_config import get_logger

logger = get_logger('TechnicalAnalysis')

@dataclass
class TradingSignal:
    """Represents a trading signal with type and strength."""
    timestamp: pd.Timestamp
    signal_type: str  # 'buy' or 'sell'
    strength: float  # 0 to 1
    indicator: str
    price: float
    metadata: Dict = None

class TechnicalAnalysis:
    def __init__(self, 
                 rsi_period: int = 14,
                 rsi_overbought: float = 70,
                 rsi_oversold: float = 30,
                 ema_short_period: int = 12,
                 ema_long_period: int = 26,
                 macd_signal_period: int = 9):
        """
        Initialize technical analysis with default parameters.
        
        Args:
            rsi_period: Period for RSI calculation
            rsi_overbought: RSI level considered overbought
            rsi_oversold: RSI level considered oversold
            ema_short_period: Short period for EMA calculation
            ema_long_period: Long period for EMA calculation
            macd_signal_period: Signal period for MACD
        """
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.ema_short_period = ema_short_period
        self.ema_long_period = ema_long_period
        self.macd_signal_period = macd_signal_period
        
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """
        Calculate the Relative Strength Index.
        
        Args:
            prices: Series of prices
            
        Returns:
            Series containing RSI values
        """
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gains = delta.copy()
        losses = delta.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        # Calculate average gains and losses
        avg_gains = gains.rolling(window=self.rsi_period).mean()
        avg_losses = losses.rolling(window=self.rsi_period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average.
        
        Args:
            prices: Series of prices
            period: EMA period
            
        Returns:
            Series containing EMA values
        """
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD, Signal line, and MACD histogram.
        
        Args:
            prices: Series of prices
            
        Returns:
            Tuple of (MACD line, Signal line, MACD histogram)
        """
        # Calculate EMAs
        ema_short = self.calculate_ema(prices, self.ema_short_period)
        ema_long = self.calculate_ema(prices, self.ema_long_period)
        
        # Calculate MACD line
        macd_line = ema_short - ema_long
        
        # Calculate Signal line
        signal_line = self.calculate_ema(macd_line, self.macd_signal_period)
        
        # Calculate MACD histogram
        macd_histogram = macd_line - signal_line
        
        return macd_line, signal_line, macd_histogram
    
    def generate_signals(self, prices: pd.Series) -> List[TradingSignal]:
        """
        Generate trading signals based on technical indicators.
        
        Args:
            prices: Series of prices with datetime index
            
        Returns:
            List of TradingSignal objects
        """
        signals = []
        
        # Calculate indicators
        rsi = self.calculate_rsi(prices)
        macd_line, signal_line, macd_hist = self.calculate_macd(prices)
        ema_short = self.calculate_ema(prices, self.ema_short_period)
        ema_long = self.calculate_ema(prices, self.ema_long_period)
        
        # Get timestamps after initial period
        valid_timestamps = prices.index[max(self.rsi_period, self.ema_long_period):]
        
        # Generate signals for each timestamp
        for i in range(1, len(valid_timestamps)):
            timestamp = valid_timestamps[i]
            prev_timestamp = valid_timestamps[i-1]
            current_signals = []
            
            # RSI signals
            if rsi[timestamp] < self.rsi_oversold:
                current_signals.append(
                    TradingSignal(
                        timestamp=timestamp,
                        signal_type='buy',
                        strength=1 - (rsi[timestamp] / self.rsi_oversold),
                        indicator='RSI',
                        price=prices[timestamp],
                        metadata={'rsi': rsi[timestamp]}
                    )
                )
            elif rsi[timestamp] > self.rsi_overbought:
                current_signals.append(
                    TradingSignal(
                        timestamp=timestamp,
                        signal_type='sell',
                        strength=(rsi[timestamp] - self.rsi_overbought) / (100 - self.rsi_overbought),
                        indicator='RSI',
                        price=prices[timestamp],
                        metadata={'rsi': rsi[timestamp]}
                    )
                )
            
            # MACD signals
            if macd_hist[timestamp] > 0 and macd_hist[prev_timestamp] <= 0:
                current_signals.append(
                    TradingSignal(
                        timestamp=timestamp,
                        signal_type='buy',
                        strength=abs(macd_hist[timestamp]),
                        indicator='MACD',
                        price=prices[timestamp],
                        metadata={
                            'macd': macd_line[timestamp],
                            'signal': signal_line[timestamp],
                            'histogram': macd_hist[timestamp]
                        }
                    )
                )
            elif macd_hist[timestamp] < 0 and macd_hist[prev_timestamp] >= 0:
                current_signals.append(
                    TradingSignal(
                        timestamp=timestamp,
                        signal_type='sell',
                        strength=abs(macd_hist[timestamp]),
                        indicator='MACD',
                        price=prices[timestamp],
                        metadata={
                            'macd': macd_line[timestamp],
                            'signal': signal_line[timestamp],
                            'histogram': macd_hist[timestamp]
                        }
                    )
                )
            
            # EMA crossover signals
            if (ema_short[timestamp] > ema_long[timestamp] and 
                ema_short[prev_timestamp] <= ema_long[prev_timestamp]):
                current_signals.append(
                    TradingSignal(
                        timestamp=timestamp,
                        signal_type='buy',
                        strength=abs(ema_short[timestamp] - ema_long[timestamp]) / prices[timestamp],
                        indicator='EMA_CROSS',
                        price=prices[timestamp],
                        metadata={
                            'ema_short': ema_short[timestamp],
                            'ema_long': ema_long[timestamp]
                        }
                    )
                )
            elif (ema_short[timestamp] < ema_long[timestamp] and 
                  ema_short[prev_timestamp] >= ema_long[prev_timestamp]):
                current_signals.append(
                    TradingSignal(
                        timestamp=timestamp,
                        signal_type='sell',
                        strength=abs(ema_short[timestamp] - ema_long[timestamp]) / prices[timestamp],
                        indicator='EMA_CROSS',
                        price=prices[timestamp],
                        metadata={
                            'ema_short': ema_short[timestamp],
                            'ema_long': ema_long[timestamp]
                        }
                    )
                )
            
            signals.extend(current_signals)
            
            if current_signals:
                signals_str = '\n'.join([f"{s.indicator} {s.signal_type.upper()} (strength: {s.strength:.2f})" 
                                       for s in current_signals])
                logger.info(f"Generated signals at {timestamp}:\n{signals_str}")
        
        return signals
