# CryptoBot Simple Configuration Script
Clear-Host
Write-Host "CryptoBot Configuration Wizard" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Write-Host ""

# Function to get user input with a prompt
function Get-UserInput {
    param (
        [string]$prompt,
        [string]$default = ""
    )
    
    Write-Host $prompt -ForegroundColor Cyan -NoNewline
    $userInput = Read-Host
    if ([string]::IsNullOrWhiteSpace($userInput) -and $default) {
        return $default
    }
    return $userInput
}

# Get configuration values
$primaryKey = Get-UserInput " Enter your Primary Helius API Key: "
$backupKey = Get-UserInput " Enter your Backup Helius API Key: "
$walletAddress = Get-UserInput " Enter your Phantom Wallet Address: "
$network = Get-UserInput " Enter network type (mainnet/devnet) [devnet]: " "devnet"

# Create the environment file content
$envContent = @"
HELIUS_PRIMARY_API_KEY=$primaryKey
HELIUS_BACKUP_API_KEY=$backupKey
PHANTOM_WALLET_ADDRESS=$walletAddress
SOLANA_NETWORK=$network
RPC_TIMEOUT_MS=30000
MAX_TRADE_SIZE_SOL=0.1
RISK_LEVEL=medium
ENABLE_2FA=true
API_REQUEST_TIMEOUT=45000
ENABLE_PERFORMANCE_METRICS=true
LOG_LEVEL=info
USE_WEBSOCKET=true
WEBSOCKET_RECONNECT_DELAY=1000
"@

# Save to .env file
$envContent | Out-File -FilePath ".env" -Encoding UTF8 -NoNewline

Write-Host "`nConfiguration saved successfully!" -ForegroundColor Green
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
