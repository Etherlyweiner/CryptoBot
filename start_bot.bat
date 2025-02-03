@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
set PYTHONPATH=.
streamlit run app.py --server.port 8501
pause
