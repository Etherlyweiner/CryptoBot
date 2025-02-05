@echo off
echo Starting trading bot server...
cd /d "%~dp0"
"C:\Program Files\nodejs\node.exe" server.js
pause
