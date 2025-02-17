import os
import json
import time
import logging
import pyautogui
import keyboard
import random
import yaml
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
    def __init__(self, config_path='config/config.yaml'):
        """Initialize the trading bot with configuration."""
        try:
            # Load configuration
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Initialize base URL and endpoints
            self.base_url = "https://photon-sol.tinyastro.io"
            self.memescope_url = f"{self.base_url}/en/memescope"
            
            # Initialize trading state
            self.trading_active = False
            
            # Set up the browser
            self.setup()
            
        except Exception as e:
            logger.error(f"Failed to initialize trader: {str(e)}")
            raise

    def load_config(self, config_path):
        """Load configuration from YAML file."""
        try:
            if not os.path.exists(config_path):
                raise ValueError(f"Config file not found: {config_path}")
                
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Validate required sections
            required_sections = ['wallet', 'network', 'rpc', 'risk']
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Missing required config section: {section}")
                    
            return config
            
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            raise
            
    def setup(self):
        """Set up the browser with stealth settings."""
        try:
            # Configure Chrome options
            chrome_options = uc.ChromeOptions()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            # Set up persistent profile
            user_data_dir = os.path.abspath("chrome_data")
            if not os.path.exists(user_data_dir):
                os.makedirs(user_data_dir)
            chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
            
            # Initialize browser with retry mechanism
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    self.driver = uc.Chrome(
                        options=chrome_options,
                        driver_executable_path=None,  # Let it auto-download
                        browser_executable_path=None,  # Auto-detect Chrome
                        version_main=None,  # Auto-detect version
                        suppress_welcome=True
                    )
                    
                    # Set page load timeout
                    self.driver.set_page_load_timeout(30)
                    
                    # Test browser is working
                    self.driver.get("about:blank")
                    time.sleep(1)
                    
                    # Add window handle check
                    if not self.driver.current_window_handle:
                        raise Exception("No valid window handle")
                    
                    logger.info("Successfully initialized browser session")
                    break
                    
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Browser initialization attempt {retry_count} failed: {str(e)}")
                    
                    if retry_count < max_retries:
                        logger.info("Retrying browser initialization...")
                        time.sleep(5)  # Wait before retry
                        
                        # Clean up failed instance
                        try:
                            if hasattr(self, 'driver'):
                                self.driver.quit()
                        except:
                            pass
                    else:
                        raise Exception(f"Failed to initialize browser after {max_retries} attempts")
            
        except Exception as e:
            logger.error(f"Failed to set up browser: {str(e)}")
            raise

    def cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'driver'):
                # Check if browser is still responding
                try:
                    # Only quit if we can still interact with the browser
                    if self.driver.current_window_handle:
                        self.driver.quit()
                except:
                    logger.warning("Browser already closed or unresponsive")
                    
                # Clear reference
                self.driver = None
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()

    def check_browser_alive(self):
        """Check if browser is still alive and responsive."""
        try:
            if not hasattr(self, 'driver'):
                return False
                
            # Try to get window handle
            self.driver.current_window_handle
            return True
            
        except:
            return False
            
    def ensure_browser_alive(self):
        """Ensure browser is alive, restart if needed."""
        if not self.check_browser_alive():
            logger.warning("Browser not responsive, attempting restart...")
            self.cleanup()
            self.setup()
            return True
        return False
            
    def check_wallet_connection(self):
        """Check if wallet is already connected."""
        try:
            # Check for wallet connection using JavaScript
            wallet_check_js = """
                return (function() {
                    const elements = document.querySelectorAll('*');
                    for (const el of elements) {
                        const text = el.textContent.toLowerCase();
                        if (text.includes('disconnect') || text.includes('connected')) {
                            return true;
                        }
                    }
                    return false;
                })();
            """
            
            return self.driver.execute_script(wallet_check_js)
            
        except Exception as e:
            logger.error(f"Error checking wallet connection: {str(e)}")
            return False
            
    def initialize_wallet(self):
        """Initialize wallet with secure key and RPC fallback."""
        try:
            # Get wallet configuration
            wallet_config = self.config.get('wallet', {})
            if not wallet_config.get('primary_address'):
                logger.warning("No primary wallet address configured")
                return False
                
            # Try RPC endpoints until one works
            connected = False
            rpc_config = self.config.get('rpc', {})
            
            # Try primary endpoint first
            if rpc_config.get('primary'):
                try:
                    logger.info(f"Trying primary RPC endpoint...")
                    time.sleep(random.uniform(0.5, 1))
                    connected = True
                    logger.info("Successfully connected to primary RPC")
                except Exception as e:
                    logger.error(f"Failed to connect to primary RPC: {str(e)}")
            
            # Try fallbacks if primary failed
            if not connected and rpc_config.get('fallbacks'):
                for endpoint in rpc_config['fallbacks']:
                    try:
                        logger.info(f"Trying fallback RPC endpoint: {endpoint}")
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
                
            # Add random delay before clicking
            time.sleep(random.uniform(2, 3))
            
            # Try to find and click the connect button using JavaScript
            connect_button_js = """
                return (function() {
                    // Try different selectors
                    const selectors = [
                        'button:not([disabled]):not([aria-hidden="true"]):not([style*="display: none"]):not([style*="visibility: hidden"])',
                        '[role="button"]',
                        '.wallet-adapter-button'
                    ];
                    
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (el.textContent.toLowerCase().includes('connect') &&
                                getComputedStyle(el).display !== 'none' &&
                                getComputedStyle(el).visibility !== 'hidden') {
                                return el;
                            }
                        }
                    }
                    return null;
                })();
            """
            
            connect_button = self.driver.execute_script(connect_button_js)
            if not connect_button:
                logger.error("Could not find connect button")
                return False
                
            # Click using JavaScript for better reliability
            self.driver.execute_script("arguments[0].click();", connect_button)
            logger.info("Clicked connect button using JavaScript")
            
            # Wait for wallet modal
            time.sleep(random.uniform(2, 3))
            
            # Try to find and click the Phantom wallet option using JavaScript
            phantom_button_js = """
                return (function() {
                    const selectors = [
                        '.wallet-adapter-modal-list button',
                        '.wallet-adapter-modal-list [role="button"]'
                    ];
                    
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (el.textContent.toLowerCase().includes('phantom') &&
                                getComputedStyle(el).display !== 'none' &&
                                getComputedStyle(el).visibility !== 'hidden') {
                                return el;
                            }
                        }
                    }
                    return null;
                })();
            """
            
            phantom_button = self.driver.execute_script(phantom_button_js)
            if not phantom_button:
                logger.error("Could not find Phantom wallet option")
                return False
                
            # Click Phantom option using JavaScript
            self.driver.execute_script("arguments[0].click();", phantom_button)
            logger.info("Selected Phantom wallet using JavaScript")
            
            # Wait for connection confirmation
            time.sleep(random.uniform(3, 4))
            
            # Check connection status using JavaScript
            connection_check_js = """
                return (function() {
                    const selectors = [
                        '.wallet-adapter-button-trigger',
                        '.wallet-adapter-connected'
                    ];
                    
                    for (const selector of selectors) {
                        const el = document.querySelector(selector);
                        if (el && el.textContent.toLowerCase().includes('connect')) {
                            return false;
                        }
                    }
                    return true;
                })();
            """
            
            connected = self.driver.execute_script(connection_check_js)
            if connected:
                logger.info("Successfully connected Phantom wallet")
                return True
            else:
                logger.error("Could not confirm wallet connection")
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

    def navigate_to_memescope(self):
        """Navigate to the memescope section and verify we're there."""
        try:
            logger.info("Navigating to memescope section...")
            
            # Try different URL variations
            urls_to_try = [
                f"{self.base_url}/en/memescope",
                f"{self.base_url}/memescope",
                self.base_url  # Base URL as fallback
            ]
            
            success = False
            for url in urls_to_try:
                try:
                    if not self.driver.current_url.endswith(url.split(self.base_url)[1]):
                        self.driver.get(url)
                        time.sleep(random.uniform(2, 3))
                    
                    # Verify we're on memescope by checking for key elements
                    memescope_check_js = """
                        return (function() {
                            // Look for memescope-specific elements
                            const indicators = [
                                'memescope',
                                'token',
                                'market',
                                'volume',
                                'price',
                                'search'
                            ];
                            
                            // Check text content
                            const pageText = document.body.textContent.toLowerCase();
                            const hasIndicators = indicators.some(indicator => pageText.includes(indicator));
                            
                            // Check for typical UI elements
                            const hasTable = document.querySelector('table') !== null;
                            const hasSearchInput = document.querySelector('input[type="text"], input[type="search"]') !== null;
                            
                            return hasIndicators && (hasTable || hasSearchInput);
                        })();
                    """
                    
                    is_on_memescope = self.driver.execute_script(memescope_check_js)
                    
                    if is_on_memescope:
                        success = True
                        break
                    
                except Exception as e:
                    logger.warning(f"Failed to navigate to {url}: {str(e)}")
                    continue
            
            if success:
                logger.info("Successfully navigated to memescope")
                return True
            else:
                # Try clicking memescope link as last resort
                try:
                    memescope_js = """
                        return (function() {
                            const links = Array.from(document.querySelectorAll('a'));
                            return links.find(link => 
                                link.textContent.toLowerCase().includes('memescope') ||
                                link.href.toLowerCase().includes('memescope') ||
                                link.href.toLowerCase().includes('token')
                            );
                        })();
                    """
                    
                    memescope_link = self.driver.execute_script(memescope_js)
                    if memescope_link:
                        self.driver.execute_script("arguments[0].click();", memescope_link)
                        time.sleep(random.uniform(2, 3))
                        
                        # Check again
                        is_on_memescope = self.driver.execute_script(memescope_check_js)
                        if is_on_memescope:
                            logger.info("Successfully navigated to memescope via link")
                            return True
                
                except Exception as e:
                    logger.error(f"Failed to click memescope link: {str(e)}")
                
                logger.error("Could not navigate to memescope page")
                return False
            
        except Exception as e:
            logger.error(f"Failed to navigate to memescope: {str(e)}")
            return False
            
    def scan_tokens(self):
        """Scan for new meme tokens and return their data."""
        try:
            logger.info("Scanning for new tokens...")
            
            # Wait longer for content to load and try to ensure we're on the right page
            time.sleep(random.uniform(5, 7))
            
            # First check if we're on the right page and log the page structure
            page_check_js = r"""
                return (function() {
                    const pageInfo = {
                        url: window.location.href,
                        title: document.title,
                        bodyText: document.body.textContent.substring(0, 200),
                        elementCounts: {
                            tables: document.getElementsByTagName('table').length,
                            divs: document.getElementsByTagName('div').length,
                            links: document.getElementsByTagName('a').length
                        }
                    };
                    return pageInfo;
                })();
            """
            
            page_info = self.driver.execute_script(page_check_js)
            logger.info(f"Page Info: URL={page_info['url']}, Title={page_info['title']}")
            logger.info(f"Element Counts: {page_info['elementCounts']}")
            logger.info(f"Page Preview: {page_info['bodyText']}")
            
            # More robust token scanning using JavaScript
            token_data_js = r"""
                return (function() {
                    const tokens = [];
                    const debug = [];
                    
                    // Helper function to clean text
                    function cleanText(text) {
                        return text.replace(/^\s+|\s+$/g, '').replace(/\s+/g, ' ');
                    }
                    
                    // Helper function to check if text contains token indicators
                    function hasTokenIndicators(text) {
                        text = text.toLowerCase();
                        return text.includes('token') || text.includes('price') || 
                               text.includes('volume') || text.includes('market') ||
                               text.includes('$') || text.includes('sol');
                    }
                    
                    // Try different ways to find token data
                    function findTokenElements() {
                        let elements = [];
                        
                        // Method 1: Look for table rows
                        const tables = document.querySelectorAll('table');
                        tables.forEach(table => {
                            if (hasTokenIndicators(table.textContent)) {
                                const rows = table.querySelectorAll('tr');
                                elements.push(...Array.from(rows));
                                debug.push(`Found table with ${rows.length} rows`);
                            }
                        });
                        
                        // Method 2: Look for list items
                        const lists = document.querySelectorAll('ul, ol');
                        lists.forEach(list => {
                            if (hasTokenIndicators(list.textContent)) {
                                const items = list.querySelectorAll('li');
                                elements.push(...Array.from(items));
                                debug.push(`Found list with ${items.length} items`);
                            }
                        });
                        
                        // Method 3: Look for grid items
                        const grids = document.querySelectorAll('div[role="grid"]');
                        grids.forEach(grid => {
                            if (hasTokenIndicators(grid.textContent)) {
                                const rows = grid.querySelectorAll('div[role="row"]');
                                elements.push(...Array.from(rows));
                                debug.push(`Found grid with ${rows.length} rows`);
                            }
                        });
                        
                        // Method 4: Look for card-like elements
                        ['token', 'card', 'item', 'row'].forEach(className => {
                            const cards = document.querySelectorAll(`div[class*="${className}"]`);
                            if (cards.length > 0) {
                                elements.push(...Array.from(cards));
                                debug.push(`Found ${cards.length} elements with class containing "${className}"`);
                            }
                        });
                        
                        // Method 5: Look for any elements with price/volume info
                        const allElements = document.querySelectorAll('*');
                        const tokenElements = Array.from(allElements).filter(el => 
                            hasTokenIndicators(el.textContent) && 
                            !elements.includes(el)
                        );
                        
                        if (tokenElements.length > 0) {
                            elements.push(...tokenElements);
                            debug.push(`Found ${tokenElements.length} elements with token indicators`);
                        }
                        
                        return { elements, debug };
                    }
                    
                    // Find token elements
                    const { elements, debug: findDebug } = findTokenElements();
                    debug.push(...findDebug);
                    
                    // Extract data from elements
                    elements.forEach((element, index) => {
                        try {
                            const elementText = cleanText(element.textContent);
                            debug.push(`Processing element ${index}: ${elementText.substring(0, 100)}`);
                            
                            // Skip header rows and elements with too little text
                            if (elementText.length < 5 || 
                                (elementText.toLowerCase().includes('price') && 
                                 elementText.toLowerCase().includes('volume') && 
                                 elementText.toLowerCase().includes('market'))) {
                                return;
                            }
                            
                            let token = {
                                name: '',
                                price: '',
                                volume: '',
                                marketCap: ''
                            };
                            
                            // Try to extract data using various patterns
                            const patterns = {
                                price: [
                                    /\$([0-9,.]+)/,
                                    /price:?\s*\$?([0-9,.]+)/i,
                                    /([0-9,.]+)\s*(?:USD|SOL)/i
                                ],
                                volume: [
                                    /volume:?\s*\$?([0-9,.]+[KMBkmb]?)/i,
                                    /(?:24h|daily)?\s*vol(?:ume)?:?\s*\$?([0-9,.]+[KMBkmb]?)/i
                                ],
                                marketCap: [
                                    /market\s*cap:?\s*\$?([0-9,.]+[KMBkmb]?)/i,
                                    /mcap:?\s*\$?([0-9,.]+[KMBkmb]?)/i
                                ]
                            };
                            
                            // Extract name (usually at the start, before any numbers)
                            const nameMatch = elementText.match(/^([^$0-9]+)/);
                            if (nameMatch) {
                                token.name = cleanText(nameMatch[1]);
                            }
                            
                            // Try each pattern for price, volume, and market cap
                            Object.entries(patterns).forEach(([field, fieldPatterns]) => {
                                for (const pattern of fieldPatterns) {
                                    const match = elementText.match(pattern);
                                    if (match) {
                                        token[field] = match[1];
                                        break;
                                    }
                                }
                            });
                            
                            // Only add if we have meaningful data
                            if (token.name && (token.price || token.volume || token.marketCap)) {
                                // Deduplicate based on name
                                if (!tokens.some(t => t.name === token.name)) {
                                    tokens.push(token);
                                    debug.push(`Added token: ${JSON.stringify(token)}`);
                                }
                            }
                        } catch (err) {
                            debug.push(`Error processing element ${index}: ${err.message}`);
                        }
                    });
                    
                    return { tokens, debug };
                })();
            """
            
            # Execute the token scanning JavaScript
            result = self.driver.execute_script(token_data_js)
            tokens = result['tokens']
            debug_info = result['debug']
            
            # Log debug information
            logger.info("Token scanning debug info:")
            for debug_msg in debug_info:
                logger.info(f"Debug: {debug_msg}")
            
            if tokens and len(tokens) > 0:
                logger.info(f"Found {len(tokens)} tokens")
                # Log first few tokens for debugging
                for i, token in enumerate(tokens[:3]):
                    logger.info(f"Token {i+1}: {token['name']} - {token['price']}")
                return tokens
            else:
                # Try scrolling and scanning again
                logger.warning("No tokens found, trying to scroll...")
                scroll_js = """
                    window.scrollTo(0, document.body.scrollHeight);
                    return document.body.scrollHeight;
                """
                scroll_height = self.driver.execute_script(scroll_js)
                logger.info(f"Scrolled to height: {scroll_height}")
                time.sleep(3)
                
                # Take screenshot for debugging
                try:
                    screenshot_path = "debug_screenshot.png"
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"Saved debug screenshot to {screenshot_path}")
                except Exception as e:
                    logger.warning(f"Failed to save screenshot: {str(e)}")
                
                # Scan again after scrolling
                result = self.driver.execute_script(token_data_js)
                tokens = result['tokens']
                debug_info = result['debug']
                
                # Log debug information after scroll
                logger.info("Token scanning debug info after scroll:")
                for debug_msg in debug_info:
                    logger.info(f"Debug: {debug_msg}")
                
                if tokens and len(tokens) > 0:
                    logger.info(f"Found {len(tokens)} tokens after scrolling")
                    for i, token in enumerate(tokens[:3]):
                        logger.info(f"Token {i+1}: {token['name']} - {token['price']}")
                    return tokens
                else:
                    logger.warning("No tokens found in the scan")
                    return []
            
        except Exception as e:
            logger.error(f"Failed to scan tokens: {str(e)}")
            if hasattr(e, 'msg'):
                logger.error(f"Error message: {e.msg}")
            return []
            
    def select_token(self, token_name):
        """Select a specific token for trading."""
        try:
            logger.info(f"Selecting token: {token_name}")
            
            # Search for token using JavaScript
            search_token_js = f"""
                return (function() {{
                    const searchInputs = document.querySelectorAll('input[type="text"], input[type="search"]');
                    for (const input of searchInputs) {{
                        if (input.placeholder && 
                            (input.placeholder.toLowerCase().includes('search') ||
                             input.placeholder.toLowerCase().includes('token'))) {{
                            return input;
                        }}
                    }}
                    return null;
                }})();
            """
            
            search_input = WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script(search_token_js)
            )
            
            if not search_input:
                raise Exception("Could not find search input")
            
            # Clear and enter token name
            self.driver.execute_script(
                "arguments[0].value = arguments[1]; " +
                "arguments[0].dispatchEvent(new Event('input')); " +
                "arguments[0].dispatchEvent(new Event('change'));",
                search_input, token_name
            )
            
            time.sleep(random.uniform(1, 2))
            
            # Click token from results
            select_token_js = f"""
                return (function() {{
                    const elements = document.querySelectorAll('*');
                    for (const el of elements) {{
                        if (el.textContent.toLowerCase().includes('{token_name.lower()}')) {{
                            return el;
                        }}
                    }}
                    return null;
                }})();
            """
            
            token_element = WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script(select_token_js)
            )
            
            if not token_element:
                raise Exception(f"Could not find token: {token_name}")
            
            self.driver.execute_script("arguments[0].click();", token_element)
            time.sleep(random.uniform(2, 3))
            
            logger.info(f"Successfully selected token: {token_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to select token: {str(e)}")
            return False
            
    def set_trade_amount(self, amount):
        """Set the trade amount in the input field."""
        try:
            logger.info(f"Setting trade amount: {amount}")
            
            # Find amount input using JavaScript
            amount_input_js = """
                return (function() {
                    const inputs = document.querySelectorAll('input[type="text"], input[type="number"]');
                    for (const input of inputs) {
                        if (input.placeholder && 
                            (input.placeholder.toLowerCase().includes('amount') ||
                             input.placeholder.toLowerCase().includes('quantity'))) {
                            return input;
                        }
                    }
                    return null;
                })();
            """
            
            amount_input = WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script(amount_input_js)
            )
            
            if not amount_input:
                raise Exception("Could not find amount input")
            
            # Set amount with random typing delay
            self.driver.execute_script(
                "arguments[0].value = arguments[1]; " +
                "arguments[0].dispatchEvent(new Event('input')); " +
                "arguments[0].dispatchEvent(new Event('change'));",
                amount_input, str(amount)
            )
            
            time.sleep(random.uniform(1, 2))
            logger.info("Successfully set trade amount")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set trade amount: {str(e)}")
            return False
            
    def execute_trade(self, trade_type='buy'):
        """Execute a buy or sell trade."""
        try:
            logger.info(f"Executing {trade_type} trade...")
            
            # Find trade button using JavaScript
            trade_button_js = f"""
                return (function() {{
                    const buttons = document.querySelectorAll('button');
                    for (const button of buttons) {{
                        if (button.textContent.toLowerCase().includes('{trade_type.lower()}')) {{
                            return button;
                        }}
                    }}
                    return null;
                }})();
            """
            
            trade_button = WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script(trade_button_js)
            )
            
            if not trade_button:
                raise Exception(f"Could not find {trade_type} button")
            
            # Click trade button
            self.driver.execute_script("arguments[0].click();", trade_button)
            
            # Wait for confirmation
            time.sleep(random.uniform(2, 3))
            
            # Check for success/error messages
            result_js = """
                return (function() {
                    const elements = document.querySelectorAll('*');
                    for (const el of elements) {
                        const text = el.textContent.toLowerCase();
                        if (text.includes('success') || text.includes('confirmed')) {
                            return { success: true, message: el.textContent };
                        }
                        if (text.includes('error') || text.includes('failed')) {
                            return { success: false, message: el.textContent };
                        }
                    }
                    return null;
                })();
            """
            
            result = WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script(result_js)
            )
            
            if result and result.get('success'):
                logger.info(f"Trade successful: {result.get('message')}")
                return True
            else:
                logger.error(f"Trade failed: {result.get('message') if result else 'Unknown error'}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to execute {trade_type} trade: {str(e)}")
            return False
            
    def test_interface(self):
        """Test the trading interface functionality."""
        try:
            logger.info("Starting interface test...")
            
            # 1. Navigate to memescope
            if not self.navigate_to_memescope():
                return False
                
            # 2. Scan for tokens
            tokens = self.scan_tokens()
            if not tokens:
                return False
                
            # 3. Select first token
            first_token = tokens[0]['name']
            if not self.select_token(first_token):
                return False
                
            # 4. Set a small test amount
            if not self.set_trade_amount(0.01):
                return False
                
            logger.info("Interface test completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Interface test failed: {str(e)}")
            return False

    def start(self):
        """Start the trading bot with enhanced navigation."""
        try:
            logger.info("Starting Photon Trading Bot...")
            self.trading_active = True
            
            # Navigate to memescope
            if not self.navigate_to_memescope():
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
                    self.navigate_to_memescope()
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
            
if __name__ == "__main__":
    trader = PhotonTrader()
    trader.start()
