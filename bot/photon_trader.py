"""Photon DEX trading bot for automated memecoin trading."""

import logging
import time
import os
from typing import Dict, Any, Optional
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import pyautogui

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

    async def initialize(self):
        """Initialize the web driver and connect to Photon DEX."""
        try:
            if self.initialized:
                return
                
            logger.info("Initializing Photon trader...")
            
            # Setup Chrome options
            chrome_options = Options()
            if self.config['browser']['headless']:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument(f"--window-size={self.config['browser']['window_size'][0]},{self.config['browser']['window_size'][1]}")
            chrome_options.add_argument(f"--user-data-dir={os.path.abspath(self.config['browser']['user_data_dir'])}")
            
            # Initialize Chrome driver
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            # Navigate to Photon DEX
            self.driver.get("https://photon-sol.tinyastro.io/en/settings?tab_id=1")
            
            # Wait for page to load
            WebDriverWait(self.driver, self.config['automation']['element_timeout']).until(
                EC.presence_of_element_located((By.CLASS_NAME, "connect-wallet-btn"))
            )
            
            # Connect wallet if needed
            if self.config['wallet']['auto_connect']:
                await self._connect_wallet()
            
            self.initialized = True
            logger.info("Photon trader initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Photon trader: {str(e)}")
            await self.cleanup()
            raise
            
    async def _connect_wallet(self):
        """Connect to Phantom wallet with retry logic."""
        while self.retry_count < self.max_retries and not self.wallet_connected:
            try:
                # Check if wallet is already connected
                try:
                    wallet_btn = self.driver.find_element(By.CLASS_NAME, "connect-wallet-btn")
                except NoSuchElementException:
                    logger.info("Wallet already connected")
                    self.wallet_connected = True
                    return
                    
                # Click connect wallet button
                wallet_btn.click()
                
                # Wait for Phantom popup
                time.sleep(self.config['automation']['wait_time'])
                
                # Use pyautogui to handle Phantom popup
                connect_pos = pyautogui.locateOnScreen(
                    os.path.join(self.config['automation']['screenshot_dir'], 'connect_button.png')
                )
                if connect_pos:
                    pyautogui.click(connect_pos)
                    self.wallet_connected = True
                    logger.info("Wallet connected successfully")
                    return
                    
                self.retry_count += 1
                if self.retry_count < self.max_retries:
                    logger.warning(f"Wallet connection failed, retrying ({self.retry_count}/{self.max_retries})")
                    time.sleep(self.config['wallet']['reconnect_interval'])
                    
            except Exception as e:
                logger.error(f"Failed to connect wallet: {str(e)}")
                self.retry_count += 1
                if self.retry_count < self.max_retries:
                    time.sleep(self.config['wallet']['reconnect_interval'])
                else:
                    raise
                    
    async def place_buy_order(self, token_address: str, amount_sol: float):
        """Place a buy order for a token with risk management."""
        try:
            if not self.initialized or not self.wallet_connected:
                raise Exception("Trader not initialized or wallet not connected")
                
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
            if not self.initialized or not self.wallet_connected:
                raise Exception("Trader not initialized or wallet not connected")
                
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
            if not self.initialized or not self.wallet_connected:
                raise Exception("Trader not initialized or wallet not connected")
                
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
            self.driver.quit()
        self.initialized = False
        self.wallet_connected = False
        self.retry_count = 0
