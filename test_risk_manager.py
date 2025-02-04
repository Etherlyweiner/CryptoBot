import json
import logging
from cryptobot.risk_manager import RiskManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Load config
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        logger.info("Testing risk manager...")
        risk_manager = RiskManager(config.get('risk_management', {}))
        
        # Test position size calculation
        test_price = 1.0
        test_liquidity = 100000
        position_size = risk_manager.calculate_position_size(test_price, test_liquidity)
        logger.info(f"\nCalculated position size for price {test_price} and liquidity {test_liquidity}: {position_size}")
        
        # Test stop loss calculation
        entry_price = 1.0
        position_size = 1000
        stop_loss = risk_manager.calculate_stop_loss(entry_price, position_size)
        logger.info(f"\nCalculated stop loss for entry price {entry_price} and position size {position_size}: {stop_loss}")
        
        # Test take profit calculation
        take_profit = risk_manager.calculate_take_profit(entry_price, position_size)
        logger.info(f"\nCalculated take profit for entry price {entry_price} and position size {position_size}: {take_profit}")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        raise

if __name__ == "__main__":
    main()
