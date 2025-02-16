"""Token discovery and analysis module for Photon DEX."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

@dataclass
class TokenMetrics:
    """Data class to store token metrics."""
    symbol: str
    name: str
    price: float
    volume_24h: float
    market_cap: float
    liquidity: float
    price_change_24h: float
    holder_count: int
    address: str
    
class TokenDiscovery:
    """Token discovery and analysis for Photon DEX."""
    
    def __init__(self, driver, config: Dict[str, Any]):
        """Initialize token discovery with webdriver and config."""
        self.driver = driver
        self.config = config
        self.min_liquidity = config['discovery']['min_liquidity']
        self.min_holders = config['discovery']['min_holders']
        self.min_volume = config['discovery']['min_volume']
        
    async def scan_tokens(self) -> List[TokenMetrics]:
        """Scan token table and extract metrics."""
        try:
            logger.info("Scanning token table...")
            
            # Wait for token table to load
            table = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "token-table"))
            )
            
            # Get all token rows
            rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
            tokens = []
            
            for row in rows:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    
                    # Extract metrics from columns
                    symbol = cols[0].text
                    name = cols[1].text
                    price = float(cols[2].text.replace("$", "").replace(",", ""))
                    volume = float(cols[3].text.replace("$", "").replace(",", ""))
                    market_cap = float(cols[4].text.replace("$", "").replace(",", ""))
                    liquidity = float(cols[5].text.replace("$", "").replace(",", ""))
                    price_change = float(cols[6].text.replace("%", ""))
                    holders = int(cols[7].text.replace(",", ""))
                    address = cols[8].find_element(By.TAG_NAME, "a").get_attribute("href").split("/")[-1]
                    
                    token = TokenMetrics(
                        symbol=symbol,
                        name=name,
                        price=price,
                        volume_24h=volume,
                        market_cap=market_cap,
                        liquidity=liquidity,
                        price_change_24h=price_change,
                        holder_count=holders,
                        address=address
                    )
                    
                    tokens.append(token)
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse token row: {str(e)}")
                    continue
                    
            logger.info(f"Successfully scanned {len(tokens)} tokens")
            return tokens
            
        except Exception as e:
            logger.error(f"Failed to scan token table: {str(e)}")
            return []
            
    def analyze_opportunity(self, token: TokenMetrics) -> Tuple[float, str]:
        """Analyze token metrics and return opportunity score and reason."""
        if token.liquidity < self.min_liquidity:
            return 0.0, "Insufficient liquidity"
            
        if token.holder_count < self.min_holders:
            return 0.0, "Too few holders"
            
        if token.volume_24h < self.min_volume:
            return 0.0, "Low trading volume"
            
        # Calculate opportunity score (0.0 to 1.0)
        score = 0.0
        reason = []
        
        # Volume score (30%)
        volume_score = min(token.volume_24h / (self.min_volume * 10), 1.0) * 0.3
        score += volume_score
        
        # Liquidity score (30%)
        liquidity_score = min(token.liquidity / (self.min_liquidity * 5), 1.0) * 0.3
        score += liquidity_score
        
        # Holder score (20%)
        holder_score = min(token.holder_count / (self.min_holders * 5), 1.0) * 0.2
        score += holder_score
        
        # Price change score (20%)
        if token.price_change_24h > 0:
            price_score = min(token.price_change_24h / 100, 1.0) * 0.2
            score += price_score
            
        # Build reason string
        if volume_score > 0.15:
            reason.append("High volume")
        if liquidity_score > 0.15:
            reason.append("Good liquidity")
        if holder_score > 0.1:
            reason.append("Strong holder base")
        if price_score > 0.1:
            reason.append("Positive price action")
            
        reason_str = ", ".join(reason) if reason else "Meets minimum criteria"
        
        return score, reason_str
