@echo off
echo Installing Node.js dependencies...
cd /d "%~dp0"
"C:\Program Files\nodejs\npm.cmd" install express ws express-rate-limit
if %ERRORLEVEL% neq 0 (
    echo Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully
echo Starting server...
"C:\Program Files\nodejs\node.exe" "%~dp0server.js"
pause
