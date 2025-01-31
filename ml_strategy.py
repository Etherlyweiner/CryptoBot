import numpy as np
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import pandas as pd
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import os
import json
import logging
import torch

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLStrategy:
    def __init__(self):
        self.model = self._create_model()
        self.scaler = StandardScaler()
        self.strategy_cache_file = "learned_strategies.json"
        self.learned_strategies = self._load_strategies()
        
        # Initialize sentiment analysis with better error handling
        try:
            # Check if CUDA is available and set the device accordingly
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Use a specific model for sentiment analysis
            model_name = "distilbert-base-uncased-finetuned-sst-2-english"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.sentiment_model.to(self.device)
            
            # Initialize the pipeline with the specific model and tokenizer
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model=self.sentiment_model,
                tokenizer=self.tokenizer,
                device=self.device if self.device == "cuda" else -1
            )
            logger.info("Sentiment analysis model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading sentiment analysis model: {str(e)}")
            self.sentiment_analyzer = None

    def _create_model(self):
        try:
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(30, 6)),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(1, activation='sigmoid')
            ])
            model.compile(optimizer=Adam(learning_rate=0.001),
                         loss='binary_crossentropy',
                         metrics=['accuracy'])
            return model
        except Exception as e:
            logger.error(f"Error creating model: {str(e)}")
            return None

    def _load_strategies(self):
        try:
            if os.path.exists(self.strategy_cache_file):
                with open(self.strategy_cache_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading strategies: {str(e)}")
            return []

    def _save_strategies(self):
        try:
            with open(self.strategy_cache_file, 'w') as f:
                json.dump(self.learned_strategies, f)
        except Exception as e:
            logger.error(f"Error saving strategies: {str(e)}")

    def prepare_data(self, df):
        try:
            features = ['close', 'volume', 'RSI', 'MACD', 'BB_upper', 'BB_lower']
            X = df[features].values
            X = self.scaler.fit_transform(X)
            X = np.array([X[i-30:i] for i in range(30, len(X))])
            y = np.where(df['close'].pct_change(periods=1).shift(-1).iloc[29:-1] > 0, 1, 0)
            return X, y
        except Exception as e:
            logger.error(f"Error preparing data: {str(e)}")
            return None, None

    def analyze_sentiment(self, text):
        try:
            if self.sentiment_analyzer is None:
                return {"label": "NEUTRAL", "score": 0.5}
            result = self.sentiment_analyzer(text)[0]
            return result
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {"label": "NEUTRAL", "score": 0.5}

    async def train(self, df):
        try:
            X, y = self.prepare_data(df)
            if X is not None and y is not None and self.model is not None:
                self.model.fit(X, y, epochs=10, batch_size=32, verbose=0)
                return True
            return False
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return False

    def get_trading_signals(self, df):
        try:
            if self.model is None:
                return None
                
            X, _ = self.prepare_data(df)
            if X is None:
                return None
                
            predictions = self.model.predict(X[-1:], verbose=0)
            signal = 'buy' if predictions[0][0] > 0.5 else 'sell'
            return signal
        except Exception as e:
            logger.error(f"Error getting trading signals: {str(e)}")
            return None

    async def learn_from_youtube(self, query="crypto trading strategy"):
        """Learn new trading strategies from YouTube videos"""
        try:
            # Search for relevant videos
            videos = YouTube.search(query, limit=5)
            
            for video in videos:
                video_id = video.video_id
                
                # Get video transcript
                try:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id)
                    text = " ".join([t['text'] for t in transcript])
                    
                    # Analyze sentiment and content
                    sentiment = self.analyze_sentiment(text[:512])
                    
                    # Only learn from positive/neutral content
                    if sentiment['label'] == 'POSITIVE' or (
                        sentiment['label'] == 'NEUTRAL' and sentiment['score'] > 0.6
                    ):
                        strategy = {
                            'video_id': video_id,
                            'title': video.title,
                            'sentiment': sentiment,
                            'transcript_summary': text[:1000]
                        }
                        
                        # Store unique strategies
                        if strategy not in self.learned_strategies:
                            self.learned_strategies.append(strategy)
                            self._save_strategies()
                            
                except Exception as e:
                    logger.error(f"Error processing video {video_id}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error learning from YouTube: {str(e)}")
