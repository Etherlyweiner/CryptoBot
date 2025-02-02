"""Test all required imports"""
import sys
print(f"Python version: {sys.version}")

try:
    import pandas as pd
    print("[OK] pandas")
    import numpy as np
    print("[OK] numpy")
    import streamlit as st
    print("[OK] streamlit")
    import plotly.graph_objects as go
    print("[OK] plotly")
    import ccxt
    print("[OK] ccxt")
    from binance.client import Client
    print("[OK] python-binance")
    import ta
    print("[OK] ta")
    import sqlalchemy
    print("[OK] sqlalchemy")
    import alembic
    print("[OK] alembic")
    from dotenv import load_dotenv
    print("[OK] python-dotenv")
    print("\nAll imports successful!")
except ImportError as e:
    print(f"\n[ERROR] Import error: {str(e)}")
