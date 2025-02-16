"""Photon DEX trading bot with manual wallet authentication."""

import logging
import time
import os
from typing import Dict, Any, Optional, List, Tuple
import re
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import pyautogui
from .token_discovery import TokenMetrics, TokenDiscovery

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
        """Set up the Edge browser by attaching to existing session."""
        try:
            logger.info("Attaching to existing Edge browser session...")
            
            # Setup Edge options to connect to existing session
            edge_options = Options()
            edge_options.add_experimental_option("debuggerAddress", "localhost:9222")
            
            # Initialize Edge driver
            service = Service(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service, options=edge_options)
            
            logger.info("Successfully attached to browser session")
            return True
            
        except Exception as e:
            logger.error(f"Failed to attach to browser: {str(e)}")
            return False
            
    def check_authentication(self):
        """Check if we're already authenticated on Photon DEX."""
        try:
            # Navigate to discover page
            current_url = self.driver.current_url
            if "photon-sol.tinyastro.io" not in current_url:
                self.driver.get("https://photon-sol.tinyastro.io/en/discover")
            
            # Check if we can access the token table
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "token-table"))
                )
                logger.info("Already authenticated on Photon DEX")
                return True
            except TimeoutException:
                logger.warning("Not authenticated on Photon DEX")
                return False
                
        except Exception as e:
            logger.error(f"Error checking authentication: {str(e)}")
            return False
            
    def wait_for_manual_auth(self):
        """Wait for manual wallet authentication."""
        try:
            logger.info("Please complete the following steps:")
            logger.info("1. Log in to Photon DEX manually")
            logger.info("2. Connect your Phantom wallet")
            logger.info("3. Complete any security verifications")
            logger.info("4. Once authenticated, the bot will continue automatically")
            
            # Navigate to Photon DEX
            self.driver.get("https://photon-sol.tinyastro.io/en/discover")
            
            input("Press Enter once you have completed the authentication steps...")
            
            # Verify connection
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "token-table"))
                )
                logger.info("Successfully verified authentication")
                return True
            except TimeoutException:
                logger.error("Could not verify authentication. Please check your connection")
                return False
                
        except Exception as e:
            logger.error(f"Error during manual authentication: {str(e)}")
            return False
            
    async def initialize(self, manual_auth: bool = True):
        """Initialize the trading bot by attaching to existing browser."""
        try:
            if self.initialized:
                return True
                
            # Set up browser connection
            if not self.setup_browser():
                return False
                
            # Check authentication
            if not self.check_authentication():
                if manual_auth:
                    if not self.wait_for_manual_auth():
                        await self.cleanup()
                        return False
                else:
                    logger.error("Please log in to Photon DEX and connect wallet in the browser first")
                    return False
                
            # Initialize token discovery
            self.discovery = TokenDiscovery(self.driver, self.config)
            
            self.initialized = True
            logger.info("Photon trader initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Photon trader: {str(e)}")
            await self.cleanup()
            return False
            
    async def scan_for_opportunities(self) -> List[Tuple[TokenMetrics, float, str]]:
        """Scan for trading opportunities."""
        try:
            # Scan tokens
            tokens = await self.discovery.scan_tokens()
            opportunities = []
            
            # Analyze each token
            for token in tokens:
                score, reason = self.discovery.analyze_opportunity(token)
                if score > 0:
                    opportunities.append((token, score, reason))
                    
            # Sort by score descending
            opportunities.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"Found {len(opportunities)} potential trading opportunities")
            return opportunities[:self.config['discovery']['max_opportunities']]
            
        except Exception as e:
            logger.error(f"Failed to scan for opportunities: {str(e)}")
            return []
            
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
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing webdriver: {str(e)}")
            finally:
                self.driver = None
                self.initialized = False
                self.wallet_connected = False
