"""
Database management for CryptoBot with SQLAlchemy
"""

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, ForeignKey, JSON, Table, MetaData, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import json
from logging_config import get_logger
import numpy as np
import scipy.stats as stats
import itertools

logger = get_logger('Database')

Base = declarative_base()

class Trade(Base):
    """Trade history model"""
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    side = Column(String, nullable=False)  # 'buy' or 'sell'
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    fee = Column(Float)
    realized_pnl = Column(Float)
    position_id = Column(Integer, ForeignKey('positions.id'))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'side': self.side,
            'price': self.price,
            'amount': self.amount,
            'cost': self.cost,
            'fee': self.fee,
            'realized_pnl': self.realized_pnl,
            'position_id': self.position_id
        }

class Position(Base):
    """Trading position model"""
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    entry_timestamp = Column(DateTime, nullable=False)
    exit_timestamp = Column(DateTime)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    amount = Column(Float, nullable=False)
    leverage = Column(Float, default=1.0)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(String, nullable=False)  # 'open' or 'closed'
    pnl = Column(Float)
    trades = relationship("Trade", backref="position")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'entry_timestamp': self.entry_timestamp,
            'exit_timestamp': self.exit_timestamp,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'amount': self.amount,
            'leverage': self.leverage,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'status': self.status,
            'pnl': self.pnl
        }

class RiskMetric(Base):
    """Risk metrics model"""
    __tablename__ = 'risk_metrics'

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    var = Column(Float)
    sharpe = Column(Float)
    max_drawdown = Column(Float)
    volatility = Column(Float)
    beta = Column(Float)
    metrics_data = Column(String)  # JSON string for additional metrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'var': self.var,
            'sharpe': self.sharpe,
            'max_drawdown': self.max_drawdown,
            'volatility': self.volatility,
            'beta': self.beta,
            'metrics_data': json.loads(self.metrics_data) if self.metrics_data else {}
        }

class NewToken(Base):
    """Model for storing new token listings"""
    __tablename__ = 'new_tokens'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    source = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100))
    initial_price = Column(Float)
    initial_market_cap = Column(Float)
    chain = Column(String(50))
    contract_address = Column(String(100))
    description = Column(Text)
    website = Column(String(200))
    social_links = Column(JSON)
    launch_date = Column(DateTime)

class TokenAnalysis(Base):
    """Model for storing token analysis results"""
    __tablename__ = 'token_analysis'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    symbol = Column(String(20), nullable=False)
    initial_momentum = Column(Float)
    social_score = Column(Float)
    risk_score = Column(Float)
    opportunity_score = Column(Float)

class Alert(Base):
    """Model for storing alerts"""
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100))
    opportunity_score = Column(Float)
    momentum_score = Column(Float)
    social_score = Column(Float)
    risk_score = Column(Float)
    alert_message = Column(Text)

