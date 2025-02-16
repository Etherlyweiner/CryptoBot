"""Main entry point for the Photon DEX trading bot."""

import os
import logging
import yaml
import asyncio
from typing import Optional
from flask import Flask, jsonify, render_template
from bot.photon_trader import PhotonTrader

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

def run_async(coro):
    """Run an async function in the event loop."""
    return asyncio.get_event_loop().run_until_complete(coro)

@app.route('/')
def index():
    """Render the main dashboard."""
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the trading bot."""
    global bot
    try:
        if not bot:
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            bot = PhotonTrader(config)
            run_async(bot.initialize())
        return jsonify({'status': 'success', 'message': 'Bot started successfully'})
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot."""
    global bot
    try:
        if bot:
            run_async(bot.cleanup())
            bot = None
        return jsonify({'status': 'success', 'message': 'Bot stopped successfully'})
    except Exception as e:
        logger.error(f"Failed to stop bot: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
