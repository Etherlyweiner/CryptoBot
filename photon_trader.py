import time
import logging
import pyautogui
import keyboard
import random
import undetected_chromedriver as uc
from decimal import Decimal
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('trading.log'), logging.StreamHandler()]
)
logger = logging.getLogger('PhotonTrader')

class PhotonTrader:
    def __init__(self):
        self.driver = None
        self.memescope_url = "https://photon-sol.tinyastro.io/en/memescope"
        self.trading_active = False
        self.wallet_balance = None
        self.token_data = {}
        self.setup()
        
    def setup(self):
        """Initialize the trading bot with undetected-chromedriver."""
        try:
            # Configure PyAutoGUI
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5
            
            # Initialize undetected-chromedriver
            options = uc.ChromeOptions()
            
            # Add some basic options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-dev-shm-usage')
            
            # Random window size
            width = random.randint(1200, 1600)
            height = random.randint(800, 1000)
            options.add_argument(f'--window-size={width},{height}')
            
            # Initialize the driver with specific version
            self.driver = uc.Chrome(
                options=options,
                version_main=132  # Match your installed Chrome version
            )
            
            logger.info("Successfully initialized undetected-chromedriver")
            
        except Exception as e:
            logger.error(f"Failed to setup browser: {str(e)}")
            raise
            
    def wait_for_element(self, by, value, timeout=10):
        """Wait for an element to be visible."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Timeout waiting for element: {value}")
            return None
            
    def update_wallet_balance(self):
        """Update current wallet balance from Photon's interface."""
        try:
            # Wait for the wallet balance element
            balance_elem = self.wait_for_element(By.CLASS_NAME, "wallet-balance")
            if balance_elem:
                balance_text = balance_elem.text.replace('SOL', '').strip()
                self.wallet_balance = Decimal(balance_text)
                logger.info(f"Wallet balance: {self.wallet_balance} SOL")
            else:
                logger.warning("Could not find wallet balance element")
        except Exception as e:
            logger.error(f"Error updating wallet balance: {str(e)}")
            
    def scan_for_opportunities(self):
        """Scan memescope for trading opportunities."""
        opportunities = []
        try:
            # Wait for token table to load
            table = self.wait_for_element(By.CLASS_NAME, "token-table")
            if not table:
                logger.warning("Could not find token table")
                return opportunities
                
            # Find all token rows
            rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
            logger.info(f"Found {len(rows)} tokens to analyze")
            
            for row in rows:
                try:
                    token_data = self.parse_token_row(row)
                    if token_data:
                        score = self.calculate_opportunity_score(token_data)
                        if score >= 5:  # Only include high-scoring opportunities
                            token_data['score'] = score
                            opportunities.append(token_data)
                except Exception as e:
                    logger.error(f"Error parsing token row: {str(e)}")
                    continue
                    
            return sorted(opportunities, key=lambda x: x['score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error scanning opportunities: {str(e)}")
            return opportunities
            
    def parse_token_row(self, row):
        """Parse a token row from the memescope table."""
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 6:
                return None
                
            return {
                'name': cells[0].text,
                'price': Decimal(cells[1].text.replace('$', '')),
                'market_cap': Decimal(cells[2].text.replace('$', '').replace(',', '')),
                'volume': Decimal(cells[3].text.replace('$', '').replace(',', '')),
                'holders': int(cells[4].text.replace(',', '')),
                'price_change': Decimal(cells[5].text.replace('%', ''))
            }
        except Exception as e:
            logger.error(f"Error parsing row: {str(e)}")
            return None
            
    def calculate_opportunity_score(self, token):
        """Calculate opportunity score based on token metrics."""
        score = 0
        
        # Price momentum
        if token['price_change'] >= 10:
            score += 3
        elif token['price_change'] >= 5:
            score += 2
            
        # Trading volume
        if token['volume'] >= 10000:
            score += 2
        elif token['volume'] >= 5000:
            score += 1
            
        # Holder count
        if token['holders'] >= 500:
            score += 2
        elif token['holders'] >= 200:
            score += 1
            
        # Market cap (prefer smaller caps)
        if token['market_cap'] <= 100000:
            score += 2
            
        return score
        
    def evaluate_and_trade(self, opportunities):
        """Evaluate opportunities and execute trades."""
        if not opportunities or not self.wallet_balance:
            return
            
        for token in opportunities:
            try:
                if token['score'] >= 5:  # Minimum score threshold
                    # Calculate position size (10% of wallet)
                    position_size = min(
                        self.wallet_balance * Decimal('0.1'),  # 10% of wallet
                        Decimal('0.5')  # Max 0.5 SOL per trade
                    )
                    
                    if position_size >= Decimal('0.1'):  # Minimum trade size
                        logger.info(f"Trading opportunity found: {token['name']}")
                        logger.info(f"Score: {token['score']}, Position size: {position_size} SOL")
                        self.execute_trade(token, position_size)
                        
            except Exception as e:
                logger.error(f"Error evaluating trade: {str(e)}")
                continue
                
    def execute_trade(self, token, position_size):
        """Execute a trade on Photon."""
        try:
            # Find and click the trade button for this token
            trade_button = self.driver.find_element(By.XPATH, 
                f"//tr[contains(., '{token['name']}')]//button[contains(@class, 'trade-button')]")
            trade_button.click()
            time.sleep(1)
            
            # Input the amount
            amount_input = self.wait_for_element(By.CLASS_NAME, "trade-amount-input")
            if amount_input:
                amount_input.clear()
                amount_input.send_keys(str(position_size))
                
                # Click the swap button
                swap_button = self.wait_for_element(By.CLASS_NAME, "swap-button")
                if swap_button and swap_button.is_enabled():
                    swap_button.click()
                    logger.info(f"Trade executed: {position_size} SOL for {token['name']}")
                    time.sleep(2)  # Wait for transaction
                    
                    # Close the trade modal
                    close_button = self.wait_for_element(By.CLASS_NAME, "close-modal")
                    if close_button:
                        close_button.click()
                        
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            
    def start(self):
        """Start the trading bot."""
        try:
            logger.info("Starting Photon Trading Bot...")
            self.trading_active = True
            
            # Navigate to memescope with random delays
            logger.info(f"Navigating to {self.memescope_url}")
            self.driver.get(self.memescope_url)
            time.sleep(random.uniform(2, 4))
            
            # Wait for manual verification
            logger.info("Waiting for manual verification...")
            logger.info("Complete any verification if needed, then press 'v' to continue or 'esc' to stop")
            
            while True:
                if keyboard.is_pressed('v'):
                    break
                if keyboard.is_pressed('esc'):
                    logger.info("Setup cancelled by user")
                    return
                time.sleep(0.1)
            
            logger.info("Verification completed, starting trading operations...")
            time.sleep(random.uniform(1, 2))
            
            # Main trading loop
            while self.trading_active:
                try:
                    self.update_wallet_balance()
                    opportunities = self.scan_for_opportunities()
                    
                    if opportunities:
                        self.evaluate_and_trade(opportunities)
                    
                    if keyboard.is_pressed('esc'):
                        logger.info("Stop signal received")
                        break
                        
                    # Random delay between iterations
                    time.sleep(random.uniform(1.5, 2.5))
                    
                except Exception as e:
                    logger.error(f"Error in trading loop: {str(e)}")
                    time.sleep(random.uniform(4, 6))
                    
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Critical error: {str(e)}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
            logger.info("Bot stopped, resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            
if __name__ == "__main__":
    trader = PhotonTrader()
    trader.start()