class Database:
    def __init__(self, db_url: str = 'sqlite:///cryptobot.db'):
        """Initialize database connection"""
        try:
            self.engine = create_engine(db_url)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

    def add_trade(self, trade_data: Dict[str, Any]) -> Optional[Trade]:
        """Add a new trade to the database"""
        try:
            trade = Trade(**trade_data)
            self.session.add(trade)
            self.session.commit()
            logger.info(f"Added trade for {trade.symbol}")
            return trade
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding trade: {str(e)}")
            return None

    def add_position(self, position_data: Dict[str, Any]) -> Optional[Position]:
        """Add a new position to the database"""
        try:
            position = Position(**position_data)
            self.session.add(position)
            self.session.commit()
            logger.info(f"Added position for {position.symbol}")
            return position
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding position: {str(e)}")
            return None

    def update_position(self, position_id: int, update_data: Dict[str, Any]) -> Optional[Position]:
        """Update an existing position"""
        try:
            position = self.session.query(Position).filter_by(id=position_id).first()
            if position:
                for key, value in update_data.items():
                    setattr(position, key, value)
                self.session.commit()
                logger.info(f"Updated position {position_id}")
                return position
            return None
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating position: {str(e)}")
            return None

    def add_risk_metric(self, metric_data: Dict[str, Any]) -> Optional[RiskMetric]:
        """Add a new risk metric record"""
        try:
            if 'metrics_data' in metric_data and isinstance(metric_data['metrics_data'], dict):
                metric_data['metrics_data'] = json.dumps(metric_data['metrics_data'])
            metric = RiskMetric(**metric_data)
            self.session.add(metric)
            self.session.commit()
            logger.info(f"Added risk metrics for {metric.symbol}")
            return metric
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding risk metric: {str(e)}")
            return None

    def get_trades(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades"""
        try:
            query = self.session.query(Trade)
            if symbol:
                query = query.filter_by(symbol=symbol)
            trades = query.order_by(Trade.timestamp.desc()).limit(limit).all()
            return [trade.to_dict() for trade in trades]
        except Exception as e:
            logger.error(f"Error getting trades: {str(e)}")
            return []

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        try:
            positions = self.session.query(Position).filter_by(status='open').all()
            return [pos.to_dict() for pos in positions]
        except Exception as e:
            logger.error(f"Error getting open positions: {str(e)}")
            return []

    def get_position_history(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get position history"""
        try:
            query = self.session.query(Position).filter_by(status='closed')
            if symbol:
                query = query.filter_by(symbol=symbol)
            positions = query.order_by(Position.exit_timestamp.desc()).all()
            return [pos.to_dict() for pos in positions]
        except Exception as e:
            logger.error(f"Error getting position history: {str(e)}")
            return []

    def get_risk_metrics(self, symbol: str, start_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get risk metrics history"""
        try:
            query = self.session.query(RiskMetric).filter_by(symbol=symbol)
            if start_time:
                query = query.filter(RiskMetric.timestamp >= start_time)
            metrics = query.order_by(RiskMetric.timestamp.desc()).all()
            return [metric.to_dict() for metric in metrics]
        except Exception as e:
            logger.error(f"Error getting risk metrics: {str(e)}")
            return []

    def get_performance_summary(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get trading performance summary"""
        try:
            query = self.session.query(Position).filter_by(status='closed')
            if symbol:
                query = query.filter_by(symbol=symbol)
            positions = query.all()

            if not positions:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'average_pnl': 0,
                    'max_drawdown': 0,
                    'best_trade': 0,
                    'worst_trade': 0
                }

            pnls = [p.pnl for p in positions if p.pnl is not None]
            winning_trades = len([p for p in pnls if p > 0])
            losing_trades = len([p for p in pnls if p < 0])

            return {
                'total_trades': len(positions),
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': (winning_trades / len(positions)) * 100 if positions else 0,
                'total_pnl': sum(pnls),
                'average_pnl': sum(pnls) / len(pnls) if pnls else 0,
                'max_drawdown': min(pnls) if pnls else 0,
                'best_trade': max(pnls) if pnls else 0,
                'worst_trade': min(pnls) if pnls else 0
            }
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {}

    def get_performance_metrics(self, symbol: str, timeframe: str = 'all') -> Dict[str, Any]:
        """Get detailed performance metrics for a symbol"""
        try:
            trades_query = self.session.query(Trade).filter(Trade.symbol == symbol)
            trades = trades_query.all()
            if not trades:
                return {}

            # Convert trades to DataFrame for analysis
            df = pd.DataFrame([{
                'timestamp': t.timestamp,
                'side': t.side,
                'price': t.price,
                'amount': t.amount,
                'cost': t.cost,
                'fee': t.fee,
                'realized_pnl': t.realized_pnl,
                'position_id': t.position_id
            } for t in trades])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

            # Filter by timeframe
            if timeframe != 'all':
                if timeframe == 'today':
                    df = df[df.index.date == datetime.now().date()]
                elif timeframe == 'week':
                    df = df[df.index >= (datetime.now() - timedelta(days=7))]
                elif timeframe == 'month':
                    df = df[df.index >= (datetime.now() - timedelta(days=30))]
                elif timeframe == 'year':
                    df = df[df.index >= (datetime.now() - timedelta(days=365))]

            if df.empty:
                return {}

            # Calculate trade metrics
            total_trades = len(df)
            winning_trades = len(df[df['realized_pnl'] > 0])
            losing_trades = len(df[df['realized_pnl'] < 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # PnL metrics
            total_pnl = df['realized_pnl'].sum()
            avg_pnl = df['realized_pnl'].mean()
            pnl_std = df['realized_pnl'].std()
            best_trade = df['realized_pnl'].max()
            worst_trade = df['realized_pnl'].min()
            
            # Calculate Sharpe ratio (assuming daily returns)
            daily_returns = df.resample('D')['realized_pnl'].sum()
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if len(daily_returns) > 1 else 0
            
            # Calculate drawdown
            cumulative_pnl = df['realized_pnl'].cumsum()
            rolling_max = cumulative_pnl.expanding(min_periods=1).max()
            drawdowns = (cumulative_pnl - rolling_max) / rolling_max
            max_drawdown = drawdowns.min()
            
            # Volume metrics
            total_volume = df['amount'].sum()
            avg_trade_size = df['amount'].mean()
            
            # Time metrics
            avg_trade_duration = self._calculate_avg_trade_duration(df)
            trades_per_day = len(df) / ((df.index.max() - df.index.min()).days + 1)
            
            # Risk metrics
            risk_metrics = self._calculate_risk_metrics(df)
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': float(total_pnl),
                'average_pnl': float(avg_pnl),
                'pnl_std': float(pnl_std),
                'best_trade': float(best_trade),
                'worst_trade': float(worst_trade),
                'sharpe_ratio': float(sharpe),
                'max_drawdown': float(max_drawdown),
                'total_volume': float(total_volume),
                'average_trade_size': float(avg_trade_size),
                'average_trade_duration': avg_trade_duration,
                'trades_per_day': float(trades_per_day),
                'risk_metrics': risk_metrics
            }
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {str(e)}")
            return {}

    def get_equity_history(self, symbol: str, timeframe: str = 'all') -> List[Dict[str, Any]]:
        """Get equity curve history for a symbol"""
        try:
            trades = self.session.query(Trade).filter_by(symbol=symbol).all()
            if not trades:
                return []

            # Convert trades to DataFrame
            df = pd.DataFrame([{
                'timestamp': t.timestamp,
                'realized_pnl': t.realized_pnl if t.realized_pnl else 0.0
            } for t in trades])

            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

            # Filter by timeframe
            if timeframe != 'all':
                if timeframe == 'today':
                    df = df[df.index.date == datetime.now().date()]
                elif timeframe == 'week':
                    df = df[df.index >= (datetime.now() - timedelta(days=7))]
                elif timeframe == 'month':
                    df = df[df.index >= (datetime.now() - timedelta(days=30))]
                elif timeframe == 'year':
                    df = df[df.index >= (datetime.now() - timedelta(days=365))]

            if df.empty:
                return []

            # Calculate equity curve
            initial_equity = 10000  # Default initial equity
            df['equity'] = initial_equity + df['realized_pnl'].cumsum()

            # Convert to list of dictionaries
            equity_history = [{
                'timestamp': index.strftime('%Y-%m-%d %H:%M:%S'),
                'equity': float(row['equity'])
            } for index, row in df.iterrows()]

            return equity_history

        except Exception as e:
            logger.error(f"Error getting equity history: {str(e)}")
            return []

    def get_position_analysis(self, symbol: str = None) -> Dict[str, Any]:
        """Analyze position performance and risk"""
        try:
            query = self.session.query(Position)
            if symbol:
                query = query.filter(Position.symbol == symbol)
            positions = query.all()

            if not positions:
                return {}

            # Convert to DataFrame
            df = pd.DataFrame([{
                'entry_timestamp': p.entry_timestamp,
                'exit_timestamp': p.exit_timestamp,
                'entry_price': p.entry_price,
                'exit_price': p.exit_price,
                'amount': p.amount,
                'leverage': p.leverage,
                'stop_loss': p.stop_loss,
                'take_profit': p.take_profit,
                'status': p.status,
                'pnl': p.pnl
            } for p in positions])
            
            df['entry_timestamp'] = pd.to_datetime(df['entry_timestamp'])
            df['exit_timestamp'] = pd.to_datetime(df['exit_timestamp'])

            # Calculate position metrics
            total_positions = len(df)
            open_positions = len(df[df['status'] == 'open'])
            closed_positions = len(df[df['status'] == 'closed'])
            
            # PnL analysis for closed positions
            closed_df = df[df['status'] == 'closed'].copy()
            if not closed_df.empty:
                total_pnl = closed_df['pnl'].sum()
                avg_pnl = closed_df['pnl'].mean()
                pnl_std = closed_df['pnl'].std()
                best_position = closed_df['pnl'].max()
                worst_position = closed_df['pnl'].min()
                
                # Calculate holding periods
                closed_df['holding_period'] = (closed_df['exit_timestamp'] - closed_df['entry_timestamp']).dt.total_seconds() / 3600  # in hours
                avg_holding_period = closed_df['holding_period'].mean()
                
                # Calculate win rate
                winning_positions = len(closed_df[closed_df['pnl'] > 0])
                win_rate = winning_positions / len(closed_df)
            else:
                total_pnl = avg_pnl = pnl_std = best_position = worst_position = avg_holding_period = win_rate = 0

            # Risk exposure analysis
            current_exposure = df[df['status'] == 'open']['amount'].sum()
            avg_leverage = df['leverage'].mean()
            
            # Stop loss and take profit analysis
            sl_tp_ratio = self._calculate_sl_tp_ratio(df)
            
            return {
                'total_positions': total_positions,
                'open_positions': open_positions,
                'closed_positions': closed_positions,
                'total_pnl': float(total_pnl),
                'average_pnl': float(avg_pnl),
                'pnl_std': float(pnl_std),
                'best_position': float(best_position),
                'worst_position': float(worst_position),
                'win_rate': float(win_rate),
                'average_holding_period': float(avg_holding_period),
                'current_exposure': float(current_exposure),
                'average_leverage': float(avg_leverage),
                'sl_tp_ratio': sl_tp_ratio
            }
        except Exception as e:
            logger.error(f"Error analyzing positions: {str(e)}")
            return {}

    def get_risk_analysis(self, symbol: str = None, timeframe: str = 'all') -> Dict[str, Any]:
        """Get comprehensive risk analysis"""
        try:
            query = self.session.query(RiskMetric)
            if symbol:
                query = query.filter(RiskMetric.symbol == symbol)
            
            # Apply timeframe filter
            if timeframe != 'all':
                if timeframe == 'today':
                    query = query.filter(RiskMetric.timestamp >= datetime.now().date())
                elif timeframe == 'week':
                    query = query.filter(RiskMetric.timestamp >= datetime.now() - timedelta(days=7))
                elif timeframe == 'month':
                    query = query.filter(RiskMetric.timestamp >= datetime.now() - timedelta(days=30))
                elif timeframe == 'year':
                    query = query.filter(RiskMetric.timestamp >= datetime.now() - timedelta(days=365))

            metrics = query.all()
            if not metrics:
                return {}

            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': m.timestamp,
                'var': m.var,
                'sharpe': m.sharpe,
                'max_drawdown': m.max_drawdown,
                'volatility': m.volatility,
                'beta': m.beta,
                'metrics_data': m.metrics_data
            } for m in metrics])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

            # Calculate average metrics
            avg_var = df['var'].mean()
            avg_sharpe = df['sharpe'].mean()
            avg_volatility = df['volatility'].mean()
            avg_beta = df['beta'].mean()
            
            # Calculate metric trends
            var_trend = self._calculate_metric_trend(df['var'])
            sharpe_trend = self._calculate_metric_trend(df['sharpe'])
            volatility_trend = self._calculate_metric_trend(df['volatility'])
            
            # Parse and analyze additional metrics
            additional_metrics = []
            for _, row in df.iterrows():
                try:
                    metrics_data = json.loads(row['metrics_data'])
                    additional_metrics.append(metrics_data)
                except:
                    continue

            if additional_metrics:
                avg_additional = {
                    key: np.mean([m[key] for m in additional_metrics if key in m])
                    for key in additional_metrics[0].keys()
                }
            else:
                avg_additional = {}

            return {
                'average_var': float(avg_var),
                'average_sharpe': float(avg_sharpe),
                'average_volatility': float(avg_volatility),
                'average_beta': float(avg_beta),
                'var_trend': var_trend,
                'sharpe_trend': sharpe_trend,
                'volatility_trend': volatility_trend,
                'additional_metrics': avg_additional,
                'sample_size': len(df),
                'date_range': {
                    'start': df.index.min().isoformat(),
                    'end': df.index.max().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing risk metrics: {str(e)}")
            return {}

    def store_backtest_results(self, backtest_data: Dict[str, Any]) -> bool:
        """Store backtest results in the database"""
        try:
            # Convert timestamps to datetime objects
            for trade in backtest_data['trades']:
                trade['timestamp'] = pd.to_datetime(trade['timestamp'])
            
            for point in backtest_data['equity_curve']:
                point['timestamp'] = pd.to_datetime(point['timestamp'])
            
            self._backtest_results = backtest_data
            return True
        except Exception as e:
            logger.error(f"Error storing backtest results: {str(e)}")
            return False
    
    def get_backtest_results(self) -> Optional[Dict[str, Any]]:
        """Retrieve backtest results from the database"""
        try:
            # First try to get stored backtest results
            if hasattr(self, '_backtest_results'):
                # Convert timestamps to string format for JSON serialization
                results = {
                    'trades': [],
                    'equity_curve': []
                }
                
                for trade in self._backtest_results['trades']:
                    trade_copy = trade.copy()
                    if isinstance(trade['timestamp'], pd.Timestamp):
                        trade_copy['timestamp'] = trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    results['trades'].append(trade_copy)
                
                for point in self._backtest_results['equity_curve']:
                    point_copy = point.copy()
                    if isinstance(point['timestamp'], pd.Timestamp):
                        point_copy['timestamp'] = point['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    results['equity_curve'].append(point_copy)
                
                return results
            
            # If no stored results, generate from trades
            trades = self.session.query(Trade).all()
            if not trades:
                return None

            # Convert trades to list of dictionaries
            trades_data = [{
                'timestamp': t.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': t.symbol,
                'side': t.side,
                'price': float(t.price),
                'amount': float(t.amount),
                'cost': float(t.cost),
                'fee': float(t.fee) if t.fee else 0.0,
                'realized_pnl': float(t.realized_pnl) if t.realized_pnl else 0.0
            } for t in trades]

            # Calculate equity curve
            df = pd.DataFrame(trades_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.sort_values('timestamp', inplace=True)
            
            # Calculate cumulative PnL and equity curve
            initial_equity = 10000  # Default initial equity
            df['cumulative_pnl'] = df['realized_pnl'].cumsum()
            df['equity'] = initial_equity + df['cumulative_pnl']
            
            equity_curve = [{
                'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'equity': float(row['equity'])
            } for _, row in df.iterrows()]

            results = {
                'trades': trades_data,
                'equity_curve': equity_curve
            }

            return results
        except Exception as e:
            logger.error(f"Error retrieving backtest results: {str(e)}")
            return None

    def store_new_token(self, token_data: Dict[str, Any]) -> bool:
        """Store new token data in the database"""
        try:
            new_token = NewToken(**token_data)
            self.session.add(new_token)
            self.session.commit()
            logger.info(f"Stored new token: {token_data['symbol']}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error storing new token: {str(e)}")
            return False

    def store_token_analysis(self, analysis_data: Dict[str, Any]) -> bool:
        """Store token analysis results"""
        try:
            analysis = TokenAnalysis(**analysis_data)
            self.session.add(analysis)
            self.session.commit()
            logger.info(f"Stored analysis for token: {analysis_data['symbol']}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error storing token analysis: {str(e)}")
            return False

    def store_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Store alert in the database"""
        try:
            alert = Alert(**alert_data)
            self.session.add(alert)
            self.session.commit()
            logger.info(f"Stored alert for token: {alert_data['symbol']}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error storing alert: {str(e)}")
            return False

    def get_recent_tokens(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get tokens discovered in the last N hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            tokens = self.session.query(NewToken).filter(
                NewToken.timestamp >= cutoff_time
            ).all()
            
            return [{
                'symbol': t.symbol,
                'name': t.name,
                'initial_price': t.initial_price,
                'initial_market_cap': t.initial_market_cap,
                'chain': t.chain,
                'source': t.source,
                'timestamp': t.timestamp,
                'website': t.website,
                'social_links': t.social_links
            } for t in tokens]
        except Exception as e:
            logger.error(f"Error getting recent tokens: {str(e)}")
            return []

    def get_high_opportunity_tokens(self, min_score: float = 0.7) -> List[Dict[str, Any]]:
        """Get tokens with high opportunity scores"""
        try:
            analyses = self.session.query(TokenAnalysis).filter(
                TokenAnalysis.opportunity_score >= min_score
            ).order_by(TokenAnalysis.opportunity_score.desc()).all()
            
            return [{
                'symbol': a.symbol,
                'opportunity_score': a.opportunity_score,
                'initial_momentum': a.initial_momentum,
                'social_score': a.social_score,
                'risk_score': a.risk_score,
                'timestamp': a.timestamp
            } for a in analyses]
        except Exception as e:
            logger.error(f"Error getting high opportunity tokens: {str(e)}")
            return []

    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alerts from the last N hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            alerts = self.session.query(Alert).filter(
                Alert.timestamp >= cutoff_time
            ).order_by(Alert.timestamp.desc()).all()
            
            return [{
                'symbol': a.symbol,
                'name': a.name,
                'opportunity_score': a.opportunity_score,
                'momentum_score': a.momentum_score,
                'social_score': a.social_score,
                'risk_score': a.risk_score,
                'alert_message': a.alert_message,
                'timestamp': a.timestamp
            } for a in alerts]
        except Exception as e:
            logger.error(f"Error getting recent alerts: {str(e)}")
            return []

    def _calculate_avg_trade_duration(self, df: pd.DataFrame) -> float:
        """Calculate average trade duration in hours"""
        try:
            if 'position_id' not in df.columns:
                return 0.0

            # Group by position_id and calculate duration
            positions = df.groupby('position_id')
            durations = []

            for _, position in positions:
                if len(position) >= 2:
                    duration = (position.index.max() - position.index.min()).total_seconds() / 3600
                    durations.append(duration)

            return float(np.mean(durations)) if durations else 0.0
        except Exception as e:
            logger.error(f"Error calculating average trade duration: {str(e)}")
            return 0.0

    def _calculate_metric_trend(self, series: pd.Series) -> str:
        """Calculate trend analysis for a metric"""
        try:
            if len(series) < 2:
                return "insufficient_data"

            # Calculate rolling averages
            short_ma = series.rolling(window=5, min_periods=1).mean()
            long_ma = series.rolling(window=20, min_periods=1).mean()

            # Get latest values
            latest_short = short_ma.iloc[-1]
            latest_long = long_ma.iloc[-1]
            
            # Determine trend
            if latest_short > latest_long:
                return "upward"
            elif latest_short < latest_long:
                return "downward"
            else:
                return "sideways"
        except Exception as e:
            logger.error(f"Error calculating metric trend: {str(e)}")
            return "error"

    def _calculate_risk_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate advanced risk metrics"""
        try:
            # Convert to daily returns if pnl column exists, otherwise use realized_pnl
            pnl_column = 'pnl' if 'pnl' in df.columns else 'realized_pnl'
            daily_returns = df[pnl_column].resample('D').sum()
            
            if len(daily_returns) < 2:
                return {}
            
            # Basic metrics
            var_95 = float(np.percentile(daily_returns, 5))
            var_99 = float(np.percentile(daily_returns, 1))
            
            # Expected Shortfall (Conditional VaR)
            es_95 = float(daily_returns[daily_returns <= var_95].mean())
            es_99 = float(daily_returns[daily_returns <= var_99].mean())
            
            # Volatility (annualized)
            volatility = float(daily_returns.std() * np.sqrt(252))
            
            # Downside deviation
            downside_returns = daily_returns[daily_returns < 0]
            downside_deviation = float(np.sqrt((downside_returns ** 2).mean()))
            
            # Sortino ratio (using risk-free rate of 0 for simplicity)
            sortino = float(daily_returns.mean() / downside_deviation * np.sqrt(252)) if downside_deviation != 0 else 0
            
            # Calculate drawdown
            cumulative = (1 + daily_returns).cumprod()
            rolling_max = cumulative.expanding(min_periods=1).max()
            drawdowns = (cumulative - rolling_max) / rolling_max
            max_drawdown = float(drawdowns.min())
            
            # Calmar ratio
            calmar = float(-daily_returns.mean() * 252 / max_drawdown) if max_drawdown != 0 else 0
            
            # Omega ratio
            threshold = 0  # Can be adjusted based on target return
            omega = float(
                daily_returns[daily_returns > threshold].sum() / 
                abs(daily_returns[daily_returns <= threshold].sum())
            ) if len(daily_returns[daily_returns <= threshold]) > 0 else float('inf')
            
            # Kurtosis and Skewness
            kurtosis = float(stats.kurtosis(daily_returns))
            skewness = float(stats.skew(daily_returns))
            
            # Calculate beta if market data is available (using S&P 500 as proxy)
            beta = 0.0  # Placeholder for beta calculation
            
            # Tail risk measures
            extreme_loss_threshold = np.percentile(daily_returns, 1)
            tail_events = len(daily_returns[daily_returns <= extreme_loss_threshold])
            tail_ratio = float(tail_events / len(daily_returns))
            
            # Risk-adjusted metrics
            avg_return = float(daily_returns.mean())
            std_dev = float(daily_returns.std())
            
            # Information ratio (assuming no benchmark for simplicity)
            information_ratio = float(avg_return / std_dev * np.sqrt(252)) if std_dev != 0 else 0
            
            # Treynor ratio (using beta)
            treynor = float(avg_return / beta * np.sqrt(252)) if beta != 0 else 0
            
            # Maximum consecutive losses
            signs = np.sign(daily_returns)
            max_consecutive_losses = int(max(
                len(list(group)) 
                for key, group in itertools.groupby(signs) 
                if key == -1
            ) if len(signs) > 0 else 0)
            
            return {
                'var_95': var_95,
                'var_99': var_99,
                'expected_shortfall_95': es_95,
                'expected_shortfall_99': es_99,
                'volatility': volatility,
                'downside_deviation': downside_deviation,
                'sortino_ratio': sortino,
                'max_drawdown': max_drawdown,
                'calmar_ratio': calmar,
                'omega_ratio': omega,
                'kurtosis': kurtosis,
                'skewness': skewness,
                'beta': beta,
                'tail_ratio': tail_ratio,
                'information_ratio': information_ratio,
                'treynor_ratio': treynor,
                'max_consecutive_losses': max_consecutive_losses,
                'risk_metrics_version': '2.0'  # Version tracking for metrics calculation
            }
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}")
            return {}

    def _calculate_metric_trend(self, series: pd.Series) -> Dict[str, float]:
        """Calculate trend analysis for a metric"""
        try:
            if len(series) < 2:
                return {
                    'trend': 0.0,
                    'volatility': 0.0,
                    'current_value': float(series.iloc[-1]) if len(series) > 0 else 0.0
                }
            
            # Calculate trend using linear regression
            x = np.arange(len(series))
            slope, _, r_value, _, _ = stats.linregress(x, series)
            
            # Calculate trend volatility
            detrended = series - (slope * x + np.mean(series))
            trend_volatility = float(np.std(detrended))
            
            return {
                'trend': float(slope),
                'r_squared': float(r_value ** 2),
                'volatility': trend_volatility,
                'current_value': float(series.iloc[-1])
            }
        except Exception as e:
            logger.error(f"Error calculating metric trend: {str(e)}")
            return {
                'trend': 0.0,
                'volatility': 0.0,
                'current_value': 0.0
            }

    def _calculate_sl_tp_ratio(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate stop loss and take profit effectiveness"""
        try:
            if df.empty:
                return {
                    'sl_hit_rate': 0.0,
                    'tp_hit_rate': 0.0,
                    'risk_reward_ratio': 0.0
                }

            closed_positions = df[df['status'] == 'closed'].copy()
            if closed_positions.empty:
                return {
                    'sl_hit_rate': 0.0,
                    'tp_hit_rate': 0.0,
                    'risk_reward_ratio': 0.0
                }

            # Calculate position outcomes
            total_positions = len(closed_positions)
            sl_hits = len(closed_positions[closed_positions['exit_price'] <= closed_positions['stop_loss']])
            tp_hits = len(closed_positions[closed_positions['exit_price'] >= closed_positions['take_profit']])

            # Calculate average risk and reward
            avg_risk = (closed_positions['entry_price'] - closed_positions['stop_loss']).abs().mean()
            avg_reward = (closed_positions['take_profit'] - closed_positions['entry_price']).abs().mean()

            return {
                'sl_hit_rate': float(sl_hits / total_positions if total_positions > 0 else 0),
                'tp_hit_rate': float(tp_hits / total_positions if total_positions > 0 else 0),
                'risk_reward_ratio': float(avg_reward / avg_risk if avg_risk != 0 else 0)
            }
        except Exception as e:
            logger.error(f"Error calculating SL/TP ratio: {str(e)}")
            return {
                'sl_hit_rate': 0.0,
                'tp_hit_rate': 0.0,
                'risk_reward_ratio': 0.0
            }

    def cleanup(self):
        """Cleanup database resources"""
        try:
            self.session.close()
            logger.info("Database session closed")
        except Exception as e:
            logger.error(f"Error during database cleanup: {str(e)}")

if __name__ == "__main__":
    # Test database functionality
    try:
        db = Database()
        
        # Test adding a position
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
        
        # Test adding a trade
        if position:
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
            db.add_trade(trade_data)
        
        # Test queries
        open_positions = db.get_open_positions()
        logger.info(f"Open positions: {len(open_positions)}")
        
        trades = db.get_trades('SOL/USDT')
        logger.info(f"Recent trades: {len(trades)}")
        
        summary = db.get_performance_summary('SOL/USDT')
        logger.info(f"Performance summary: {summary}")
        
        db.cleanup()
        
    except Exception as e:
        logger.error(f"Test error: {str(e)}")
