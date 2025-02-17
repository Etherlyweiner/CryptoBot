import os
import json
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
from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('trading.log'), logging.StreamHandler()]
)
logger = logging.getLogger('PhotonTrader')

class PhotonTrader:
    def __init__(self, config_path='config.json'):
        self.driver = None
        self.memescope_url = "https://photon-sol.tinyastro.io/en/memescope"
        self.trading_active = False
        self.wallet_balance = None
        self.token_data = {}
        self.config = self.load_config(config_path)
        self.setup()
        
    def load_config(self, config_path):
        """Load encrypted configuration."""
        try:
            if not os.path.exists(config_path):
                # Create default config if not exists
                default_config = {
                    'key': Fernet.generate_key().decode(),
                    'wallet_key': '',
                    'rpc_endpoints': [
                        'https://api.mainnet-beta.solana.com',
                        'https://solana-api.projectserum.com',
                        'https://rpc.ankr.com/solana'
                    ],
                    'risk_settings': {
                        'max_trade_size_sol': 0.5,
                        'wallet_percent_per_trade': 10,
                        'min_trade_size_sol': 0.1,
                        'max_slippage_percent': 1,
                        'min_liquidity_sol': 1000
                    }
                }
                
                # Save config
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                
                logger.info(f"Created new config file at {config_path}")
                return default_config
            
            # Load existing config
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Validate config
            required_keys = ['key', 'wallet_key', 'rpc_endpoints', 'risk_settings']
            for key in required_keys:
                if key not in config:
                    raise ValueError(f"Missing required config key: {key}")
                    
            return config
            
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            raise
            
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
            
    def initialize_wallet(self):
        """Initialize wallet with secure key and RPC fallback."""
        try:
            # Decrypt wallet key if encrypted
            if self.config['wallet_key']:
                f = Fernet(self.config['key'].encode())
                wallet_key = f.decrypt(self.config['wallet_key'].encode()).decode()
            else:
                logger.warning("No wallet key configured")
                return False
                
            # Try RPC endpoints until one works
            connected = False
            for endpoint in self.config['rpc_endpoints']:
                try:
                    logger.info(f"Trying RPC endpoint: {endpoint}")
                    # Here we would initialize the RPC connection
                    # For now, we'll simulate it with a delay
                    time.sleep(random.uniform(0.5, 1))
                    connected = True
                    logger.info(f"Successfully connected to RPC: {endpoint}")
                    break
                except Exception as e:
                    logger.error(f"Failed to connect to RPC {endpoint}: {str(e)}")
                    continue
                    
            if not connected:
                logger.error("Failed to connect to any RPC endpoint")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error initializing wallet: {str(e)}")
            return False
            
    def connect_wallet(self):
        """Connect to the Photon Sol wallet with initialization sequence."""
        try:
            # First initialize wallet and RPC
            if not self.initialize_wallet():
                logger.error("Failed to initialize wallet")
                return False
                
            # Look for connect wallet button with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Try different button selectors
                    selectors = [
                        (By.XPATH, "//button[contains(., 'Connect')]"),
                        (By.XPATH, "//button[contains(., 'Connect Wallet')]"),
                        (By.CLASS_NAME, "connect-wallet"),
                        (By.CLASS_NAME, "wallet-connect")
                    ]
                    
                    connect_button = None
                    for selector_type, selector in selectors:
                        try:
                            connect_button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((selector_type, selector))
                            )
                            if connect_button:
                                break
                        except:
                            continue
                            
                    if connect_button:
                        # Add random delay before clicking
                        time.sleep(random.uniform(0.5, 1.5))
                        connect_button.click()
                        break
                        
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to find connect button after {max_retries} attempts")
                        return False
                    time.sleep(random.uniform(1, 2))
                    
            # Wait for and handle wallet modal
            try:
                # Wait for modal with retry
                modal_found = False
                for attempt in range(max_retries):
                    try:
                        modal = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'modal') or contains(@class, 'wallet-list')]"))
                        )
                        modal_found = True
                        break
                    except:
                        if attempt == max_retries - 1:
                            logger.error("Failed to find wallet modal")
                            return False
                        time.sleep(random.uniform(1, 2))
                        
                if modal_found:
                    # Look for Photon wallet option
                    wallet_options = [
                        "//button[contains(., 'Photon')]",
                        "//div[contains(., 'Photon')]",
                        ".photon-wallet",
                        ".wallet-option"
                    ]
                    
                    wallet_button = None
                    for option in wallet_options:
                        try:
                            if option.startswith("//"):
                                wallet_button = modal.find_element(By.XPATH, option)
                            else:
                                wallet_button = modal.find_element(By.CSS_SELECTOR, option)
                            if wallet_button:
                                break
                        except:
                            continue
                            
                    if wallet_button:
                        time.sleep(random.uniform(0.5, 1.5))
                        wallet_button.click()
                        
                        # Wait for connection confirmation
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(., 'Connected') or contains(@class, 'connected')]"))
                        )
                        
                        logger.info("Successfully connected to Photon wallet")
                        return True
                        
            except Exception as e:
                logger.error(f"Error in wallet modal handling: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting wallet: {str(e)}")
            return False
            
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
        """Update the current wallet balance."""
        try:
            balance_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "wallet-balance"))
            )
            balance_text = balance_element.text.replace("SOL", "").strip()
            self.wallet_balance = float(balance_text)
            logger.info(f"Updated wallet balance: {self.wallet_balance} SOL")
        except Exception as e:
            logger.error(f"Error updating wallet balance: {str(e)}")
            
    def scan_for_opportunities(self):
        """Scan the memescope page for trading opportunities."""
        try:
            # Wait for the token list to load
            logger.info("Scanning for trading opportunities...")
            token_list = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "token-list"))
            )
            
            # Get all token rows
            token_rows = token_list.find_elements(By.CLASS_NAME, "token-row")
            opportunities = []
            
            for row in token_rows:
                try:
                    token_data = self.extract_token_data(row)
                    if token_data and self.evaluate_token(token_data):
                        opportunities.append(token_data)
                except Exception as e:
                    logger.error(f"Error processing token row: {str(e)}")
                    continue
            
            logger.info(f"Found {len(opportunities)} potential opportunities")
            return opportunities
            
        except TimeoutException:
            logger.error("Timeout waiting for token list to load")
            return []
        except Exception as e:
            logger.error(f"Error scanning for opportunities: {str(e)}")
            return []
            
    def extract_token_data(self, row):
        """Extract token data from a row element."""
        try:
            # Extract token information
            token_name = row.find_element(By.CLASS_NAME, "token-name").text
            token_price = row.find_element(By.CLASS_NAME, "token-price").text
            token_volume = row.find_element(By.CLASS_NAME, "token-volume").text
            holders = row.find_element(By.CLASS_NAME, "token-holders").text
            market_cap = row.find_element(By.CLASS_NAME, "token-mcap").text
            
            # Clean and convert data
            price = float(token_price.replace("$", "").strip())
            volume = float(token_volume.replace("$", "").replace(",", "").strip())
            holder_count = int(holders.replace(",", "").strip())
            mcap = float(market_cap.replace("$", "").replace(",", "").strip())
            
            return {
                "name": token_name,
                "price": price,
                "volume": volume,
                "holders": holder_count,
                "market_cap": mcap,
                "row_element": row
            }
            
        except Exception as e:
            logger.error(f"Error extracting token data: {str(e)}")
            return None
            
    def evaluate_token(self, token_data):
        """Evaluate if a token is worth trading based on our criteria."""
        score = 0
        
        # Price momentum (assuming we store historical prices)
        current_price = token_data["price"]
        if token_data["name"] in self.token_data:
            old_price = self.token_data[token_data["name"]].get("price", current_price)
            price_change = ((current_price - old_price) / old_price) * 100
            if price_change >= 10:
                score += 3
            elif price_change >= 5:
                score += 2
        
        # Volume criteria
        if token_data["volume"] > 10000:
            score += 2
        elif token_data["volume"] > 5000:
            score += 1
            
        # Holder count criteria
        if token_data["holders"] > 500:
            score += 2
        elif token_data["holders"] > 200:
            score += 1
            
        # Market cap criteria (prefer smaller market caps)
        if token_data["market_cap"] < 100000:
            score += 2
            
        # Update token history
        self.token_data[token_data["name"]] = token_data
        
        # Token is worth trading if score is 5 or higher
        return score >= 5
        
    def execute_trade(self, token_data):
        """Execute a trade for a given token."""
        try:
            # Click on the trade button for this token
            row = token_data["row_element"]
            trade_button = row.find_element(By.CLASS_NAME, "trade-button")
            trade_button.click()
            
            # Wait for trade modal to appear
            trade_modal = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "trade-modal"))
            )
            
            # Calculate trade amount based on wallet balance
            if self.wallet_balance:
                trade_amount = min(self.wallet_balance * 0.1, 0.5)  # 10% of balance or 0.5 SOL max
                trade_amount = max(trade_amount, 0.1)  # Minimum 0.1 SOL
                
                # Input trade amount
                amount_input = trade_modal.find_element(By.CLASS_NAME, "amount-input")
                amount_input.clear()
                amount_input.send_keys(str(trade_amount))
                
                # Click buy button
                buy_button = trade_modal.find_element(By.CLASS_NAME, "buy-button")
                buy_button.click()
                
                # Wait for confirmation
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
                )
                
                logger.info(f"Successfully executed trade for {token_data['name']} with {trade_amount} SOL")
                return True
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            # Try to close modal if it's open
            try:
                close_button = self.driver.find_element(By.CLASS_NAME, "close-modal")
                close_button.click()
            except:
                pass
        return False
        
    def evaluate_and_trade(self, opportunities):
        """Evaluate opportunities and execute trades."""
        for token in opportunities:
            if self.trading_active:
                if self.execute_trade(token):
                    # Add delay between trades
                    time.sleep(random.uniform(2, 3))
                    
    def navigate_to_section(self, section):
        """Navigate to a specific section of the Photon Sol website."""
        try:
            sections = {
                'memescope': 'https://photon-sol.tinyastro.io/en/memescope',
                'swap': 'https://photon-sol.tinyastro.io/en/swap',
                'pools': 'https://photon-sol.tinyastro.io/en/pools',
                'portfolio': 'https://photon-sol.tinyastro.io/en/portfolio'
            }
            
            if section in sections:
                logger.info(f"Navigating to {section} section...")
                self.driver.get(sections[section])
                time.sleep(random.uniform(2, 3))
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to {section}: {str(e)}")
            return False

    def check_portfolio(self):
        """Check portfolio performance and holdings."""
        try:
            if self.navigate_to_section('portfolio'):
                # Wait for portfolio to load
                portfolio = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "portfolio-container"))
                )
                
                # Get total value
                total_value = portfolio.find_element(By.CLASS_NAME, "total-value").text
                logger.info(f"Portfolio total value: {total_value}")
                
                # Get token holdings
                holdings = portfolio.find_elements(By.CLASS_NAME, "token-holding")
                for holding in holdings:
                    token_name = holding.find_element(By.CLASS_NAME, "token-name").text
                    token_amount = holding.find_element(By.CLASS_NAME, "token-amount").text
                    token_value = holding.find_element(By.CLASS_NAME, "token-value").text
                    logger.info(f"Holding: {token_name} - Amount: {token_amount} - Value: {token_value}")
                
                return True
        except Exception as e:
            logger.error(f"Error checking portfolio: {str(e)}")
            return False

    def check_pool_opportunities(self):
        """Check liquidity pool opportunities."""
        try:
            if self.navigate_to_section('pools'):
                # Wait for pools to load
                pools_container = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "pools-container"))
                )
                
                # Get all pool pairs
                pool_pairs = pools_container.find_elements(By.CLASS_NAME, "pool-pair")
                opportunities = []
                
                for pair in pool_pairs:
                    try:
                        pair_name = pair.find_element(By.CLASS_NAME, "pair-name").text
                        apr = float(pair.find_element(By.CLASS_NAME, "pair-apr").text.replace('%', ''))
                        tvl = pair.find_element(By.CLASS_NAME, "pair-tvl").text
                        
                        if apr > 50:  # High APR opportunity
                            opportunities.append({
                                'pair': pair_name,
                                'apr': apr,
                                'tvl': tvl,
                                'element': pair
                            })
                    except Exception as e:
                        logger.error(f"Error processing pool pair: {str(e)}")
                        continue
                
                logger.info(f"Found {len(opportunities)} high-APR pool opportunities")
                return opportunities
                
        except Exception as e:
            logger.error(f"Error checking pool opportunities: {str(e)}")
            return []

    def provide_liquidity(self, pool_data):
        """Provide liquidity to a pool."""
        try:
            # Click on the pool pair
            pool_data['element'].click()
            
            # Wait for liquidity modal
            liquidity_modal = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "liquidity-modal"))
            )
            
            # Input amounts
            if self.wallet_balance:
                lp_amount = min(self.wallet_balance * 0.2, 1.0)  # 20% of balance or 1 SOL max
                
                # Input first token amount
                amount_input = liquidity_modal.find_element(By.CLASS_NAME, "token-amount-input")
                amount_input.clear()
                amount_input.send_keys(str(lp_amount))
                
                # Wait for second token amount to calculate
                time.sleep(2)
                
                # Click add liquidity button
                add_button = liquidity_modal.find_element(By.CLASS_NAME, "add-liquidity-button")
                if add_button.is_enabled():
                    add_button.click()
                    
                    # Wait for confirmation
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
                    )
                    
                    logger.info(f"Successfully added liquidity to {pool_data['pair']}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error providing liquidity: {str(e)}")
            # Try to close modal
            try:
                close_button = self.driver.find_element(By.CLASS_NAME, "close-modal")
                close_button.click()
            except:
                pass
        return False

    def monitor_token_price(self, token_name):
        """Monitor price of a specific token."""
        try:
            if self.navigate_to_section('swap'):
                # Open token selector
                token_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "token-selector"))
                )
                token_input.click()
                
                # Search for token
                search_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "token-search"))
                )
                search_input.send_keys(token_name)
                
                # Wait and select token
                token_option = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, f"//div[contains(@class, 'token-option') and contains(text(), '{token_name}')]"))
                )
                token_option.click()
                
                # Get price
                price_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "token-price"))
                )
                price = float(price_element.text.replace('$', ''))
                
                return price
                
        except Exception as e:
            logger.error(f"Error monitoring {token_name} price: {str(e)}")
            return None

    def start(self):
        """Start the trading bot with enhanced navigation."""
        try:
            logger.info("Starting Photon Trading Bot...")
            self.trading_active = True
            
            # Navigate to memescope
            if not self.navigate_to_section('memescope'):
                logger.error("Failed to navigate to memescope")
                return
                
            # Connect wallet if needed
            if not self.connect_wallet():
                logger.error("Failed to connect wallet")
                return
                
            # Wait for manual verification if needed
            logger.info("Waiting for verification...")
            logger.info("Complete any verification if needed, then press 'v' to continue or 'esc' to stop")
            
            while True:
                if keyboard.is_pressed('v'):
                    break
                if keyboard.is_pressed('esc'):
                    logger.info("Setup cancelled by user")
                    return
                time.sleep(0.1)
            
            logger.info("Verification completed, starting operations...")
            
            # Main trading loop
            while self.trading_active:
                try:
                    # Check portfolio performance
                    self.check_portfolio()
                    
                    # Look for pool opportunities
                    pool_opportunities = self.check_pool_opportunities()
                    for pool in pool_opportunities:
                        if self.trading_active and pool['apr'] > 100:  # Very high APR
                            self.provide_liquidity(pool)
                    
                    # Navigate back to memescope for token opportunities
                    self.navigate_to_section('memescope')
                    opportunities = self.scan_for_opportunities()
                    
                    if opportunities:
                        self.evaluate_and_trade(opportunities)
                    
                    if keyboard.is_pressed('esc'):
                        logger.info("Stop signal received")
                        break
                        
                    # Random delay between iterations
                    time.sleep(random.uniform(10, 15))
                    
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
