"""Main entry point for the Photon DEX trading bot."""

import os
import logging
import yaml
import asyncio
import threading
import time
from typing import Optional
from flask import Flask, jsonify, render_template
from photon_trader import PhotonTrader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize bot
bot: Optional[PhotonTrader] = None
bot_thread: Optional[threading.Thread] = None

def bot_worker(config):
    """Worker function to run the bot in a separate thread."""
    global bot
    try:
        bot = PhotonTrader(config)
        bot.setup()
        bot.navigate_to_memescope()
        while bot and bot.trading_active:
            try:
                # Scan for opportunities
                tokens = bot.scan_token_opportunities()
                if tokens:
                    logger.info(f"Found {len(tokens)} potential opportunities")
                    for token in tokens:
                        if bot.evaluate_token(token):
                            logger.info(f"Trading token: {token['name']}")
                            bot.execute_trade(token)
                
                # Check portfolio and manage positions
                bot.check_portfolio()
                
            except Exception as e:
                logger.error(f"Error in bot loop: {str(e)}")
            
            # Sleep for a short interval
            time.sleep(30)
            
    except Exception as e:
        logger.error(f"Bot worker failed: {str(e)}")
    finally:
        if bot:
            bot.cleanup()

@app.route('/')
def index():
    """Render the main dashboard."""
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the trading bot."""
    global bot, bot_thread
    try:
        if not bot and not bot_thread:
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Start bot in a separate thread
            bot_thread = threading.Thread(target=bot_worker, args=(config,))
            bot_thread.daemon = True
            bot_thread.start()
            
            return jsonify({'status': 'success', 'message': 'Bot started successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Bot is already running'})
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot."""
    global bot, bot_thread
    try:
        if bot:
            bot.trading_active = False
            bot.cleanup()
            bot = None
            bot_thread = None
            return jsonify({'status': 'success', 'message': 'Bot stopped successfully'})
        return jsonify({'status': 'error', 'message': 'Bot is not running'})
    except Exception as e:
        logger.error(f"Failed to stop bot: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get the current status of the bot."""
    global bot
    try:
        if bot:
            return jsonify({
                'status': 'running' if bot.trading_active else 'stopped',
                'wallet_balance': bot.wallet_balance,
                'active_trades': len(bot.token_data) if bot.token_data else 0
            })
        return jsonify({
            'status': 'stopped',
            'wallet_balance': None,
            'active_trades': 0
        })
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
