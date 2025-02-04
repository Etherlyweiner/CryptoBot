"""Main entry point for the trading bot."""

import os
import sys
import logging
import asyncio
import signal
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from bot.trading_bot import TradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file.
    
    Returns:
        Configuration dictionary
    """
    try:
        config_path = Path("secure_config/config.yaml")
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required fields
        required_fields = [
            ('api_keys', 'helius', 'key'),
            ('wallet', 'address'),
        ]
        
        for field_path in required_fields:
            current = config
            for key in field_path:
                if not isinstance(current, dict) or key not in current:
                    raise ValueError(f"Missing required config field: {'.'.join(field_path)}")
                current = current[key]
                
        return config
        
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        raise

class TradingBotRunner:
    """Runner for the trading bot with proper signal handling."""
    
    def __init__(self):
        """Initialize the runner."""
        self.bot: Optional[TradingBot] = None
        self.shutdown_event = asyncio.Event()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Enable debug mode if requested
        if os.environ.get('DEBUG'):
            self.loop.set_debug(True)
            logging.getLogger('asyncio').setLevel(logging.DEBUG)
        
    def handle_signal(self, signum, frame):
        """Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating shutdown...")
        if not self.shutdown_event.is_set():
            self.loop.call_soon_threadsafe(self.shutdown_event.set)
            
    async def shutdown(self):
        """Clean shutdown of the trading bot."""
        if self.bot:
            await self.bot.stop()
            
    async def run(self):
        """Run the trading bot with proper initialization and cleanup."""
        try:
            # Load configuration
            config = load_config()
            
            # Create and start bot
            self.bot = TradingBot(config)
            
            # Register signal handlers
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self.handle_signal)
                
            # Start the bot
            bot_task = self.loop.create_task(self.bot.start())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel bot task
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
                
            # Clean shutdown
            await self.shutdown()
            
        except Exception as e:
            logger.error(f"Error running trading bot: {str(e)}")
            if self.bot:
                await self.bot.stop()
            raise
            
def main():
    """Main entry point."""
    try:
        # Create and run the bot
        runner = TradingBotRunner()
        runner.loop.run_until_complete(runner.run())
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        # Clean up the event loop
        runner.loop.close()
        
if __name__ == "__main__":
    main()
