"""
Monitoring and reporting module for CryptoBot
"""
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
import aiohttp
import asyncio
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger('CryptoBot.Monitoring')

@dataclass
class TradeAlert:
    token: str
    type: str  # 'entry', 'exit', 'error', 'warning'
    message: str
    timestamp: datetime
    data: Dict[str, Any]

@dataclass
class PerformanceMetrics:
    total_pnl: float
    daily_pnl: float
    win_rate: float
    avg_trade_duration: float
    sharpe_ratio: float
    max_drawdown: float
    current_drawdown: float
    open_positions: int
    total_trades: int
    timestamp: datetime

class MonitoringSystem:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {
            'log_dir': 'logs',
            'data_dir': 'data',
            'telegram_token': None,
            'telegram_chat_id': None,
            'discord_webhook': None,
            'alert_levels': {
                'drawdown_warning': 0.05,
                'drawdown_critical': 0.1,
                'pnl_warning': -0.02,
                'pnl_critical': -0.05
            }
        }
        
        # Initialize directories
        self.log_dir = Path(self.config['log_dir'])
        self.data_dir = Path(self.config['data_dir'])
        self.log_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.telegram_bot = None
        if self.config['telegram_token']:
            self.telegram_bot = Bot(token=self.config['telegram_token'])
            
        self._session: Optional[aiohttp.ClientSession] = None
        self.alerts: List[TradeAlert] = []
        self.metrics_history: List[PerformanceMetrics] = []
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
        
    async def log_trade(self, trade_data: Dict[str, Any]):
        """Log trade information to file and notify if necessary"""
        try:
            # Create trade log
            timestamp = datetime.utcnow()
            log_file = self.log_dir / f"trades_{timestamp.strftime('%Y%m')}.json"
            
            trade_log = {
                'timestamp': timestamp.isoformat(),
                'trade_data': trade_data
            }
            
            # Append to log file
            with open(log_file, 'a') as f:
                f.write(json.dumps(trade_log) + '\n')
                
            # Check for alerts
            if trade_data.get('pnl'):
                if trade_data['pnl'] < self.config['alert_levels']['pnl_critical']:
                    await self.create_alert(
                        trade_data['token'],
                        'warning',
                        f"Critical PNL loss: {trade_data['pnl']:.2%}",
                        trade_data
                    )
                    
        except Exception as e:
            logger.error(f"Error logging trade: {str(e)}")
            
    async def create_alert(self, token: str, alert_type: str, message: str, data: Dict[str, Any]):
        """Create and send alert"""
        try:
            alert = TradeAlert(
                token=token,
                type=alert_type,
                message=message,
                timestamp=datetime.utcnow(),
                data=data
            )
            
            self.alerts.append(alert)
            
            # Send notifications
            await self._send_notifications(alert)
            
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")
            
    async def _send_notifications(self, alert: TradeAlert):
        """Send notifications to configured channels"""
        try:
            message = f"""
🚨 {alert.type.upper()} ALERT
Token: {alert.token}
Message: {alert.message}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
            
            # Send to Telegram if configured
            if self.telegram_bot and self.config['telegram_chat_id']:
                try:
                    await self.telegram_bot.send_message(
                        chat_id=self.config['telegram_chat_id'],
                        text=message
                    )
                except TelegramError as e:
                    logger.error(f"Telegram notification failed: {str(e)}")
                    
            # Send to Discord if configured
            if self.config['discord_webhook']:
                try:
                    session = await self._get_session()
                    webhook_data = {
                        'content': message,
                        'username': 'CryptoBot Monitor'
                    }
                    async with session.post(
                        self.config['discord_webhook'],
                        json=webhook_data
                    ) as response:
                        if response.status != 204:
                            logger.error(f"Discord notification failed: {response.status}")
                except Exception as e:
                    logger.error(f"Discord notification failed: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
            
    async def update_metrics(self, metrics: Dict[str, Any]):
        """Update performance metrics"""
        try:
            performance = PerformanceMetrics(
                total_pnl=metrics['total_pnl'],
                daily_pnl=metrics['daily_pnl'],
                win_rate=metrics['win_rate'],
                avg_trade_duration=metrics['avg_trade_duration'],
                sharpe_ratio=metrics['sharpe_ratio'],
                max_drawdown=metrics['max_drawdown'],
                current_drawdown=metrics['current_drawdown'],
                open_positions=metrics['open_positions'],
                total_trades=metrics['total_trades'],
                timestamp=datetime.utcnow()
            )
            
            self.metrics_history.append(performance)
            
            # Save metrics to file
            metrics_file = self.data_dir / f"metrics_{performance.timestamp.strftime('%Y%m')}.json"
            with open(metrics_file, 'a') as f:
                f.write(json.dumps(asdict(performance)) + '\n')
                
            # Check for alerts
            if performance.current_drawdown > self.config['alert_levels']['drawdown_warning']:
                await self.create_alert(
                    'PORTFOLIO',
                    'warning',
                    f"High drawdown: {performance.current_drawdown:.2%}",
                    asdict(performance)
                )
                
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
            
    def generate_report(self, start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate performance report"""
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
                
            # Filter metrics
            metrics = [m for m in self.metrics_history if m.timestamp >= start_date]
            if not metrics:
                return {}
                
            # Calculate statistics
            df = pd.DataFrame([asdict(m) for m in metrics])
            
            report = {
                'period_start': start_date.isoformat(),
                'period_end': datetime.utcnow().isoformat(),
                'total_pnl': df['total_pnl'].iloc[-1],
                'max_drawdown': df['max_drawdown'].min(),
                'win_rate': df['win_rate'].mean(),
                'sharpe_ratio': df['sharpe_ratio'].iloc[-1],
                'total_trades': df['total_trades'].iloc[-1],
                'current_positions': df['open_positions'].iloc[-1],
                'daily_stats': {
                    'mean_pnl': df['daily_pnl'].mean(),
                    'std_pnl': df['daily_pnl'].std(),
                    'best_day': df['daily_pnl'].max(),
                    'worst_day': df['daily_pnl'].min()
                }
            }
            
            # Generate plots
            self._generate_performance_plots(df, start_date)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return {}
            
    def _generate_performance_plots(self, df: pd.DataFrame, start_date: datetime):
        """Generate performance visualization plots"""
        try:
            # Set style
            plt.style.use('seaborn')
            
            # Equity curve
            plt.figure(figsize=(12, 6))
            plt.plot(df['timestamp'], df['total_pnl'].cumsum(), label='Equity Curve')
            plt.title('Portfolio Performance')
            plt.xlabel('Date')
            plt.ylabel('Cumulative PnL')
            plt.legend()
            plt.savefig(self.data_dir / 'equity_curve.png')
            plt.close()
            
            # Drawdown
            plt.figure(figsize=(12, 6))
            plt.plot(df['timestamp'], df['current_drawdown'], label='Drawdown', color='red')
            plt.title('Portfolio Drawdown')
            plt.xlabel('Date')
            plt.ylabel('Drawdown %')
            plt.legend()
            plt.savefig(self.data_dir / 'drawdown.png')
            plt.close()
            
            # Daily PnL distribution
            plt.figure(figsize=(10, 6))
            sns.histplot(df['daily_pnl'], bins=50)
            plt.title('Daily PnL Distribution')
            plt.xlabel('Daily PnL')
            plt.ylabel('Frequency')
            plt.savefig(self.data_dir / 'pnl_distribution.png')
            plt.close()
            
        except Exception as e:
            logger.error(f"Error generating plots: {str(e)}")
            
    async def cleanup(self):
        """Clean up resources"""
        if self._session and not self._session.closed:
            await self._session.close()
