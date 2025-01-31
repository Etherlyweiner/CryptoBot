import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM
import tensorflow as tf
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLStrategy:
    def __init__(self):
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.setup_model()
        
    def setup_model(self):
        """Initialize the LSTM model"""
        try:
            # Simple LSTM model
            self.model = Sequential([
                LSTM(50, activation='relu', input_shape=(60, 5), return_sequences=True),
                LSTM(50, activation='relu'),
                Dense(1)
            ])
            
            self.model.compile(optimizer='adam', loss='mse')
            logger.info("ML model initialized successfully")
        except Exception as e:
            logger.error(f"Error setting up ML model: {str(e)}")
            self.model = None

    def prepare_data(self, df):
        """Prepare data for ML model"""
        try:
            # Use basic features
            features = ['open', 'high', 'low', 'close', 'volume']
            
            # Ensure all required columns exist
            for feature in features:
                if feature not in df.columns:
                    raise ValueError(f"Missing required column: {feature}")
            
            # Scale the features
            scaled_data = self.scaler.fit_transform(df[features])
            
            # Create sequences
            X, y = [], []
            for i in range(60, len(scaled_data)):
                X.append(scaled_data[i-60:i])
                y.append(scaled_data[i, 3])  # Predict close price
            
            return np.array(X), np.array(y)
        except Exception as e:
            logger.error(f"Error preparing data: {str(e)}")
            return None, None

    def train(self, df):
        """Train the model on historical data"""
        try:
            if self.model is None:
                self.setup_model()
                
            X, y = self.prepare_data(df)
            if X is None or y is None:
                return False
                
            # Train the model
            self.model.fit(X, y, epochs=50, batch_size=32, verbose=0)
            logger.info("Model training completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return False

    def predict(self, df):
        """Make predictions using the trained model"""
        try:
            if self.model is None:
                logger.warning("Model not initialized")
                return None
                
            X, _ = self.prepare_data(df)
            if X is None:
                return None
                
            # Make prediction
            prediction = self.model.predict(X[-1:], verbose=0)
            
            # Inverse transform to get actual price
            dummy_array = np.zeros((1, 5))
            dummy_array[0, 3] = prediction[0, 0]
            actual_prediction = self.scaler.inverse_transform(dummy_array)[0, 3]
            
            return actual_prediction
        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}")
            return None

    def get_signal(self, df):
        """Generate trading signal based on ML prediction"""
        try:
            current_price = df['close'].iloc[-1]
            predicted_price = self.predict(df)
            
            if predicted_price is None:
                return 0
                
            # Calculate percentage change
            price_change = ((predicted_price - current_price) / current_price) * 100
            
            # Generate signal based on predicted price movement
            if price_change > 1.0:  # Predicted 1% or more increase
                return 1  # Buy signal
            elif price_change < -1.0:  # Predicted 1% or more decrease
                return -1  # Sell signal
            else:
                return 0  # Hold
                
        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            return 0  # Return neutral signal on error
