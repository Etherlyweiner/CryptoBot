import csv
import json
import logging
from typing import List, Dict
from datetime import datetime
import os
import pandas as pd

logger = logging.getLogger(__name__)

class DataExporter:
    def __init__(self, output_dir: str = "data"):
        self.output_dir = output_dir
        self._ensure_output_dir()
        
    def _ensure_output_dir(self):
        """Ensure output directory exists"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
    def export_tokens_to_csv(self, tokens: List[Dict], filename: str = None):
        """Export token data to CSV file"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"new_tokens_{timestamp}.csv"
                
            filepath = os.path.join(self.output_dir, filename)
            
            # Flatten nested dictionaries
            flattened_tokens = []
            for token in tokens:
                flat_token = {}
                self._flatten_dict(token, flat_token)
                flattened_tokens.append(flat_token)
                
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(flattened_tokens)
            
            # Sort by launch date and risk score
            if 'launch_date' in df.columns:
                df['launch_date'] = pd.to_datetime(df['launch_date'])
                df = df.sort_values(['launch_date', 'initial_analysis_risk_score'], 
                                  ascending=[False, False])
                
            # Export to CSV
            df.to_csv(filepath, index=False)
            logger.info(f"Exported {len(tokens)} tokens to {filepath}")
            
            # Generate summary
            self._generate_summary(df, filepath)
            
        except Exception as e:
            logger.error(f"Error exporting tokens to CSV: {str(e)}")
            
    def _flatten_dict(self, d: Dict, flat_dict: Dict, prefix: str = ''):
        """Flatten nested dictionary structure"""
        for k, v in d.items():
            key = f"{prefix}{k}" if prefix else k
            
            if isinstance(v, dict):
                self._flatten_dict(v, flat_dict, f"{key}_")
            else:
                flat_dict[key] = v
                
    def _generate_summary(self, df: pd.DataFrame, filepath: str):
        """Generate summary statistics"""
        try:
            summary_path = filepath.replace('.csv', '_summary.txt')
            
            with open(summary_path, 'w') as f:
                f.write("Token Analysis Summary\n")
                f.write("===================\n\n")
                
                f.write(f"Total Tokens Analyzed: {len(df)}\n")
                
                if 'market_cap' in df.columns:
                    f.write(f"\nMarket Cap Statistics:\n")
                    f.write(f"Average: ${df['market_cap'].mean():,.2f}\n")
                    f.write(f"Median: ${df['market_cap'].median():,.2f}\n")
                    f.write(f"Max: ${df['market_cap'].max():,.2f}\n")
                    
                if 'liquidity' in df.columns:
                    f.write(f"\nLiquidity Statistics:\n")
                    f.write(f"Average: ${df['liquidity'].mean():,.2f}\n")
                    f.write(f"Median: ${df['liquidity'].median():,.2f}\n")
                    
                if 'initial_analysis_holder_count' in df.columns:
                    f.write(f"\nHolder Statistics:\n")
                    f.write(f"Average Holders: {df['initial_analysis_holder_count'].mean():,.0f}\n")
                    f.write(f"Median Holders: {df['initial_analysis_holder_count'].median():,.0f}\n")
                    
                if 'initial_analysis_risk_score' in df.columns:
                    f.write(f"\nRisk Score Distribution:\n")
                    risk_dist = df['initial_analysis_risk_score'].value_counts(bins=5)
                    for idx, count in enumerate(risk_dist):
                        f.write(f"Score {idx*0.2:.1f}-{(idx+1)*0.2:.1f}: {count} tokens\n")
                        
                logger.info(f"Generated summary at {summary_path}")
                
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            
    def export_trades_to_csv(self, trades: List[Dict], filename: str = None):
        """Export trade history to CSV file"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"trades_{timestamp}.csv"
                
            filepath = os.path.join(self.output_dir, filename)
            
            # Convert to DataFrame
            df = pd.DataFrame(trades)
            
            # Sort by timestamp
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp', ascending=False)
                
            # Export to CSV
            df.to_csv(filepath, index=False)
            logger.info(f"Exported {len(trades)} trades to {filepath}")
            
            # Generate trade summary
            self._generate_trade_summary(df, filepath)
            
        except Exception as e:
            logger.error(f"Error exporting trades to CSV: {str(e)}")
            
    def _generate_trade_summary(self, df: pd.DataFrame, filepath: str):
        """Generate trade summary statistics"""
        try:
            summary_path = filepath.replace('.csv', '_summary.txt')
            
            with open(summary_path, 'w') as f:
                f.write("Trade Analysis Summary\n")
                f.write("====================\n\n")
                
                f.write(f"Total Trades: {len(df)}\n")
                
                if 'profit_loss' in df.columns:
                    total_pnl = df['profit_loss'].sum()
                    win_rate = (df['profit_loss'] > 0).mean() * 100
                    
                    f.write(f"\nPerformance Metrics:\n")
                    f.write(f"Total P&L: {total_pnl:,.4f} SOL\n")
                    f.write(f"Win Rate: {win_rate:.1f}%\n")
                    
                    if len(df) > 0:
                        f.write(f"Average Trade P&L: {df['profit_loss'].mean():,.4f} SOL\n")
                        f.write(f"Best Trade: {df['profit_loss'].max():,.4f} SOL\n")
                        f.write(f"Worst Trade: {df['profit_loss'].min():,.4f} SOL\n")
                        
                if 'size' in df.columns:
                    f.write(f"\nSize Statistics:\n")
                    f.write(f"Average Size: {df['size'].mean():,.4f} SOL\n")
                    f.write(f"Total Volume: {df['size'].sum():,.4f} SOL\n")
                    
                logger.info(f"Generated trade summary at {summary_path}")
                
        except Exception as e:
            logger.error(f"Error generating trade summary: {str(e)}")
            
