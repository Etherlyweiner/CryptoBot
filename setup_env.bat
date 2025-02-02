@echo off
echo Setting up CryptoBot environment...

REM Check if Python 3.10 is installed
python -V 2>NUL | findstr /i "3.10" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo Python 3.10 is required but not found.
    echo Please install Python 3.10 from https://www.python.org/downloads/release/python-3109/
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist venv_py310 (
    echo Creating virtual environment...
    python -m venv venv_py310
)

REM Activate virtual environment and install dependencies
call venv_py310\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e .

echo Environment setup complete!
echo To activate the environment, run: venv_py310\Scripts\activate.bat
