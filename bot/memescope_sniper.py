import os
import logging
import time
from decimal import Decimal
from typing import Optional, Dict, List, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timedelta

logger = logging.getLogger('MemescopeSniper')

class MemescopeSniper:
    """Bot for sniping tokens about to migrate on Photon memescope."""
    
    def __init__(self, headless: bool = False):
        """Initialize MemescopeSniper."""
        self.headless = headless
        self.driver = None
        self.memescope_url = "https://photon-sol.tinyastro.io/en/memescope"
        self.setup_driver()
        self.token_data = {}
        
    def setup_driver(self):
        """Set up Selenium WebDriver."""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        
        # Add necessary Chrome options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(5)
        
    def navigate_to_memescope(self):
        """Navigate to Photon memescope."""
        try:
            self.driver.get(self.memescope_url)
            # Wait for the table to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "token-table"))
            )
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to memescope: {str(e)}")
            return False
            
    def scan_tokens(self) -> List[Dict]:
        """Scan memescope for potential tokens to snipe."""
        tokens = []
        try:
            # Find all token rows in the table
            rows = self.driver.find_elements(By.CSS_SELECTOR, ".token-table tr")
            
            for row in rows[1:]:  # Skip header row
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 6:
                        continue
                        
                    # Extract token data
                    token = {
                        'name': cols[0].text,
                        'symbol': cols[1].text,
                        'price': self._parse_price(cols[2].text),
                        'market_cap': self._parse_market_cap(cols[3].text),
                        'volume': self._parse_volume(cols[4].text),
                        'holders': self._parse_holders(cols[5].text),
                        'migration_status': self._check_migration_status(row),
                        'bonding_curve': self._check_bonding_curve(row),
                        'timestamp': datetime.now()
                    }
                    
                    # Store historical data for analysis
                    if token['symbol'] not in self.token_data:
                        self.token_data[token['symbol']] = []
                    self.token_data[token['symbol']].append(token)
                    
                    tokens.append(token)
                    
                except Exception as e:
                    logger.warning(f"Error parsing row: {str(e)}")
                    continue
                    
            return tokens
            
        except Exception as e:
            logger.error(f"Error scanning tokens: {str(e)}")
            return []
            
    def analyze_migration_opportunities(self, tokens: List[Dict]) -> List[Dict]:
        """Analyze tokens for migration opportunities."""
        opportunities = []
        
        for token in tokens:
            score = 0
            reasons = []
            
            # Check migration status
            if token['migration_status'] == 'pending':
                score += 3
                reasons.append("Migration pending")
                
            # Check bonding curve position
            if token['bonding_curve'] == 'early':
                score += 2
                reasons.append("Early in bonding curve")
                
            # Check market metrics
            if token['holders'] > 100:
                score += 1
                reasons.append("Good holder count")
                
            if token['volume'] > 1000:
                score += 1
                reasons.append("Good volume")
                
            # Check price momentum
            if token['symbol'] in self.token_data:
                history = self.token_data[token['symbol']]
                if len(history) > 1:
                    price_change = (token['price'] - history[-2]['price']) / history[-2]['price']
                    if price_change > 0.05:  # 5% price increase
                        score += 2
                        reasons.append("Positive price momentum")
                        
            if score >= 5:  # Minimum score threshold
                opportunities.append({
                    **token,
                    'score': score,
                    'reasons': reasons
                })
                
        return sorted(opportunities, key=lambda x: x['score'], reverse=True)
        
    def execute_trade(self, token: Dict, amount_sol: Decimal) -> bool:
        """Execute a trade for a given token."""
        try:
            # Click on the token row to open trade interface
            token_row = self.driver.find_element(By.XPATH, f"//td[contains(text(), '{token['symbol']}')]/..")
            token_row.click()
            
            # Wait for trade interface to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "trade-interface"))
            )
            
            # Enter amount
            amount_input = self.driver.find_element(By.XPATH, "//input[@type='number']")
            amount_input.clear()
            amount_input.send_keys(str(amount_sol))
            
            # Click buy button
            buy_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Buy')]")
            buy_button.click()
            
            # Wait for transaction confirmation
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Transaction confirmed')]"))
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Trade execution error: {str(e)}")
            return False
            
    def _parse_price(self, price_text: str) -> Decimal:
        """Parse price from text."""
        try:
            return Decimal(price_text.strip().replace('$', '').replace(',', ''))
        except:
            return Decimal('0')
            
    def _parse_market_cap(self, mcap_text: str) -> Decimal:
        """Parse market cap from text."""
        try:
            return Decimal(mcap_text.strip().replace('$', '').replace(',', ''))
        except:
            return Decimal('0')
            
    def _parse_volume(self, volume_text: str) -> Decimal:
        """Parse volume from text."""
        try:
            return Decimal(volume_text.strip().replace('$', '').replace(',', ''))
        except:
            return Decimal('0')
            
    def _parse_holders(self, holders_text: str) -> int:
        """Parse holders count from text."""
        try:
            return int(holders_text.strip().replace(',', ''))
        except:
            return 0
            
    def _check_migration_status(self, row) -> str:
        """Check token migration status."""
        try:
            status_element = row.find_element(By.CLASS_NAME, "migration-status")
            return status_element.text.lower()
        except:
            return "unknown"
            
    def _check_bonding_curve(self, row) -> str:
        """Check position in bonding curve."""
        try:
            curve_element = row.find_element(By.CLASS_NAME, "bonding-curve")
            position = curve_element.get_attribute("data-position")
            return position.lower() if position else "unknown"
        except:
            return "unknown"
            
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
            
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
