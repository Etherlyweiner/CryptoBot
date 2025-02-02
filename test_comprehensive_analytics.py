"""
Test comprehensive analytics functionality including portfolio analysis and backtesting
"""

import asyncio
import sys
import platform
from bot import TradingBot
from database import Database
from analytics_visualizer import AnalyticsVisualizer
from datetime import datetime, timedelta
import logging
from logging_config import get_logger
import json
import random

logger = get_logger('TestComprehensiveAnalytics')

async def generate_test_data(db: Database):
    """Generate test data for multiple symbols"""
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    start_date = datetime.now() - timedelta(days=90)
    
    # Generate backtest data
    backtest_data = {
        'trades': [],
        'equity_curve': []
    }
    
    equity = 10000.0  # Starting equity
    
    for symbol in symbols:
        # Generate positions with different outcomes
        base_price = 100.0 if "SOL" in symbol else 1000.0 if "ETH" in symbol else 30000.0
        
        for i in range(20):  # Generate 20 positions per symbol
            entry_date = start_date + timedelta(days=i*2)
            exit_date = entry_date + timedelta(days=1)
            
            # Randomize price movements
            price_change = random.uniform(-0.05, 0.05)
            entry_price = base_price * (1 + random.uniform(-0.02, 0.02))
            exit_price = entry_price * (1 + price_change)
            amount = random.uniform(0.1, 2.0)
            pnl = (exit_price - entry_price) * amount
            
            position_data = {
                'symbol': symbol,
                'entry_timestamp': entry_date,
                'exit_timestamp': exit_date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'amount': amount,
                'leverage': 1.0,
                'stop_loss': entry_price * 0.95,
                'take_profit': entry_price * 1.05,
                'status': 'closed',
                'pnl': pnl
            }
            
            position = db.add_position(position_data)
            if position:
                # Add corresponding trades
                trade_entry = {
                    'symbol': symbol,
                    'timestamp': entry_date,
                    'side': 'buy',
                    'price': entry_price,
                    'amount': amount,
                    'cost': entry_price * amount,
                    'fee': 0.1,
                    'realized_pnl': 0,
                    'position_id': position.id
                }
                db.add_trade(trade_entry)
                
                trade_exit = {
                    'symbol': symbol,
                    'timestamp': exit_date,
                    'side': 'sell',
                    'price': exit_price,
                    'amount': amount,
                    'cost': exit_price * amount,
                    'fee': 0.1,
                    'realized_pnl': pnl,
                    'position_id': position.id
                }
                db.add_trade(trade_exit)
                
                # Add trade to backtest data
                backtest_data['trades'].append({
                    'timestamp': entry_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': symbol,
                    'side': 'buy',
                    'price': entry_price,
                    'amount': amount,
                    'realized_pnl': 0
                })
                
                backtest_data['trades'].append({
                    'timestamp': exit_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': symbol,
                    'side': 'sell',
                    'price': exit_price,
                    'amount': amount,
                    'realized_pnl': pnl
                })
                
                # Update equity curve
                equity += pnl
                backtest_data['equity_curve'].append({
                    'timestamp': exit_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'equity': equity
                })
        
        # Generate risk metrics
        for i in range(30):  # Generate 30 days of risk metrics
            metric_date = start_date + timedelta(days=i*3)
            
            metric_data = {
                'symbol': symbol,
                'timestamp': metric_date,
                'var': random.uniform(-0.02, -0.01),
                'sharpe': random.uniform(0.8, 2.0),
                'max_drawdown': random.uniform(-0.1, -0.02),
                'volatility': random.uniform(0.1, 0.3),
                'beta': random.uniform(0.8, 1.2),
                'metrics_data': json.dumps({
                    'rolling_var': random.uniform(0.0003, 0.0008),
                    'rolling_sharpe': random.uniform(0.8, 1.5),
                    'skewness': random.uniform(-0.2, 0.2),
                    'kurtosis': random.uniform(2.8, 3.2)
                })
            }
            db.add_risk_metric(metric_data)
    
    # Store backtest data
    db.store_backtest_results(backtest_data)

async def test_comprehensive_analytics():
    try:
        # Initialize components
        bot = TradingBot()
        db = Database()
        visualizer = AnalyticsVisualizer(db)
        
        # Generate test data
        logger.info("Generating test data...")
        await generate_test_data(db)
        
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        timeframes = ['week', 'month', 'all']
        
        # Test all analytics functions
        logger.info("\nTesting individual symbol analytics...")
        for symbol in symbols:
            for timeframe in timeframes:
                logger.info(f"\nAnalyzing {symbol} for {timeframe} timeframe:")
                
                # Test performance metrics
                metrics = db.get_performance_metrics(symbol, timeframe)
                logger.info(f"Performance metrics: {json.dumps(metrics, indent=2)}")
                
                # Test position analysis
                pos_analysis = db.get_position_analysis(symbol)
                logger.info(f"Position analysis: {json.dumps(pos_analysis, indent=2)}")
                
                # Test risk analysis
                risk_analysis = db.get_risk_analysis(symbol, timeframe)
                logger.info(f"Risk analysis: {json.dumps(risk_analysis, indent=2)}")
        
        # Test portfolio analytics
        logger.info("\nTesting portfolio analytics...")
        
        # Generate comprehensive report
        logger.info("\nGenerating comprehensive report...")
        success = visualizer.generate_comprehensive_report(symbols, 'month', 'test_reports')
        if success:
            logger.info("Successfully generated comprehensive report in 'test_reports' directory")
        else:
            logger.error("Failed to generate comprehensive report")
        
        await bot.cleanup()
        db.cleanup()
        
    except Exception as e:
        logger.error(f"Error in comprehensive analytics test: {str(e)}")
        raise e

if __name__ == "__main__":
    if platform.system() == 'Windows':
        # Set up proper event loop policy for Windows
        if sys.version_info[0] == 3 and sys.version_info[1] >= 8:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_comprehensive_analytics())
