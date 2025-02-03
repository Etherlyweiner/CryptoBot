@echo off
echo Setting up CryptoBot Environment Variables
echo =======================================

set /p HELIUS_KEY=Enter your Helius API key: 
set /p WALLET=Enter your wallet address: 

:: Set the environment variables
setx HELIUS_API_KEY "%HELIUS_KEY%"
setx WALLET_ADDRESS "%WALLET%"
setx NETWORK "mainnet-beta"
setx RPC_URL "https://rpc.helius.xyz/?api-key=%HELIUS_KEY%"

:: Also set for current session
set HELIUS_API_KEY=%HELIUS_KEY%
set WALLET_ADDRESS=%WALLET%
set NETWORK=mainnet-beta
set RPC_URL=https://rpc.helius.xyz/?api-key=%HELIUS_KEY%

echo.
echo Environment variables set successfully!
echo.
echo Current Settings:
echo ----------------
echo HELIUS_API_KEY: %HELIUS_KEY:~0,4%...
echo WALLET_ADDRESS: %WALLET:~0,4%...
echo NETWORK: mainnet-beta
echo RPC_URL: https://rpc.helius.xyz/?api-key=%HELIUS_KEY:~0,4%...
echo.
echo Press any key to exit...
pause
