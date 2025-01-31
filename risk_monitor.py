import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import aiohttp
import asyncio
from config import *
import json
import telegram
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import platform

class RiskMonitor:
    def __init__(self):
        self.last_notification = {}
        self.bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        self.setup_browser()
        
    def setup_browser(self):
        """Setup headless browser for web scraping"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            # Add these options for Linux environments (like Streamlit Cloud)
            if platform.system() == "Linux":
                chrome_options.add_argument("--disable-software-rasterizer")
                chrome_options.add_argument("--disable-features=VizDisplayCompositor")
                chrome_options.binary_location = "/usr/bin/google-chrome"
            
            self.browser = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Browser setup failed: {str(e)}")
            self.browser = None

    def __del__(self):
        """Cleanup browser resources"""
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.quit()
        except:
            pass

    async def check_dex_screener(self, token_address):
        """Check DEX Screener for token information"""
        if not self.browser:
            return None
            
        try:
            url = f"{DEX_SCREENER_URL}/solana/{token_address}"
            self.browser.get(url)
            
            # Wait for price element
            wait = WebDriverWait(self.browser, 10)
            price_element = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "price"))
            )
            
            # Extract data
            price = float(price_element.text.strip().replace("$", ""))
            liquidity = float(self.browser.find_element(By.CLASS_NAME, "liquidity").text.replace("$", "").replace(",", ""))
            holders = int(self.browser.find_element(By.CLASS_NAME, "holders").text.replace(",", ""))
            
            return {
                "price": price,
                "liquidity": liquidity,
                "holders": holders
            }
        except Exception as e:
            print(f"Error checking DEX Screener: {str(e)}")
            return None

    async def monitor_pump_signals(self):
        """Monitor various sources for pump signals"""
        pump_signals = []
        
        for source in PUMP_DETECTION_SOURCES:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(source) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Extract relevant information based on source
                            if "pumpfun.com" in source:
                                signals = soup.find_all("div", class_="pump-signal")
                                for signal in signals:
                                    pump_signals.append({
                                        "source": source,
                                        "token": signal.get("data-token"),
                                        "probability": float(signal.get("data-probability", 0))
                                    })
                            
                            # Add more source-specific parsing here
                            
            except Exception as e:
                print(f"Error monitoring {source}: {str(e)}")
                
        return pump_signals

    def calculate_risk_score(self, token_data, pump_signals):
        """Calculate risk score based on various factors"""
        risk_factors = {
            "liquidity": 0.3,
            "holder_distribution": 0.2,
            "volume_pattern": 0.2,
            "pump_signals": 0.3
        }
        
        scores = {}
        
        # Liquidity score
        if token_data["liquidity"] > LIQUIDITY_THRESHOLD:
            scores["liquidity"] = 1.0
        else:
            scores["liquidity"] = token_data["liquidity"] / LIQUIDITY_THRESHOLD

        # Holder distribution score
        if token_data["holders"] > 1000:
            scores["holder_distribution"] = 1.0
        else:
            scores["holder_distribution"] = token_data["holders"] / 1000

        # Volume pattern score
        volume_increase = token_data.get("volume_24h", 0) / token_data.get("volume_24h_prev", 1)
        if volume_increase > VOLUME_SPIKE_THRESHOLD:
            scores["volume_pattern"] = 0.2  # High volume spike is suspicious
        else:
            scores["volume_pattern"] = 1.0

        # Pump signals score
        pump_probability = max([signal["probability"] for signal in pump_signals] or [0])
        scores["pump_signals"] = 1.0 - pump_probability  # Higher probability means higher risk

        # Calculate weighted score
        final_score = sum(scores[k] * risk_factors[k] for k in risk_factors)
        return final_score

    async def send_notification(self, message, priority="normal"):
        """Send notification via Telegram"""
        current_time = datetime.now()
        
        # Check notification cooldown
        if priority in self.last_notification:
            time_diff = (current_time - self.last_notification[priority]).total_seconds()
            if time_diff < NOTIFICATION_COOLDOWN:
                return

        try:
            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='Markdown'
            )
            self.last_notification[priority] = current_time
        except Exception as e:
            print(f"Error sending notification: {str(e)}")

    async def monitor_new_launches(self):
        """Monitor for new token launches"""
        try:
            # Monitor DEX Screener for new listings
            self.browser.get(f"{DEX_SCREENER_URL}/solana/new")
            
            new_tokens = WebDriverWait(self.browser, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "token-item"))
            )
            
            for token in new_tokens[:5]:  # Check latest 5 tokens
                token_data = {
                    "address": token.get_attribute("data-address"),
                    "name": token.find_element(By.CLASS_NAME, "token-name").text,
                    "time": token.find_element(By.CLASS_NAME, "listing-time").text
                }
                
                # Get detailed token data
                details = await self.check_dex_screener(token_data["address"])
                if details:
                    token_data.update(details)
                    
                    # Check risk score
                    pump_signals = await self.monitor_pump_signals()
                    risk_score = self.calculate_risk_score(token_data, pump_signals)
                    
                    if risk_score >= RISK_SCORE_THRESHOLD:
                        notification = (
                            f"🚀 *New Token Launch Alert*\n"
                            f"Name: {token_data['name']}\n"
                            f"Address: `{token_data['address']}`\n"
                            f"Price: ${token_data['price']:.6f}\n"
                            f"Liquidity: ${token_data['liquidity']:,.2f}\n"
                            f"Risk Score: {risk_score:.2f}\n"
                            f"Time: {token_data['time']}"
                        )
                        await self.send_notification(notification, priority="high")
                        
        except Exception as e:
            print(f"Error monitoring new launches: {str(e)}")
