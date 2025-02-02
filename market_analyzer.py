"""Market analysis and volatility detection for conservative trading."""

import pandas as pd
import numpy as np
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
import ta
from scipy import stats

logger = logging.getLogger('MarketAnalyzer')

@dataclass
class MarketCondition:
    """Current market condition assessment."""
    volatility: Decimal
    trend_strength: Decimal
    is_ranging: bool
    support_level: Optional[Decimal]
    resistance_level: Optional[Decimal]
    volume_profile: str  # 'high', 'medium', 'low'
    risk_score: Decimal  # 0 (low risk) to 1 (high risk)

class MarketAnalyzer:
    """Analyzes market conditions for conservative trading."""
    
    def __init__(self,
                 volatility_window: int = 20,
                 trend_window: int = 50,
                 volume_window: int = 20,
                 min_data_points: int = 100):
        """Initialize market analyzer."""
        self.volatility_window = volatility_window
        self.trend_window = trend_window
        self.volume_window = volume_window
        self.min_data_points = min_data_points
        
    def analyze_market(self,
                      df: pd.DataFrame,
                      current_price: Decimal) -> MarketCondition:
        """Analyze current market conditions."""
        if len(df) < self.min_data_points:
            raise ValueError(f"Insufficient data points: {len(df)} < {self.min_data_points}")
            
        # Calculate volatility
        returns = df['close'].pct_change()
        volatility = Decimal(str(returns.std() * np.sqrt(252)))  # Annualized
        
        # Calculate trend strength using ADX
        adx = ta.trend.ADXIndicator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=self.trend_window
        )
        trend_strength = Decimal(str(adx.adx().iloc[-1] / 100))  # Normalize to 0-1
        
        # Detect ranging market
        is_ranging = trend_strength < Decimal('0.25')
        
        # Find support and resistance levels
        support, resistance = self._find_support_resistance(df, current_price)
        
        # Analyze volume profile
        volume_profile = self._analyze_volume(df)
        
        # Calculate overall risk score
        risk_score = self._calculate_risk_score(
            volatility=volatility,
            trend_strength=trend_strength,
            is_ranging=is_ranging,
            volume_profile=volume_profile
        )
        
        return MarketCondition(
            volatility=volatility,
            trend_strength=trend_strength,
            is_ranging=is_ranging,
            support_level=support,
            resistance_level=resistance,
            volume_profile=volume_profile,
            risk_score=risk_score
        )
        
    def _find_support_resistance(self,
                               df: pd.DataFrame,
                               current_price: Decimal) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Find nearby support and resistance levels."""
        # Use pivot points and price action to find levels
        highs = df['high'].values
        lows = df['low'].values
        
        # Find local maxima and minima
        window = 20
        resistance_levels = []
        support_levels = []
        
        for i in range(window, len(df) - window):
            # Check for local maximum
            if all(highs[i] >= highs[i-window:i]) and all(highs[i] >= highs[i+1:i+window+1]):
                resistance_levels.append(highs[i])
                
            # Check for local minimum
            if all(lows[i] <= lows[i-window:i]) and all(lows[i] <= lows[i+1:i+window+1]):
                support_levels.append(lows[i])
                
        # Find closest levels to current price
        current_price_float = float(current_price)
        support = None
        resistance = None
        
        if support_levels:
            supports_below = [p for p in support_levels if p < current_price_float]
            if supports_below:
                support = Decimal(str(max(supports_below)))
                
        if resistance_levels:
            resistances_above = [p for p in resistance_levels if p > current_price_float]
            if resistances_above:
                resistance = Decimal(str(min(resistances_above)))
                
        return support, resistance
        
    def _analyze_volume(self, df: pd.DataFrame) -> str:
        """Analyze recent volume profile."""
        recent_volume = df['volume'].iloc[-self.volume_window:].mean()
        long_term_volume = df['volume'].mean()
        
        volume_ratio = recent_volume / long_term_volume
        
        if volume_ratio > 1.5:
            return 'high'
        elif volume_ratio < 0.7:
            return 'low'
        else:
            return 'medium'
            
    def _calculate_risk_score(self,
                            volatility: Decimal,
                            trend_strength: Decimal,
                            is_ranging: bool,
                            volume_profile: str) -> Decimal:
        """Calculate overall market risk score."""
        risk_score = Decimal('0')
        
        # Volatility contribution (0-0.4)
        vol_score = min(volatility * Decimal('2'), Decimal('0.4'))
        risk_score += vol_score
        
        # Trend contribution (0-0.3)
        if is_ranging:
            risk_score += Decimal('0.2')  # Ranging markets are moderately risky
        elif trend_strength > Decimal('0.7'):
            risk_score += Decimal('0.1')  # Strong trends are safer
        else:
            risk_score += Decimal('0.3')  # Weak trends are riskier
            
        # Volume contribution (0-0.3)
        if volume_profile == 'low':
            risk_score += Decimal('0.3')  # Low volume is risky
        elif volume_profile == 'high':
            risk_score += Decimal('0.2')  # High volume can be volatile
        else:
            risk_score += Decimal('0.1')  # Medium volume is safest
            
        return min(risk_score, Decimal('1'))
