"""
Test advanced analytics functionality
"""

import asyncio
import sys
import platform
from bot import TradingBot
from database import Database
from datetime import datetime, timedelta
import logging
from logging_config import get_logger
import json

logger = get_logger('TestAnalytics')

async def test_analytics():
    try:
        bot = TradingBot()
        db = Database()
        symbol = "SOL/USDT"
        
        # Generate some test data
        logger.info("Generating test data...")
        
        # Create positions with different outcomes
        positions = [
            {
                'symbol': symbol,
                'entry_timestamp': datetime.now() - timedelta(days=30),
                'exit_timestamp': datetime.now() - timedelta(days=25),
                'entry_price': 100.0,
                'exit_price': 110.0,
                'amount': 1.0,
                'leverage': 1.0,
                'stop_loss': 95.0,
                'take_profit': 115.0,
                'status': 'closed',
                'pnl': 10.0
            },
            {
                'symbol': symbol,
                'entry_timestamp': datetime.now() - timedelta(days=20),
                'exit_timestamp': datetime.now() - timedelta(days=15),
                'entry_price': 105.0,
                'exit_price': 95.0,
                'amount': 1.5,
                'leverage': 1.0,
                'stop_loss': 90.0,
                'take_profit': 120.0,
                'status': 'closed',
                'pnl': -15.0
            },
            {
                'symbol': symbol,
                'entry_timestamp': datetime.now() - timedelta(days=10),
                'entry_price': 98.0,
                'amount': 2.0,
                'leverage': 1.0,
                'stop_loss': 95.0,
                'take_profit': 110.0,
                'status': 'open'
            }
        ]
        
        for pos_data in positions:
            position = db.add_position(pos_data)
            if position:
                logger.info(f"Created position: {position.to_dict()}")
        
        # Create trades for these positions
        trades = [
            {
                'symbol': symbol,
                'timestamp': datetime.now() - timedelta(days=30),
                'side': 'buy',
                'price': 100.0,
                'amount': 1.0,
                'cost': 100.0,
                'fee': 0.1,
                'realized_pnl': None,
                'position_id': 1
            },
            {
                'symbol': symbol,
                'timestamp': datetime.now() - timedelta(days=25),
                'side': 'sell',
                'price': 110.0,
                'amount': 1.0,
                'cost': 110.0,
                'fee': 0.1,
                'realized_pnl': 10.0,
                'position_id': 1
            },
            {
                'symbol': symbol,
                'timestamp': datetime.now() - timedelta(days=20),
                'side': 'buy',
                'price': 105.0,
                'amount': 1.5,
                'cost': 157.5,
                'fee': 0.15,
                'realized_pnl': None,
                'position_id': 2
            },
            {
                'symbol': symbol,
                'timestamp': datetime.now() - timedelta(days=15),
                'side': 'sell',
                'price': 95.0,
                'amount': 1.5,
                'cost': 142.5,
                'fee': 0.15,
                'realized_pnl': -15.0,
                'position_id': 2
            },
            {
                'symbol': symbol,
                'timestamp': datetime.now() - timedelta(days=10),
                'side': 'buy',
                'price': 98.0,
                'amount': 2.0,
                'cost': 196.0,
                'fee': 0.2,
                'realized_pnl': None,
                'position_id': 3
            }
        ]
        
        for trade_data in trades:
            trade = db.add_trade(trade_data)
            if trade:
                logger.info(f"Created trade: {trade.to_dict()}")
        
        # Generate some risk metrics
        risk_metrics = [
            {
                'symbol': symbol,
                'timestamp': datetime.now() - timedelta(days=30),
                'var': -0.02,
                'sharpe': 1.5,
                'max_drawdown': -0.05,
                'volatility': 0.2,
                'beta': 1.1,
                'metrics_data': json.dumps({
                    'rolling_var': 0.0004,
                    'rolling_sharpe': 1.2,
                    'skewness': 0.1,
                    'kurtosis': 3.0
                })
            },
            {
                'symbol': symbol,
                'timestamp': datetime.now() - timedelta(days=15),
                'var': -0.025,
                'sharpe': 1.2,
                'max_drawdown': -0.08,
                'volatility': 0.25,
                'beta': 1.2,
                'metrics_data': json.dumps({
                    'rolling_var': 0.0005,
                    'rolling_sharpe': 1.0,
                    'skewness': 0.2,
                    'kurtosis': 3.2
                })
            },
            {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'var': -0.03,
                'sharpe': 1.0,
                'max_drawdown': -0.1,
                'volatility': 0.3,
                'beta': 1.3,
                'metrics_data': json.dumps({
                    'rolling_var': 0.0006,
                    'rolling_sharpe': 0.8,
                    'skewness': 0.3,
                    'kurtosis': 3.5
                })
            }
        ]
        
        for metric_data in risk_metrics:
            metric = db.add_risk_metric(metric_data)
            if metric:
                logger.info(f"Created risk metric: {metric.to_dict()}")
        
        # Test analytics functions
        logger.info("\nTesting performance metrics...")
        perf_metrics = db.get_performance_metrics(symbol)
        logger.info(f"Performance metrics: {json.dumps(perf_metrics, indent=2)}")
        
        logger.info("\nTesting position analysis...")
        pos_analysis = db.get_position_analysis(symbol)
        logger.info(f"Position analysis: {json.dumps(pos_analysis, indent=2)}")
        
        logger.info("\nTesting risk analysis...")
        risk_analysis = db.get_risk_analysis(symbol)
        logger.info(f"Risk analysis: {json.dumps(risk_analysis, indent=2)}")
        
        # Test different timeframes
        for timeframe in ['today', 'week', 'month', 'year', 'all']:
            logger.info(f"\nTesting {timeframe} timeframe...")
            metrics = db.get_performance_metrics(symbol, timeframe)
            logger.info(f"{timeframe.capitalize()} metrics: {json.dumps(metrics, indent=2)}")
        
        await bot.cleanup()
        db.cleanup()
        
    except Exception as e:
        logger.error(f"Error in analytics test: {str(e)}")

if __name__ == "__main__":
    if platform.system() == 'Windows':
        # Set up proper event loop policy for Windows
        if sys.version_info[0] == 3 and sys.version_info[1] >= 8:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_analytics())
