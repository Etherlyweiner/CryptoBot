"""
Machine learning engine for trade prediction and optimization.
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
from pathlib import Path
import json
from dataclasses import dataclass
from prometheus_client import Gauge, Counter

logger = logging.getLogger(__name__)

# Prometheus metrics
MODEL_ACCURACY = Gauge('ml_model_accuracy', 'Current model accuracy')
PREDICTION_COUNT = Counter('ml_predictions_total', 'Total number of predictions made')
TRAINING_COUNT = Counter('ml_training_runs_total', 'Total number of training runs')

@dataclass
class ModelMetrics:
    """Metrics for model performance evaluation."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    timestamp: datetime

class MLEngine:
    """Machine learning engine for trade prediction and optimization."""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        # Initialize models
        self.classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.regressor = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        self.scaler = StandardScaler()
        self.feature_columns = [
            'price', 'volume', 'market_cap', 'volatility',
            'rsi', 'macd', 'bollinger_upper', 'bollinger_lower'
        ]
        
        # Load latest models if available
        self.load_latest_models()

    def preprocess_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess data for training or prediction."""
        # Ensure all required features are present
        missing_cols = set(self.feature_columns) - set(data.columns)
        if missing_cols:
            raise ValueError(f"Missing required features: {missing_cols}")
            
        # Handle missing values
        data = data.copy()
        data[self.feature_columns] = data[self.feature_columns].fillna(method='ffill')
        
        # Add technical indicators
        data = self.add_technical_indicators(data)
        
        # Scale features
        X = self.scaler.fit_transform(data[self.feature_columns])
        y = data['target'].values if 'target' in data.columns else None
        
        return X, y

    def add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the dataset."""
        # RSI
        delta = data['price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = data['price'].ewm(span=12, adjust=False).mean()
        exp2 = data['price'].ewm(span=26, adjust=False).mean()
        data['macd'] = exp1 - exp2
        
        # Bollinger Bands
        sma = data['price'].rolling(window=20).mean()
        std = data['price'].rolling(window=20).std()
        data['bollinger_upper'] = sma + (std * 2)
        data['bollinger_lower'] = sma - (std * 2)
        
        return data

    def train(self, data: pd.DataFrame, hyperparameter_tune: bool = True) -> ModelMetrics:
        """Train the ML models with optional hyperparameter tuning."""
        try:
            TRAINING_COUNT.inc()
            
            # Preprocess data
            X, y = self.preprocess_data(data)
            
            if hyperparameter_tune:
                # Hyperparameter tuning for classifier
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [5, 10, 15],
                    'min_samples_split': [2, 5, 10]
                }
                
                tscv = TimeSeriesSplit(n_splits=5)
                grid_search = GridSearchCV(
                    self.classifier,
                    param_grid,
                    cv=tscv,
                    scoring='f1',
                    n_jobs=-1
                )
                
                grid_search.fit(X, y)
                self.classifier = grid_search.best_estimator_
                logger.info(f"Best parameters: {grid_search.best_params_}")
            else:
                self.classifier.fit(X, y)
            
            # Evaluate model
            y_pred = self.classifier.predict(X)
            metrics = ModelMetrics(
                accuracy=accuracy_score(y, y_pred),
                precision=precision_score(y, y_pred),
                recall=recall_score(y, y_pred),
                f1_score=f1_score(y, y_pred),
                timestamp=datetime.utcnow()
            )
            
            # Update Prometheus metrics
            MODEL_ACCURACY.set(metrics.accuracy)
            
            # Save models
            self.save_models()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error training models: {str(e)}")
            raise

    def predict(self, features: Dict[str, float]) -> Tuple[bool, float, Dict[str, float]]:
        """
        Make predictions for a trade.
        
        Returns:
            Tuple containing:
            - Boolean indicating if trade should be executed
            - Confidence score
            - Dictionary of feature importances
        """
        try:
            PREDICTION_COUNT.inc()
            
            # Convert features to DataFrame
            df = pd.DataFrame([features])
            
            # Preprocess
            X, _ = self.preprocess_data(df)
            
            # Make predictions
            trade_decision = self.classifier.predict(X)[0]
            confidence = np.max(self.classifier.predict_proba(X)[0])
            
            # Get feature importances
            importances = dict(zip(
                self.feature_columns,
                self.classifier.feature_importances_
            ))
            
            return trade_decision, confidence, importances
            
        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}")
            raise

    def save_models(self):
        """Save models and scaler to disk."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Save classifier
        classifier_path = self.model_dir / f"classifier_{timestamp}.joblib"
        joblib.dump(self.classifier, classifier_path)
        
        # Save scaler
        scaler_path = self.model_dir / f"scaler_{timestamp}.joblib"
        joblib.dump(self.scaler, scaler_path)
        
        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "feature_columns": self.feature_columns,
            "classifier_path": str(classifier_path),
            "scaler_path": str(scaler_path)
        }
        
        with open(self.model_dir / "model_metadata.json", "w") as f:
            json.dump(metadata, f)

    def load_latest_models(self):
        """Load the latest saved models."""
        try:
            metadata_path = self.model_dir / "model_metadata.json"
            if not metadata_path.exists():
                logger.info("No saved models found")
                return
                
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            
            # Load classifier and scaler
            self.classifier = joblib.load(metadata["classifier_path"])
            self.scaler = joblib.load(metadata["scaler_path"])
            self.feature_columns = metadata["feature_columns"]
            
            logger.info("Loaded latest models successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            raise

    def validate_features(self, features: Dict[str, float]) -> bool:
        """Validate that all required features are present."""
        return all(feature in features for feature in self.feature_columns)
