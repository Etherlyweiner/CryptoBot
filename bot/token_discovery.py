"""Token discovery with focus on meme tokens and migration opportunities."""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import logging
import re

logger = logging.getLogger(__name__)

@dataclass
class TokenMetrics:
    """Token metrics data structure."""
    address: str
    symbol: str
    name: str
    price: float
    price_change_24h: float
    volume_24h: float
    liquidity: float
    holder_count: Optional[int] = None
    is_meme: bool = False
    migration_signals: List[str] = None
    social_signals: List[str] = None
    
    def __post_init__(self):
        if self.migration_signals is None:
            self.migration_signals = []
        if self.social_signals is None:
            self.social_signals = []

class TokenDiscovery:
    """Token discovery with focus on meme tokens and migration opportunities."""
    
    def __init__(self, config):
        """Initialize token discovery."""
        self.config = config
        self.meme_keywords = [
            'pepe', 'doge', 'shib', 'inu', 'elon', 'moon', 'safe', 'baby',
            'chad', 'wojak', 'based', 'meme', 'cat', 'dog', 'frog', 'coin'
        ]
        self.migration_indicators = [
            'v2', 'migration', 'upgrade', 'relaunch', 'airdrop', 'snapshot',
            'bridge', 'transfer', 'lock', 'vesting'
        ]
        
    def calculate_priority_fee(self, token_price: float, wallet_balance: float) -> int:
        """Calculate optimal priority fee based on token price and wallet balance."""
        # Base priority fee in lamports (1 SOL = 1e9 lamports)
        base_fee = 10000  # 0.00001 SOL
        
        # Adjust fee based on wallet balance (more aggressive if we have more funds)
        balance_factor = min(wallet_balance / 100, 10)  # Cap at 10x
        
        # Adjust fee based on token price (more aggressive for higher priced tokens)
        price_factor = min(token_price * 1000, 5)  # Cap at 5x
        
        # Calculate final fee
        priority_fee = int(base_fee * balance_factor * price_factor)
        
        # Cap the fee at 0.1% of wallet balance
        max_fee = int(wallet_balance * 1e9 * 0.001)  # Convert SOL to lamports
        priority_fee = min(priority_fee, max_fee)
        
        return priority_fee
        
    def is_potential_meme(self, token: TokenMetrics) -> bool:
        """Check if token has meme potential."""
        name_lower = token.name.lower()
        symbol_lower = token.symbol.lower()
        
        # Check for meme keywords
        if any(kw in name_lower or kw in symbol_lower for kw in self.meme_keywords):
            return True
            
        # Check for typical meme token patterns
        if re.search(r'[A-Z]{4,}', token.symbol):  # All caps symbols
            return True
            
        return False
        
    def detect_migration_signals(self, token: TokenMetrics) -> List[str]:
        """Detect potential migration or upgrade signals."""
        signals = []
        name_lower = token.name.lower()
        
        # Check for migration indicators
        for indicator in self.migration_indicators:
            if indicator in name_lower:
                signals.append(f"Found '{indicator}' in token name")
                
        # Check for version patterns
        if re.search(r'v[0-9]+', name_lower):
            signals.append("Version number in token name")
            
        # Check for typical migration patterns
        if token.holder_count and token.holder_count < 1000:
            signals.append("Low holder count - potential early migration")
            
        return signals
        
    def analyze_bonding_curve(self, token: TokenMetrics) -> Tuple[float, List[str]]:
        """Analyze token's bonding curve for profitable entry points."""
        reasons = []
        score = 0.0
        
        # Check liquidity to market cap ratio
        liq_ratio = token.liquidity / (token.price * token.holder_count if token.holder_count else 1e6)
        if liq_ratio < 0.1:
            score += 2.0
            reasons.append("Low liquidity ratio - potential for price impact")
            
        # Check volume to liquidity ratio
        vol_ratio = token.volume_24h / token.liquidity if token.liquidity > 0 else 0
        if vol_ratio > 2.0:
            score += 1.5
            reasons.append("High volume relative to liquidity")
            
        # Check price movement
        if abs(token.price_change_24h) > 20:
            score += 1.0
            reasons.append("Significant price movement in 24h")
            
        return score, reasons
        
    def calculate_opportunity_score(self, token: TokenMetrics) -> Tuple[float, str]:
        """Calculate opportunity score for a token."""
        score = 0.0
        reasons = []
        
        # Check if it's a potential meme token
        if self.is_potential_meme(token):
            score += 2.0
            reasons.append("Meme token potential")
            token.is_meme = True
            
        # Detect migration signals
        migration_signals = self.detect_migration_signals(token)
        if migration_signals:
            score += len(migration_signals) * 1.5
            reasons.extend(migration_signals)
            token.migration_signals = migration_signals
            
        # Analyze bonding curve
        curve_score, curve_reasons = self.analyze_bonding_curve(token)
        score += curve_score
        reasons.extend(curve_reasons)
        
        # Risk adjustments
        if token.liquidity < self.config['risk']['min_liquidity']:
            score -= 2.0
            reasons.append("Low liquidity risk")
            
        if token.volume_24h < self.config['risk']['min_volume']:
            score -= 1.5
            reasons.append("Low volume risk")
            
        # Format reasons
        reason_text = " | ".join(reasons)
        
        return score, reason_text
