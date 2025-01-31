@echo off
echo Starting CryptoBot and Dashboard...

:: Activate the virtual environment
call c:\Users\Jonat\CryptoBot\venv\Scripts\activate.bat

:: Start the trading bot in a new window
start "CryptoBot" python bot.py

:: Start the Streamlit dashboard in a new window
start "CryptoBot Dashboard" streamlit run app.py

echo CryptoBot and Dashboard are now running!
