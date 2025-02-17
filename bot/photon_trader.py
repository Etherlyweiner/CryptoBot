"""Photon DEX trading bot with manual wallet authentication."""

import logging
import time
import os
from typing import Dict, Any, Optional, List, Tuple
import re
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import pyautogui
import aiohttp
import asyncio
from .token_discovery import TokenMetrics, TokenDiscovery
import json

logger = logging.getLogger(__name__)

class PhotonTrader:
    """Photon DEX trading bot that interacts with the web interface."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Photon trader."""
        self.config = config
        self.driver = None
        self.initialized = False
        self.wallet_connected = False
        self.retry_count = 0
        self.max_retries = config['wallet']['max_retries']
        self.discovery = None
        
        # RPC Configuration
        self.rpc_config = config['rpc']
        self.rpc_endpoints = [self.rpc_config['primary']] + self.rpc_config['fallbacks']
        self.current_rpc = 0
        self.helius_enabled = self.rpc_config['helius']['enabled']
        self.helius_api_key = self.rpc_config['helius']['api_key']
        
        self._validate_wallet_addresses()
        
    def _validate_wallet_addresses(self):
        """Validate wallet addresses in config."""
        wallet_pattern = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')
        
        primary = self.config['wallet'].get('primary_address')
        secondary = self.config['wallet'].get('secondary_address')
        
        if not primary or not wallet_pattern.match(primary):
            raise ValueError("Invalid primary wallet address")
            
        if secondary and not wallet_pattern.match(secondary):
            raise ValueError("Invalid secondary wallet address")
            
        logger.info(f"Wallet addresses validated. Primary: {primary[:6]}...{primary[-4:]}")
        if secondary:
            logger.info(f"Secondary wallet: {secondary[:6]}...{secondary[-4:]}")
            
    def setup_browser(self):
        """Set up the browser connection."""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retrying browser setup (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    
                logger.info("Attaching to existing Edge browser session...")
                
                options = Options()
                options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                options.use_chromium = True
                options.page_load_strategy = 'eager'
                
                self.driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=options)
                self.driver.implicitly_wait(5)  # Set shorter implicit wait
                
                # Verify browser connection
                try:
                    self.driver.current_window_handle
                except:
                    raise Exception("Failed to connect to browser")
                    
                # Switch to Photon DEX tab or create new one
                photon_tab = None
                original_handles = self.driver.window_handles
                
                for handle in original_handles:
                    try:
                        self.driver.switch_to.window(handle)
                        current_url = self.driver.current_url
                        if "photon-sol.tinyastro.io" in current_url:
                            photon_tab = handle
                            logger.info(f"Found existing Photon DEX tab: {current_url}")
                            break
                    except Exception as e:
                        logger.debug(f"Error checking tab: {str(e)}")
                        continue
                        
                if not photon_tab:
                    logger.info("No existing Photon DEX tab found, creating new one...")
                    # Try direct navigation first
                    self.driver.get("https://photon-sol.tinyastro.io/en/discover")
                    
                # Wait for page load
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    logger.info(f"Page loaded: {self.driver.current_url}")
                except Exception as e:
                    logger.warning(f"Page load timeout: {str(e)}")
                    
                # Verify we can interact with the page
                try:
                    self.driver.execute_script("return window.localStorage")
                    return True
                except:
                    raise Exception("Cannot interact with page")
                    
            except Exception as e:
                logger.error(f"Browser setup attempt {attempt + 1} failed: {str(e)}")
                if hasattr(self, 'driver') and self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                    
                if attempt == max_retries - 1:
                    logger.error("All browser setup attempts failed")
                    return False
                    
        return False
        
    def check_authentication(self):
        """Check if we're already authenticated on Photon DEX."""
        try:
            # Verify browser is still responsive
            try:
                self.driver.current_window_handle
            except:
                logger.error("Browser connection lost")
                return False
                
            # Check current URL and navigate if needed
            current_url = self.driver.current_url
            logger.info(f"Current URL: {current_url}")
            
            # First check if we're already on memescope
            if "photon-sol.tinyastro.io/en/memescope" in current_url:
                logger.info("Already on memescope page")
            else:
                logger.info("Navigating to Photon DEX memescope...")
                self.driver.get("https://photon-sol.tinyastro.io/en/memescope")
                time.sleep(3)  # Short wait for initial load
            
            # Wait for page to be fully loaded
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)  # Additional wait for dynamic content
            except Exception as e:
                logger.warning(f"Page load wait timed out: {str(e)}")
            
            # Check for Photon-specific elements that indicate we're connected
            photon_indicators = [
                (By.CLASS_NAME, "photon-balance"),
                (By.CLASS_NAME, "photon-wallet"),
                (By.XPATH, "//*[contains(@class, 'balance')]"),
                (By.XPATH, "//*[contains(@class, 'account-info')]"),
                (By.XPATH, "//div[contains(@class, 'wallet') and contains(@class, 'active')]")
            ]
            
            for by, value in photon_indicators:
                try:
                    elements = self.driver.find_elements(by, value)
                    for elem in elements:
                        if elem.is_displayed():
                            logger.info(f"Found Photon wallet indicator: {value}")
                            return True
                except:
                    continue
            
            # Check for meme token content as fallback
            content_indicators = [
                (By.CLASS_NAME, "token-card"),
                (By.CLASS_NAME, "meme-token"),
                (By.XPATH, "//*[contains(@class, 'token-list')]"),
                (By.XPATH, "//*[contains(@class, 'token-grid')]")
            ]
            
            for by, value in content_indicators:
                try:
                    elements = self.driver.find_elements(by, value)
                    for elem in elements:
                        if elem.is_displayed():
                            try:
                                # Verify we can interact with the content
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                                logger.info(f"Found and verified token content: {value}")
                                return True
                            except:
                                continue
                except:
                    continue
            
            logger.warning("Could not verify Photon wallet connection")
            return False
            
        except Exception as e:
            logger.error(f"Error checking Photon connection: {str(e)}")
            return False
            
    def attempt_manual_authentication(self):
        """Guide the user through Photon wallet connection."""
        try:
            logger.info("\nPlease ensure you're connected to Photon:")
            logger.info("1. Make sure you can see your Photon wallet balance")
            logger.info("2. Wait for the meme token list to load")
            
            max_retries = 3
            retry_delay = 10
            
            for attempt in range(max_retries):
                logger.info("Waiting for Photon connection...")
                time.sleep(retry_delay)
                
                if self.check_authentication():
                    logger.info("Successfully connected to Photon!")
                    return True
                    
                # Try refreshing the page if needed
                try:
                    self.driver.refresh()
                    time.sleep(5)
                except:
                    pass
                    
            logger.error("Timed out waiting for Photon connection")
            return False
            
        except Exception as e:
            logger.error(f"Error during Photon connection: {str(e)}")
            return False
            
    async def initialize_rpc(self) -> bool:
        """Initialize RPC connection with Helius."""
        try:
            # Create aiohttp session for RPC
            if not hasattr(self, '_session'):
                self._session = aiohttp.ClientSession()
                
            # Test Helius connection first
            if self.helius_enabled:
                response = await self.make_rpc_request(
                    self.rpc_config['primary'],
                    "getHealth",
                    []
                )
                
                if response and response.get('result') == "ok":
                    logger.info("Connected to Helius RPC")
                    return True
                    
            # Try fallback endpoints
            for endpoint in self.rpc_config['fallbacks']:
                response = await self.make_rpc_request(
                    endpoint,
                    "getHealth",
                    []
                )
                
                if response and response.get('result') == "ok":
                    logger.info(f"Connected to fallback RPC: {endpoint}")
                    return True
                    
            logger.error("Failed to connect to any RPC endpoint")
            return False
            
        except Exception as e:
            logger.error(f"Error initializing RPC: {str(e)}")
            return False
            
    async def initialize(self, manual_auth: bool = True) -> bool:
        """Initialize the trader with fallback options."""
        try:
            # Setup browser
            if not self.setup_browser():
                logger.error("Failed to setup browser")
                return False
                
            # Initialize RPC connection
            if not await self.initialize_rpc():
                logger.error("Failed to establish RPC connection")
                return False
                
            # Check authentication
            auth_retries = 3
            while auth_retries > 0:
                if self.check_authentication():
                    self.initialized = True
                    return True
                    
                if manual_auth:
                    logger.info("Attempting manual authentication...")
                    if await self.attempt_manual_authentication():
                        self.initialized = True
                        return True
                    break  # Don't retry if manual auth failed
                    
                auth_retries -= 1
                if auth_retries > 0:
                    logger.info(f"Retrying authentication ({auth_retries} attempts left)")
                    time.sleep(5)
                    
            logger.error("Failed to verify authentication after retries")
            return False
            
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            return False
            
    async def check_rpc_connection(self) -> bool:
        """Check RPC connection with fallback options."""
        for i, endpoint in enumerate(self.rpc_endpoints):
            try:
                # Try to get recent blockhash to test connection
                response = await self.make_rpc_request(
                    endpoint,
                    "getRecentBlockhash",
                    []
                )
                
                if response and 'result' in response:
                    self.current_rpc = i
                    logger.info(f"Connected to RPC endpoint: {endpoint}")
                    return True
                    
            except Exception as e:
                logger.warning(f"Failed to connect to RPC {endpoint}: {str(e)}")
                continue
                
        logger.error("All RPC endpoints failed")
        return False
        
    async def make_rpc_request(self, endpoint: str, method: str, params: list) -> Optional[dict]:
        """Make RPC request with retry logic and Helius support."""
        max_retries = self.rpc_config['retries']
        timeout = self.rpc_config['timeout']
        retry_delay = 1
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add Helius-specific headers if using Helius endpoint
        if self.helius_enabled and "helius" in endpoint:
            headers["Authorization"] = f"Bearer {self.helius_api_key}"
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        endpoint,
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": method,
                            "params": params
                        },
                        headers=headers,
                        timeout=timeout
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            # Check for Helius enhanced logs if enabled
                            if (self.helius_enabled and 
                                self.rpc_config['helius']['enhanced_logs'] and 
                                'result' in result):
                                await self._process_helius_logs(result)
                                
                            return result
                            
            except Exception as e:
                logger.warning(f"RPC request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    
        return None
        
    async def _process_helius_logs(self, result: dict):
        """Process enhanced logs from Helius."""
        try:
            if 'logs' in result['result']:
                logs = result['result']['logs']
                for log in logs:
                    if 'programId' in log:
                        # Process program-specific logs
                        await self._handle_program_log(log)
                        
        except Exception as e:
            logger.error(f"Error processing Helius logs: {str(e)}")
            
    async def _handle_program_log(self, log: dict):
        """Handle program-specific logs from Helius."""
        try:
            program_id = log.get('programId')
            if program_id:
                # Handle specific program logs (e.g., token program, AMM program)
                if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                    await self._handle_token_program_log(log)
                elif "AMM" in program_id:
                    await self._handle_amm_program_log(log)
                    
        except Exception as e:
            logger.error(f"Error handling program log: {str(e)}")
            
    async def _handle_token_program_log(self, log: dict):
        """Handle token program specific logs."""
        try:
            if 'type' in log:
                log_type = log['type']
                if log_type == 'transfer':
                    # Process transfer logs
                    amount = log.get('amount')
                    from_address = log.get('from')
                    to_address = log.get('to')
                    logger.info(f"Token transfer: {amount} from {from_address} to {to_address}")
                    
        except Exception as e:
            logger.error(f"Error handling token program log: {str(e)}")
            
    async def _handle_amm_program_log(self, log: dict):
        """Handle AMM program specific logs."""
        try:
            if 'type' in log:
                log_type = log['type']
                if log_type == 'swap':
                    # Process swap logs
                    amount_in = log.get('amountIn')
                    amount_out = log.get('amountOut')
                    logger.info(f"Swap: {amount_in} -> {amount_out}")
                    
        except Exception as e:
            logger.error(f"Error handling AMM program log: {str(e)}")
            
    async def wait_for_manual_auth(self):
        """Wait for manual wallet authentication."""
        try:
            logger.info("\nPlease complete these steps:")
            logger.info("1. Connect your wallet using the 'Connect Wallet' button")
            logger.info("2. Approve any wallet connection requests")
            logger.info("3. Wait for the token table to load")
            
            # Wait for wallet connection
            max_wait = 60  # Maximum wait time in seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                if self.check_authentication():
                    logger.info("Authentication successful!")
                    return True
                    
                # Check for wallet connect button
                try:
                    connect_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Connect Wallet')]"))
                    )
                    if connect_button.is_displayed():
                        logger.info("Found Connect Wallet button - waiting for user to connect...")
                except TimeoutException:
                    # Button not found, might be already connecting
                    pass
                    
                # Wait a bit before next check
                await asyncio.sleep(5)
                logger.info("Waiting for wallet connection...")
                
            logger.error("Timed out waiting for manual authentication")
            return False
            
        except Exception as e:
            logger.error(f"Error during manual authentication: {str(e)}")
            return False
            
    async def analyze_bonding_curve(self, token_data: Dict) -> Dict:
        """Analyze token bonding curve and market dynamics."""
        try:
            analysis = {
                'token': token_data['name'],
                'signals': [],
                'risk_level': 0,
                'opportunity_score': 0,
                'strategy': None,
                'entry_type': None
            }
            
            # Check Telegram signals
            telegram_signals = []
            if os.path.exists('telegram_signals.json'):
                try:
                    with open('telegram_signals.json', 'r') as f:
                        telegram_signals = json.load(f)
                except:
                    pass
                    
            # Look for recent signals for this token
            token_signals = [
                s for s in telegram_signals 
                if s['token'].lower() in token_data['name'].lower() 
                and (time.time() - s['timestamp']) < 3600  # Within last hour
            ]
            
            if token_signals:
                latest_signal = max(token_signals, key=lambda x: x['timestamp'])
                analysis['signals'].append(f"Telegram momentum: {latest_signal['score']}")
                analysis['opportunity_score'] += min(latest_signal['score'], 3)  # Cap at 3 points
                
            # Calculate market metrics
            if token_data.get('market_cap') and token_data.get('volume'):
                turnover = token_data['volume'] / token_data['market_cap']
                analysis['turnover_ratio'] = turnover
                
                # High turnover relative to market cap indicates active trading
                if turnover > 0.3:
                    analysis['signals'].append('High market turnover')
                    analysis['opportunity_score'] += 2
                    
                # Check for potential bonding curve arbitrage
                if turnover > 0.5 and token_data.get('price_change', 0) > 5:
                    analysis['signals'].append('Potential bonding curve arbitrage')
                    analysis['opportunity_score'] += 2
                    analysis['entry_type'] = 'CURVE_ARBITRAGE'
                    
            # Enhanced price momentum analysis
            if token_data.get('price_change'):
                if token_data['price_change'] > 20:  # Strong upward momentum
                    analysis['signals'].append('Strong upward momentum')
                    analysis['opportunity_score'] += 2
                    analysis['risk_level'] += 2
                    analysis['entry_type'] = 'MOMENTUM_CHASE'
                elif token_data['price_change'] > 10:  # Moderate upward momentum
                    analysis['signals'].append('Building momentum')
                    analysis['opportunity_score'] += 1
                    analysis['risk_level'] += 1
                elif token_data['price_change'] < -15:  # Potential reversal
                    analysis['signals'].append('Potential reversal opportunity')
                    analysis['opportunity_score'] += 1
                    analysis['entry_type'] = 'REVERSAL'
                    
            # Market cap analysis with enhanced early detection
            if token_data.get('market_cap'):
                if token_data['market_cap'] < 250000:  # Ultra early stage
                    analysis['signals'].append('Ultra early stage - exceptional growth potential')
                    analysis['opportunity_score'] += 4
                    analysis['risk_level'] += 3
                    analysis['entry_type'] = 'EARLY_GEM'
                elif token_data['market_cap'] < 1000000:  # Very early stage
                    analysis['signals'].append('Very early stage - high growth potential')
                    analysis['opportunity_score'] += 3
                    analysis['risk_level'] += 2
                elif token_data['market_cap'] < 5000000:  # Early stage
                    analysis['signals'].append('Early stage - good growth potential')
                    analysis['opportunity_score'] += 1
                    analysis['risk_level'] += 1
                    
            # Determine optimal strategy based on analysis
            if analysis['opportunity_score'] >= 6:
                if analysis['entry_type'] == 'EARLY_GEM':
                    analysis['strategy'] = 'AGGRESSIVE_ACCUMULATION'
                elif analysis['entry_type'] == 'CURVE_ARBITRAGE':
                    analysis['strategy'] = 'ARBITRAGE_SCALP'
                elif analysis['entry_type'] == 'MOMENTUM_CHASE':
                    analysis['strategy'] = 'MOMENTUM_RIDE'
                else:
                    analysis['strategy'] = 'MODERATE_ACCUMULATION'
            elif analysis['opportunity_score'] >= 4:
                if analysis['entry_type'] == 'REVERSAL':
                    analysis['strategy'] = 'REVERSAL_SCALP'
                else:
                    analysis['strategy'] = 'GRADUAL_ENTRY'
            else:
                analysis['strategy'] = 'MONITOR'
                
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing bonding curve: {str(e)}")
            return None
            
    async def execute_trade_strategy(self, token: str, strategy: str, analysis: Dict) -> bool:
        """Execute advanced trading strategy for a given token."""
        try:
            logger.info(f"Executing {strategy} strategy for {token}")
            
            # Find and click the trade button for this token
            token_elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{token}')]")
            trade_button = None
            
            for elem in token_elements:
                if not elem.is_displayed():
                    continue
                    
                # Find parent card/row
                parent = elem
                for _ in range(5):  # Look up to 5 levels up
                    parent = parent.find_element(By.XPATH, '..')
                    trade_buttons = parent.find_elements(By.XPATH, ".//button[contains(text(), 'Trade') or contains(text(), 'Buy') or contains(text(), 'Sell')]")
                    if trade_buttons:
                        trade_button = trade_buttons[0]
                        break
                        
                if trade_button:
                    break
                    
            if not trade_button:
                logger.error(f"Could not find trade button for {token}")
                return False
                
            # Click trade button and wait for modal
            trade_button.click()
            time.sleep(2)
            
            # Execute strategy-specific logic
            if strategy == 'AGGRESSIVE_ACCUMULATION':
                return await self._execute_aggressive_accumulation(token, analysis)
            elif strategy == 'ARBITRAGE_SCALP':
                return await self._execute_arbitrage_scalp(token, analysis)
            elif strategy == 'MOMENTUM_RIDE':
                return await self._execute_momentum_ride(token, analysis)
            elif strategy == 'REVERSAL_SCALP':
                return await self._execute_reversal_scalp(token, analysis)
            elif strategy == 'MODERATE_ACCUMULATION':
                return await self._execute_moderate_accumulation(token, analysis)
            elif strategy == 'GRADUAL_ENTRY':
                return await self._execute_gradual_entry(token, analysis)
            else:
                logger.info(f"Strategy {strategy} requires monitoring only")
                return True
                
        except Exception as e:
            logger.error(f"Error executing trade strategy: {str(e)}")
            return False
            
    async def _execute_arbitrage_scalp(self, token: str, analysis: Dict) -> bool:
        """Execute arbitrage scalping strategy."""
        try:
            # Set aggressive position size for quick scalp
            investment = 0.15  # SOL
            
            # Find input field and set amount
            amount_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@class, 'amount') or contains(@class, 'quantity')]"))
            )
            
            # Clear and set amount
            amount_input.clear()
            amount_input.send_keys(str(investment))
            time.sleep(1)
            
            # Set higher slippage for faster execution
            try:
                slippage_settings = self.driver.find_element(By.XPATH, "//*[contains(@class, 'slippage-settings')]")
                slippage_settings.click()
                time.sleep(0.5)
                
                slippage_input = self.driver.find_element(By.XPATH, "//input[contains(@class, 'slippage-input')]")
                slippage_input.clear()
                slippage_input.send_keys("3")  # 3% slippage
                time.sleep(0.5)
            except:
                pass
                
            # Execute buy
            buy_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Buy') or contains(text(), 'Swap')]"))
            )
            
            if buy_button.is_displayed() and buy_button.is_enabled():
                buy_button.click()
                time.sleep(2)
                
                try:
                    confirm_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Approve')]"))
                    )
                    if confirm_button.is_displayed():
                        confirm_button.click()
                        time.sleep(2)
                except:
                    pass
                    
                logger.info(f"Executed arbitrage scalp buy for {token}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error in arbitrage scalp: {str(e)}")
            return False
            
    async def _execute_momentum_ride(self, token: str, analysis: Dict) -> bool:
        """Execute momentum riding strategy."""
        try:
            # Set position size based on momentum strength
            base_investment = 0.1  # SOL
            momentum_multiplier = min(analysis['opportunity_score'] / 5, 2)  # Cap at 2x
            investment = base_investment * momentum_multiplier
            
            # Find input field and set amount
            amount_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@class, 'amount') or contains(@class, 'quantity')]"))
            )
            
            # Clear and set amount
            amount_input.clear()
            amount_input.send_keys(str(investment))
            time.sleep(1)
            
            # Execute buy
            buy_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Buy') or contains(text(), 'Swap')]"))
            )
            
            if buy_button.is_displayed() and buy_button.is_enabled():
                buy_button.click()
                time.sleep(2)
                
                try:
                    confirm_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Approve')]"))
                    )
                    if confirm_button.is_displayed():
                        confirm_button.click()
                        time.sleep(2)
                except:
                    pass
                    
                logger.info(f"Executed momentum ride buy for {token}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error in momentum ride: {str(e)}")
            return False
            
    async def _execute_reversal_scalp(self, token: str, analysis: Dict) -> bool:
        """Execute reversal scalping strategy."""
        try:
            # Set smaller position size for reversal trades
            investment = 0.05  # SOL
            
            # Find input field and set amount
            amount_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@class, 'amount') or contains(@class, 'quantity')]"))
            )
            
            # Clear and set amount
            amount_input.clear()
            amount_input.send_keys(str(investment))
            time.sleep(1)
            
            # Set tight slippage for better entry
            try:
                slippage_settings = self.driver.find_element(By.XPATH, "//*[contains(@class, 'slippage-settings')]")
                slippage_settings.click()
                time.sleep(0.5)
                
                slippage_input = self.driver.find_element(By.XPATH, "//input[contains(@class, 'slippage-input')]")
                slippage_input.clear()
                slippage_input.send_keys("1")  # 1% slippage
                time.sleep(0.5)
            except:
                pass
                
            # Execute buy
            buy_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Buy') or contains(text(), 'Swap')]"))
            )
            
            if buy_button.is_displayed() and buy_button.is_enabled():
                buy_button.click()
                time.sleep(2)
                
                try:
                    confirm_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Approve')]"))
                    )
                    if confirm_button.is_displayed():
                        confirm_button.click()
                        time.sleep(2)
                except:
                    pass
                    
                logger.info(f"Executed reversal scalp buy for {token}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error in reversal scalp: {str(e)}")
            return False
            
    async def scan_for_opportunities(self) -> List[Dict]:
        """Scan for trading opportunities with advanced analysis."""
        try:
            logger.info("Scanning for trading opportunities...")
            
            # Get current token data
            tokens = await self.scan_token_table()
            
            if not tokens:
                return []
                
            # Analyze each token
            opportunities = []
            for token in tokens:
                # Perform detailed analysis
                analysis = await self.analyze_bonding_curve(token)
                if not analysis:
                    continue
                    
                if analysis['strategy'] != 'MONITOR':
                    opportunities.append({
                        'token': token['name'],
                        'score': analysis['opportunity_score'],
                        'risk_level': analysis['risk_level'],
                        'signals': analysis['signals'],
                        'strategy': analysis['strategy'],
                        'data': token
                    })
                    
            # Sort by opportunity score descending
            opportunities.sort(key=lambda x: x['score'], reverse=True)
            
            if opportunities:
                logger.info(f"Found {len(opportunities)} actionable opportunities")
                for opp in opportunities[:3]:  # Log top 3
                    logger.info(f"Token: {opp['token']}")
                    logger.info(f"Strategy: {opp['strategy']}")
                    logger.info(f"Score: {opp['score']}, Risk: {opp['risk_level']}")
                    logger.info(f"Signals: {', '.join(opp['signals'])}")
                    logger.info("---")
                    
                    # Execute trading strategy for top opportunities
                    if opp['score'] >= 3:  # Minimum score threshold
                        await self.execute_trade_strategy(
                            opp['token'],
                            opp['strategy'],
                            analysis
                        )
                    
            return opportunities
            
        except Exception as e:
            logger.error(f"Failed to scan for opportunities: {str(e)}")
            return []
            
    async def scan_token_table(self) -> List[Dict]:
        """Scan the token table for trading opportunities."""
        try:
            # Wait for token content to be visible
            token_selectors = [
                (By.CLASS_NAME, "token-card"),
                (By.CLASS_NAME, "meme-token"),
                (By.XPATH, "//*[contains(@class, 'token-list')]"),
                (By.XPATH, "//*[contains(@class, 'token-grid')]")
            ]
            
            tokens = []
            for by, value in token_selectors:
                try:
                    elements = self.driver.find_elements(by, value)
                    if elements:
                        logger.info(f"Found {len(elements)} tokens using {value}")
                        for elem in elements:
                            if not elem.is_displayed():
                                continue
                                
                            try:
                                # Scroll element into view
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                                time.sleep(0.1)  # Brief pause for dynamic content
                                
                                token_data = {}
                                
                                # Extract token name/symbol
                                try:
                                    name_elem = elem.find_element(By.XPATH, ".//*[contains(@class, 'name') or contains(@class, 'symbol')]")
                                    token_data['name'] = name_elem.text.strip()
                                except:
                                    continue
                                    
                                # Extract price if available
                                try:
                                    price_elem = elem.find_element(By.XPATH, ".//*[contains(@class, 'price')]")
                                    price_text = price_elem.text.strip().replace('$', '').replace(',', '')
                                    token_data['price'] = float(price_text) if price_text else None
                                except:
                                    token_data['price'] = None
                                    
                                # Extract volume if available
                                try:
                                    volume_elem = elem.find_element(By.XPATH, ".//*[contains(@class, 'volume')]")
                                    volume_text = volume_elem.text.strip().replace('$', '').replace(',', '')
                                    token_data['volume'] = float(volume_text) if volume_text else None
                                except:
                                    token_data['volume'] = None
                                    
                                # Extract market cap if available
                                try:
                                    mcap_elem = elem.find_element(By.XPATH, ".//*[contains(@class, 'mcap') or contains(@class, 'market-cap')]")
                                    mcap_text = mcap_elem.text.strip().replace('$', '').replace(',', '')
                                    token_data['market_cap'] = float(mcap_text) if mcap_text else None
                                except:
                                    token_data['market_cap'] = None
                                    
                                # Extract price change if available
                                try:
                                    change_elem = elem.find_element(By.XPATH, ".//*[contains(@class, 'change') or contains(@class, 'percent')]")
                                    change_text = change_elem.text.strip().replace('%', '').replace('+', '')
                                    token_data['price_change'] = float(change_text) if change_text else None
                                except:
                                    token_data['price_change'] = None
                                    
                                # Only add tokens with at least name and one metric
                                if token_data.get('name') and any(v is not None for v in token_data.values() if v != token_data['name']):
                                    tokens.append(token_data)
                                    
                            except Exception as e:
                                logger.debug(f"Error extracting token data: {str(e)}")
                                continue
                                
                        if tokens:
                            break  # Stop if we found tokens with one method
                            
                except Exception as e:
                    logger.debug(f"Error with selector {value}: {str(e)}")
                    continue
                    
            if not tokens:
                logger.warning("No tokens found in scan")
                
            return tokens
            
        except Exception as e:
            logger.error(f"Error scanning token table: {str(e)}")
            return []
            
    async def execute_trade(self, token: TokenMetrics, wallet_balance: float) -> bool:
        """Execute trade with MEV optimization."""
        try:
            # Calculate optimal priority fee
            priority_fee = self.discovery.calculate_priority_fee(
                token_price=token.price,
                wallet_balance=wallet_balance
            )
            
            # Check if backrunning is enabled and profitable
            if self.config['mev']['backrun_enabled']:
                large_trades = await self.scan_mempool_for_trades(token.address)
                if large_trades:
                    logger.info(f"Found {len(large_trades)} large trades to backrun")
                    # Increase priority fee to ensure we get in after the target transaction
                    priority_fee = min(
                        priority_fee * 1.2,
                        self.config['mev']['max_priority_fee']
                    )
            
            # Calculate trade size based on wallet balance
            trade_size = min(
                wallet_balance * self.config['wallet']['max_allocation'],
                self.config['risk']['max_trade_size']
            )
            
            # Execute the trade
            success = await self.place_trade(
                token=token,
                amount=trade_size,
                priority_fee=priority_fee,
                max_blocks_to_wait=self.config['mev']['max_blocks_to_wait']
            )
            
            if success:
                logger.info(f"Successfully executed trade for {token.symbol}")
                return True
            else:
                logger.warning(f"Failed to execute trade for {token.symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return False
            
    async def scan_mempool_for_trades(self, token_address: str) -> List[dict]:
        """Scan mempool for large trades to potentially backrun."""
        try:
            # TODO: Implement mempool scanning logic
            # This would involve connecting to a Solana RPC node
            # and monitoring for large pending transactions
            return []
        except Exception as e:
            logger.error(f"Error scanning mempool: {str(e)}")
            return []
            
    async def get_wallet_balance(self) -> float:
        """Get current wallet balance in SOL."""
        try:
            # TODO: Implement actual balance checking
            # For now return a dummy value
            return 10.0
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            return 0.0
            
    async def place_buy_order(self, token_address: str, amount_sol: float):
        """Place a buy order for a token with risk management."""
        try:
            if not self.initialized:
                raise Exception("Trader not initialized")
                
            # Check risk limits
            if amount_sol > self.config['risk']['max_trade_size']:
                raise Exception(f"Trade size {amount_sol} SOL exceeds maximum allowed {self.config['risk']['max_trade_size']} SOL")
                
            # Navigate to swap page
            self.driver.get(f"https://photon-sol.tinyastro.io/en/swap")
            
            # Wait for input fields
            WebDriverWait(self.driver, self.config['automation']['element_timeout']).until(
                EC.presence_of_element_located((By.CLASS_NAME, "token-amount-input"))
            )
            
            # Input token address
            token_input = self.driver.find_element(By.CLASS_NAME, "token-search-input")
            token_input.send_keys(token_address)
            
            # Select token from list
            WebDriverWait(self.driver, self.config['automation']['element_timeout']).until(
                EC.presence_of_element_located((By.CLASS_NAME, "token-item"))
            ).click()
            
            # Input amount
            amount_input = self.driver.find_element(By.CLASS_NAME, "token-amount-input")
            amount_input.send_keys(str(amount_sol))
            
            # Check slippage
            slippage_element = self.driver.find_element(By.CLASS_NAME, "slippage-value")
            current_slippage = float(slippage_element.text.strip('%'))
            if current_slippage > self.config['trading']['max_slippage']:
                raise Exception(f"Slippage {current_slippage}% exceeds maximum allowed {self.config['trading']['max_slippage']}%")
                
            # Click swap button
            swap_btn = self.driver.find_element(By.CLASS_NAME, "swap-button")
            swap_btn.click()
            
            # Wait for confirmation
            time.sleep(self.config['automation']['wait_time'])
            
            # Confirm transaction in Phantom
            confirm_pos = pyautogui.locateOnScreen(
                os.path.join(self.config['automation']['screenshot_dir'], 'confirm_button.png')
            )
            if confirm_pos:
                pyautogui.click(confirm_pos)
                
            logger.info(f"Buy order placed for {amount_sol} SOL of {token_address}")
            
        except Exception as e:
            logger.error(f"Failed to place buy order: {str(e)}")
            raise
            
    async def place_sell_order(self, token_address: str, amount_tokens: float):
        """Place a sell order for a token with risk management."""
        try:
            if not self.initialized:
                raise Exception("Trader not initialized")
                
            # Navigate to swap page
            self.driver.get(f"https://photon-sol.tinyastro.io/en/swap")
            
            # Wait for input fields
            WebDriverWait(self.driver, self.config['automation']['element_timeout']).until(
                EC.presence_of_element_located((By.CLASS_NAME, "token-amount-input"))
            )
            
            # Select token to sell
            sell_token = self.driver.find_element(By.CLASS_NAME, "token-select-trigger")
            sell_token.click()
            
            # Input token address
            token_input = self.driver.find_element(By.CLASS_NAME, "token-search-input")
            token_input.send_keys(token_address)
            
            # Select token from list
            WebDriverWait(self.driver, self.config['automation']['element_timeout']).until(
                EC.presence_of_element_located((By.CLASS_NAME, "token-item"))
            ).click()
            
            # Input amount
            amount_input = self.driver.find_element(By.CLASS_NAME, "token-amount-input")
            amount_input.send_keys(str(amount_tokens))
            
            # Check slippage
            slippage_element = self.driver.find_element(By.CLASS_NAME, "slippage-value")
            current_slippage = float(slippage_element.text.strip('%'))
            if current_slippage > self.config['trading']['max_slippage']:
                raise Exception(f"Slippage {current_slippage}% exceeds maximum allowed {self.config['trading']['max_slippage']}%")
                
            # Click swap button
            swap_btn = self.driver.find_element(By.CLASS_NAME, "swap-button")
            swap_btn.click()
            
            # Wait for confirmation
            time.sleep(self.config['automation']['wait_time'])
            
            # Confirm transaction in Phantom
            confirm_pos = pyautogui.locateOnScreen(
                os.path.join(self.config['automation']['screenshot_dir'], 'confirm_button.png')
            )
            if confirm_pos:
                pyautogui.click(confirm_pos)
                
            logger.info(f"Sell order placed for {amount_tokens} tokens of {token_address}")
            
        except Exception as e:
            logger.error(f"Failed to place sell order: {str(e)}")
            raise
            
    async def get_token_price(self, token_address: str) -> float:
        """Get current token price in SOL."""
        try:
            if not self.initialized:
                raise Exception("Trader not initialized")
                
            # Navigate to swap page
            self.driver.get(f"https://photon-sol.tinyastro.io/en/swap")
            
            # Wait for input fields
            WebDriverWait(self.driver, self.config['automation']['element_timeout']).until(
                EC.presence_of_element_located((By.CLASS_NAME, "token-amount-input"))
            )
            
            # Input token address
            token_input = self.driver.find_element(By.CLASS_NAME, "token-search-input")
            token_input.send_keys(token_address)
            
            # Select token from list
            WebDriverWait(self.driver, self.config['automation']['element_timeout']).until(
                EC.presence_of_element_located((By.CLASS_NAME, "token-item"))
            ).click()
            
            # Input 1 SOL
            amount_input = self.driver.find_element(By.CLASS_NAME, "token-amount-input")
            amount_input.send_keys("1")
            
            # Get output amount
            output_amount = self.driver.find_element(By.CLASS_NAME, "token-amount-output")
            price = float(output_amount.get_attribute("value"))
            
            return price
            
        except Exception as e:
            logger.error(f"Failed to get token price: {str(e)}")
            raise
            
    async def cleanup(self):
        """Clean up resources."""
        try:
            # Close browser if it exists
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.warning(f"Error closing browser: {str(e)}")
                finally:
                    self.driver = None
                    
            # Close any active RPC sessions
            if hasattr(self, '_session') and self._session:
                try:
                    await self._session.close()
                except Exception as e:
                    logger.warning(f"Error closing RPC session: {str(e)}")
                finally:
                    self._session = None
                    
            self.initialized = False
            logger.info("Cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
