@echo off
echo Starting CryptoBot Dashboard and Trading System...

:: Check for admin privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges
) else (
    echo Please run this script as Administrator
    echo Right-click the script and select "Run as administrator"
    pause
    exit /b 1
)

:: Start Redis if not running
sc query "Redis" | find "RUNNING" > nul
if errorlevel 1 (
    echo Starting Redis...
    net start Redis
    if errorlevel 1 (
        echo Failed to start Redis. Please ensure Redis is installed and you have admin rights.
        echo You can install Redis by running: msiexec /i redis-windows.msi
        pause
        exit /b 1
    )
    timeout /t 5
)

:: Set Node.js path
set PATH=%PATH%;C:\Program Files\nodejs

:: Start the trading bot and dashboard
cd /d "%~dp0"
echo Starting CryptoBot services...
start "CryptoBot Dashboard" /min cmd /c "python start.py"

:: Wait for server to start
echo Waiting for server to start...
timeout /t 5

:: Open dashboard in default browser
start http://localhost:8000

echo CryptoBot system started successfully!
echo Dashboard is available at: http://localhost:8000
echo.
echo Press Ctrl+C to stop all services
echo.
