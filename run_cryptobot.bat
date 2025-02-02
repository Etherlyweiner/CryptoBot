@echo off
echo Starting CryptoBot...
call .\venv_py310\Scripts\activate.bat
python start_app.py
if errorlevel 1 (
    echo Error starting CryptoBot. Please check the logs.
    pause
    exit /b 1
)
