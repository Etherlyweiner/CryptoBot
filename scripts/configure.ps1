# CryptoBot Configuration Script
Write-Host "CryptoBot Configuration Wizard" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Write-Host ""

# Create .env file
$envPath = ".env"

# Get user input
Write-Host "Helius API Configuration:" -ForegroundColor Cyan
$primaryKey = Read-Host "Enter your Primary Helius API Key"
$backupKey = Read-Host "Enter your Backup Helius API Key"

Write-Host "`nWallet Configuration:" -ForegroundColor Cyan
$walletAddress = Read-Host "Enter your Phantom Wallet Address"

Write-Host "`nNetwork Configuration:" -ForegroundColor Cyan
$network = Read-Host "Enter network type (mainnet/devnet) [devnet]"
if ([string]::IsNullOrWhiteSpace($network)) {
    $network = "devnet"
}

# Create .env content
$envContent = @"
# Helius API Configuration
HELIUS_PRIMARY_API_KEY=$primaryKey
HELIUS_BACKUP_API_KEY=$backupKey

# Network Configuration
SOLANA_NETWORK=$network
RPC_TIMEOUT_MS=30000

# Wallet Configuration
PHANTOM_WALLET_ADDRESS=$walletAddress

# Trading Parameters
MAX_TRADE_SIZE_SOL=0.1
RISK_LEVEL=medium

# Security Settings
ENABLE_2FA=true
API_REQUEST_TIMEOUT=45000

# Monitoring
ENABLE_PERFORMANCE_METRICS=true
LOG_LEVEL=info

# WebSocket Settings
USE_WEBSOCKET=true
WEBSOCKET_RECONNECT_DELAY=1000
"@

# Save to .env file
$envContent | Out-File -FilePath $envPath -Encoding UTF8

Write-Host "`nConfiguration saved successfully!" -ForegroundColor Green
Write-Host "Next step: Run 'python scripts/validate_config.py' to test the configuration." -ForegroundColor Yellow
