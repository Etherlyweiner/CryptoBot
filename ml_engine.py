"""
Machine Learning Engine for CryptoBot with adaptive learning capabilities
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import logging
from logging_config import get_logger

logger = get_logger('MLEngine')

class MLEngine:
    def __init__(self, bot):
        """Initialize ML Engine"""
        try:
            self.bot = bot
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.scaler = StandardScaler()
            self.is_trained = False
            logger.info("MLEngine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MLEngine: {str(e)}", exc_info=True)
            raise

    def prepare_features(self, df: pd.DataFrame) -> tuple:
        """Prepare features for prediction"""
        try:
            # Create features from technical indicators
            features = pd.DataFrame()
            
            # Price-based features
            features['price_sma20'] = df['close'] / df['sma_20'] - 1
            features['price_sma50'] = df['close'] / df['sma_50'] - 1
            features['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Technical indicators
            features['rsi'] = df['rsi']
            features['macd'] = df['macd']
            
            # Volume features
            features['volume_sma'] = df['volume'].rolling(window=20).mean()
            features['volume_std'] = df['volume'].rolling(window=20).std()
            
            # Create labels (1 for price increase, 0 for decrease)
            labels = (df['close'].shift(-1) > df['close']).astype(int)
            
            # Drop NaN values
            features = features.dropna()
            labels = labels[features.index]
            
            return features, labels
            
        except Exception as e:
            logger.error(f"Error preparing features: {str(e)}", exc_info=True)
            return None, None

    def train_model(self, symbol: str) -> bool:
        """Train the ML model"""
        try:
            # Get technical indicators
            df = self.bot.get_technical_indicators(symbol)
            if df is None or df.empty:
                logger.error("No data available for training")
                return False
            
            # Prepare features and labels
            features, labels = self.prepare_features(df)
            if features is None or labels is None:
                return False
            
            # Scale features
            scaled_features = self.scaler.fit_transform(features)
            
            # Train model
            self.model.fit(scaled_features, labels)
            self.is_trained = True
            
            logger.info("Model trained successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}", exc_info=True)
            return False

    def get_predictions(self, symbol: str) -> dict:
        """Get predictions for a symbol"""
        try:
            # Get latest data
            df = self.bot.get_technical_indicators(symbol)
            if df is None or df.empty:
                logger.error("No data available for prediction")
                return None
            
            # Prepare features
            features, _ = self.prepare_features(df)
            if features is None:
                return None
            
            # Scale features
            scaled_features = self.scaler.transform(features)
            
            # Make predictions
            if not self.is_trained:
                if not self.train_model(symbol):
                    return None
            
            probabilities = self.model.predict_proba(scaled_features)
            predictions = self.model.predict(scaled_features)
            
            # Calculate confidence metrics
            avg_probability = probabilities[-1][1]  # Probability of price increase
            prediction = predictions[-1]  # Latest prediction
            
            # Get feature importance
            feature_importance = dict(zip(
                features.columns,
                self.model.feature_importances_
            ))
            
            return {
                'prediction': 'bullish' if prediction == 1 else 'bearish',
                'confidence': avg_probability,
                'feature_importance': feature_importance,
                'timestamp': df.index[-1]
            }
            
        except Exception as e:
            logger.error(f"Error making predictions: {str(e)}", exc_info=True)
            return None
