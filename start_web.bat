@echo off
echo Starting CryptoBot Web Interface...
cd /d %~dp0
call venv\Scripts\activate.bat
streamlit run app.py --server.port 8502
pause
