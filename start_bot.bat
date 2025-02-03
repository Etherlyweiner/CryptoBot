@echo off
echo Starting CryptoBot...
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python run_bot.py
pause
