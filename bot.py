import ccxt
import pandas as pd
import numpy as np
from config import *
import time
import schedule
from datetime import datetime
import ta
from ml_strategy import MLStrategy
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import functools
import aiohttp

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cryptobot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CryptoBot')

def async_retry(retries=3, delay=1):
    """Decorator for async functions with retry logic"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {i+1} failed: {str(e)}")
                    if i < retries - 1:
                        await asyncio.sleep(delay * (i + 1))
            logger.error(f"All {retries} attempts failed: {str(last_exception)}")
            raise last_exception
        return wrapper
    return decorator

class CryptoBot:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        self.positions = {}
        self.ml_strategy = MLStrategy()
        self.daily_trades = 0
        self.last_trade_time = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._session = None
        self._data_cache = {}
        self._last_cache_update = {}

    async def get_session(self):
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _clear_old_cache(self, max_age_seconds=300):
        """Clear cache entries older than max_age_seconds"""
        current_time = time.time()
        for key in list(self._data_cache.keys()):
            if current_time - self._last_cache_update.get(key, 0) > max_age_seconds:
                del self._data_cache[key]
                del self._last_cache_update[key]

    @async_retry(retries=3)
    async def fetch_ohlcv(self, symbol, timeframe='1h', limit=100):
        """Fetch OHLCV data for a given symbol with caching"""
        cache_key = f"{symbol}_{timeframe}_{limit}"
        current_time = time.time()
        
        # Return cached data if fresh
        if (cache_key in self._data_cache and 
            current_time - self._last_cache_update.get(cache_key, 0) < 60):
            return self._data_cache[cache_key]

        try:
            # Clear old cache entries
            self._clear_old_cache()
            
            # Fetch new data
            ohlcv = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            )
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Cache the result
            self._data_cache[cache_key] = df
            self._last_cache_update[cache_key] = current_time
            
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None

    def calculate_signals(self, df):
        """Calculate trading signals using technical indicators"""
        if df is None or df.empty:
            return None
            
        try:
            # Calculate indicators in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(lambda: ta.momentum.rsi(df['close'], window=14)),
                    executor.submit(lambda: ta.trend.MACD(df['close'])),
                    executor.submit(lambda: ta.volatility.BollingerBands(df['close']))
                ]
                
                # Get results
                rsi = futures[0].result()
                macd = futures[1].result()
                bollinger = futures[2].result()
                
                # Assign results to dataframe
                df['RSI'] = rsi
                df['MACD'] = macd.macd()
                df['MACD_signal'] = macd.macd_signal()
                df['BB_upper'] = bollinger.bollinger_hband()
                df['BB_lower'] = bollinger.bollinger_lband()
                
            return df
        except Exception as e:
            logger.error(f"Error calculating signals: {str(e)}")
            return None

    def calculate_position_size(self, current_price):
        """Calculate the quantity based on TARGET_POSITION_SIZE"""
        try:
            return TARGET_POSITION_SIZE / current_price
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return None

    @async_retry(retries=3)
    async def update_ml_model(self):
        """Update the ML model with new data and learn from YouTube"""
        logger.info("Updating ML model...")
        try:
            for pair in TRADING_PAIRS:
                df = await self.fetch_ohlcv(pair, TIMEFRAME, limit=500)
                if df is not None:
                    df = self.calculate_signals(df)
                    await self.ml_strategy.train(df)
            
            # Learn from YouTube
            await self.ml_strategy.learn_from_youtube()
            logger.info("ML model update completed")
        except Exception as e:
            logger.error(f"Error updating ML model: {str(e)}")

    def generate_trading_decision(self, df):
        """Generate trading decision based on ML strategy"""
        try:
            if self.daily_trades >= MAX_TRADES_PER_DAY:
                return None
                
            # Get ML-based trading signal
            signal = self.ml_strategy.get_trading_signals(df)
            
            # Apply additional risk management
            if signal == 'buy':
                try:
                    balance = self.exchange.fetch_balance()
                    usdt_balance = balance.get('USDT', {}).get('free', 0)
                    if usdt_balance < TARGET_POSITION_SIZE:
                        logger.warning(f"Insufficient USDT balance: {usdt_balance}")
                        return None
                except Exception as e:
                    logger.error(f"Error checking balance: {str(e)}")
                    return None
                    
            return signal
        except Exception as e:
            logger.error(f"Error generating trading decision: {str(e)}")
            return None

    @async_retry(retries=3)
    async def execute_trade(self, symbol, side, current_price):
        """Execute a trade with position sizing and error handling"""
        try:
            quantity = self.calculate_position_size(current_price)
            if quantity is None:
                return None
                
            order = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=quantity
                )
            )
            
            # Update trading metrics
            self.daily_trades += 1
            self.last_trade_time = datetime.now()
            
            logger.info(f"Executed {side} order for {symbol}: {order}")
            
            # Place stop loss and take profit orders
            if side == 'buy':
                stop_loss_price = current_price * (1 - STOP_LOSS_PERCENTAGE)
                take_profit_price = current_price * (1 + TAKE_PROFIT_PERCENTAGE)
                
                # Place stop loss order
                await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: self.exchange.create_order(
                        symbol=symbol,
                        type='stop_loss',
                        side='sell',
                        amount=quantity,
                        price=stop_loss_price
                    )
                )
                
                # Place take profit order
                await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: self.exchange.create_order(
                        symbol=symbol,
                        type='take_profit',
                        side='sell',
                        amount=quantity,
                        price=take_profit_price
                    )
                )
            
            return order
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return None

    async def run_trading_strategy(self):
        """Run the trading strategy for all pairs"""
        try:
            # Reset daily trades counter at the start of each day
            current_time = datetime.now()
            if self.last_trade_time and self.last_trade_time.date() != current_time.date():
                self.daily_trades = 0
            
            for pair in TRADING_PAIRS:
                logger.info(f"\nAnalyzing {pair} at {current_time}")
                
                # Fetch and analyze data
                df = await self.fetch_ohlcv(pair, TIMEFRAME)
                if df is None:
                    continue
                    
                df = self.calculate_signals(df)
                if df is None:
                    continue
                    
                decision = self.generate_trading_decision(df)
                
                current_price = df.iloc[-1]['close']
                
                # Execute trades based on signals
                if decision == 'buy' and pair not in self.positions:
                    order = await self.execute_trade(pair, 'buy', current_price)
                    if order:
                        self.positions[pair] = {
                            'entry_price': float(order['price']),
                            'quantity': float(order['amount'])
                        }
                        
                elif decision == 'sell' and pair in self.positions:
                    order = await self.execute_trade(pair, 'sell', current_price)
                    if order:
                        del self.positions[pair]
        except Exception as e:
            logger.error(f"Error in trading strategy: {str(e)}")

    async def start(self):
        """Start the trading bot with ML capabilities"""
        logger.info("Starting CryptoBot with ML Strategy...")
        
        try:
            # Schedule model updates
            schedule.every(MODEL_UPDATE_INTERVAL).hours.do(
                lambda: asyncio.create_task(self.update_ml_model())
            )
            
            # Schedule trading strategy
            schedule.every(15).minutes.do(
                lambda: asyncio.create_task(self.run_trading_strategy())
            )
            
            while True:
                try:
                    schedule.run_pending()
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Critical error in bot: {str(e)}")
        finally:
            # Clean up resources
            if self._session and not self._session.closed:
                await self._session.close()
            self._executor.shutdown(wait=True)

if __name__ == "__main__":
    bot = CryptoBot()
    asyncio.run(bot.start())
