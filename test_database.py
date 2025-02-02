"""
Test database functionality
"""

from database import Database
from datetime import datetime

def test_database():
    try:
        db = Database()
        
        # Create a test position
        position_data = {
            'symbol': 'SOL/USDT',
            'entry_timestamp': datetime.now(),
            'entry_price': 100.0,
            'amount': 1.0,
            'leverage': 1.0,
            'stop_loss': 95.0,
            'take_profit': 110.0,
            'status': 'open'
        }
        
        position = db.add_position(position_data)
        if position:
            print(f"Created position: {position.to_dict()}")
            
            # Create a test trade
            trade_data = {
                'symbol': 'SOL/USDT',
                'timestamp': datetime.now(),
                'side': 'buy',
                'price': 100.0,
                'amount': 1.0,
                'cost': 100.0,
                'fee': 0.1,
                'position_id': position.id
            }
            
            trade = db.add_trade(trade_data)
            if trade:
                print(f"Created trade: {trade.to_dict()}")
        
        # Test queries
        open_positions = db.get_open_positions()
        print(f"\nOpen positions: {len(open_positions)}")
        for pos in open_positions:
            print(pos)
        
        trades = db.get_trades('SOL/USDT')
        print(f"\nRecent trades: {len(trades)}")
        for trade in trades:
            print(trade)
        
        summary = db.get_performance_summary('SOL/USDT')
        print(f"\nPerformance summary: {summary}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        db.cleanup()

if __name__ == "__main__":
    test_database()
