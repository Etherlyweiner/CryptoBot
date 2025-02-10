"""Flask application for CryptoBot dashboard."""

import os
import logging
import yaml
from typing import Optional
import asyncio
from flask import Flask, jsonify, render_template, request
from bot import CryptoBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Initialize bot
bot: Optional[CryptoBot] = None

@app.route('/')
def index():
    """Render main dashboard."""
    return render_template('index.html')

@app.route('/config')
def get_config():
    """Get bot configuration."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
        if not os.path.exists(config_path):
            return jsonify({'error': 'Configuration file not found'}), 404
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return jsonify(config)
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/status')
def get_bot_status():
    """Get bot status."""
    if not bot:
        return jsonify({'error': 'Bot not initialized'}), 500
    return jsonify(bot.get_status())

@app.route('/api/bot/start', methods=['POST'])
async def start_bot():
    """Start the bot."""
    global bot
    try:
        if not bot:
            bot = CryptoBot('config/config.yaml')
            await bot.initialize()
        await bot.start()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/stop', methods=['POST'])
async def stop_bot():
    """Stop the bot."""
    global bot
    try:
        if bot:
            await bot.stop()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Failed to stop bot: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
def get_performance():
    """Get performance metrics."""
    if not bot or not bot.analytics:
        return jsonify({'error': 'Bot not initialized'}), 500
    return jsonify(bot.analytics.get_summary())

@app.route('/api/positions')
def get_positions():
    """Get open positions."""
    if not bot or not bot.strategy:
        return jsonify({'error': 'Bot not initialized'}), 500
    return jsonify(bot.strategy.get_positions())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
