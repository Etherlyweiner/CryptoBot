@echo off
echo Starting CryptoBot Services...

REM Start Redis (if using Windows Redis)
echo Starting Redis...
start /B redis-server.exe config/redis.conf

REM Start the trading bot
echo Starting Trading Bot...
start /B python run_trading_bot.py

REM Start the monitoring dashboard
echo Starting Dashboard...
start /B streamlit run streamlit_app.py

REM Start the API server
echo Starting API Server...
start /B python run_server.py

echo All services started. Check individual logs for status.
