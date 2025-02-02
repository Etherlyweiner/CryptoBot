"""Enhanced database management for CryptoBot with ML capabilities."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, 
    JSON, ForeignKey, Boolean, Text, func, and_
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
import pandas as pd
import numpy as np
from dataclasses import dataclass
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from .ml_engine import MLEngine

logger = logging.getLogger(__name__)
Base = declarative_base()

class Trade(Base):
    """Trade record with enhanced ML features."""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    token_address = Column(String(255), nullable=False)
    type = Column(String(10), nullable=False)  # buy or sell
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    gas_price = Column(Float)
    slippage = Column(Float)
    status = Column(String(20))  # pending, completed, failed
    error = Column(Text)
    
    # ML features
    market_data = Column(JSON)  # Store market indicators
    prediction_data = Column(JSON)  # Store ML predictions
    actual_outcome = Column(Boolean)  # Whether the trade was profitable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trade to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'token_address': self.token_address,
            'type': self.type,
            'amount': self.amount,
            'price': self.price,
            'gas_price': self.gas_price,
            'slippage': self.slippage,
            'status': self.status,
            'error': self.error,
            'market_data': self.market_data,
            'prediction_data': self.prediction_data,
            'actual_outcome': self.actual_outcome
        }

class MLModel(Base):
    """ML model metadata and performance tracking."""
    __tablename__ = 'ml_models'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    version = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    parameters = Column(JSON)
    performance_metrics = Column(JSON)
    is_active = Column(Boolean, default=True)
    model_path = Column(String(255))

@dataclass
class TradeMetrics:
    """Comprehensive trade metrics."""
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_profit_loss: float
    avg_profit_loss: float
    win_rate: float
    avg_slippage: float
    avg_gas: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float

class TradeDatabaseManager:
    """Enhanced database manager with ML capabilities."""
    
    def __init__(self, db_url: str = 'sqlite:///cryptobot_ml.db'):
        """Initialize database and ML components."""
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        # Initialize ML engine
        self.ml_engine = MLEngine()
        
    def log_trade(self, trade_data: Dict[str, Any]):
        """Log a trade with enhanced market data."""
        try:
            with self.get_session() as session:
                # Prepare trade record
                trade = Trade(
                    token_address=trade_data['token_address'],
                    type=trade_data['type'],
                    amount=trade_data['amount'],
                    price=trade_data['price'],
                    gas_price=trade_data.get('gas_price'),
                    slippage=trade_data.get('slippage'),
                    status=trade_data.get('status', 'pending'),
                    market_data=trade_data.get('market_data', {}),
                )
                
                # Get ML prediction if market data is available
                if trade.market_data:
                    try:
                        decision, confidence, importances = self.ml_engine.predict(trade.market_data)
                        trade.prediction_data = {
                            'decision': bool(decision),
                            'confidence': float(confidence),
                            'feature_importances': importances
                        }
                    except Exception as e:
                        logger.error(f"ML prediction failed: {str(e)}")
                        trade.prediction_data = {'error': str(e)}
                
                session.add(trade)
                session.commit()
                logger.info(f"Trade logged successfully: ID {trade.id}")
                return trade.id
                
        except Exception as e:
            logger.error(f"Error logging trade: {str(e)}")
            raise

    def get_trade_metrics(self, 
                         token_address: Optional[str] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> TradeMetrics:
        """Get comprehensive trade metrics."""
        try:
            with self.get_session() as session:
                # Build query
                query = session.query(Trade)
                if token_address:
                    query = query.filter(Trade.token_address == token_address)
                if start_date:
                    query = query.filter(Trade.timestamp >= start_date)
                if end_date:
                    query = query.filter(Trade.timestamp <= end_date)
                
                trades = query.all()
                if not trades:
                    return TradeMetrics(
                        total_trades=0,
                        successful_trades=0,
                        failed_trades=0,
                        total_profit_loss=0.0,
                        avg_profit_loss=0.0,
                        win_rate=0.0,
                        avg_slippage=0.0,
                        avg_gas=0.0,
                        volatility=0.0,
                        sharpe_ratio=0.0,
                        max_drawdown=0.0
                    )
                
                # Calculate metrics
                successful = sum(1 for t in trades if t.actual_outcome)
                failed = len(trades) - successful
                
                profit_loss = sum(t.market_data.get('profit_loss', 0) for t in trades)
                avg_profit = profit_loss / len(trades) if trades else 0
                
                prices = [t.price for t in trades]
                returns = np.diff(prices) / prices[:-1]
                volatility = float(np.std(returns)) if len(returns) > 0 else 0
                
                # Calculate Sharpe ratio (assuming risk-free rate of 0.01)
                rf_rate = 0.01
                excess_returns = np.mean(returns) - rf_rate
                sharpe = float(excess_returns / volatility) if volatility > 0 else 0
                
                # Calculate maximum drawdown
                cumulative_returns = np.cumprod(1 + returns)
                running_max = np.maximum.accumulate(cumulative_returns)
                drawdowns = (cumulative_returns - running_max) / running_max
                max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0
                
                return TradeMetrics(
                    total_trades=len(trades),
                    successful_trades=successful,
                    failed_trades=failed,
                    total_profit_loss=float(profit_loss),
                    avg_profit_loss=float(avg_profit),
                    win_rate=successful / len(trades) if trades else 0,
                    avg_slippage=float(np.mean([t.slippage for t in trades if t.slippage])),
                    avg_gas=float(np.mean([t.gas_price for t in trades if t.gas_price])),
                    volatility=volatility,
                    sharpe_ratio=sharpe,
                    max_drawdown=max_drawdown
                )
                
        except Exception as e:
            logger.error(f"Error getting trade metrics: {str(e)}")
            raise

    def train_ml_model(self):
        """Train ML model on historical trade data."""
        try:
            with self.get_session() as session:
                # Get all completed trades with market data
                trades = session.query(Trade).filter(
                    Trade.status == 'completed',
                    Trade.market_data.isnot(None),
                    Trade.actual_outcome.isnot(None)
                ).all()
                
                if not trades:
                    logger.warning("No suitable trades found for training")
                    return None
                
                # Prepare training data
                data = []
                for trade in trades:
                    trade_data = trade.market_data.copy()
                    trade_data['target'] = trade.actual_outcome
                    data.append(trade_data)
                
                df = pd.DataFrame(data)
                
                # Train model
                metrics = self.ml_engine.train(df)
                
                # Log model performance
                model = MLModel(
                    name='trade_classifier',
                    version=datetime.utcnow().strftime('%Y%m%d'),
                    parameters=self.ml_engine.classifier.get_params(),
                    performance_metrics={
                        'accuracy': metrics.accuracy,
                        'precision': metrics.precision,
                        'recall': metrics.recall,
                        'f1_score': metrics.f1_score
                    }
                )
                
                session.add(model)
                session.commit()
                
                logger.info(f"ML model trained successfully: {metrics}")
                return metrics
                
        except Exception as e:
            logger.error(f"Error training ML model: {str(e)}")
            raise

    def predict_trade_success(self, trade_features: List[float]) -> Tuple[bool, float]:
        """Predict probability of trade success."""
        try:
            decision, confidence, _ = self.ml_engine.predict(dict(zip(
                self.ml_engine.feature_columns,
                trade_features
            )))
            return decision, confidence
        except Exception as e:
            logger.error(f"Error predicting trade success: {str(e)}")
            raise

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.Session()

    def close(self):
        """Close database connection."""
        self.engine.dispose()
