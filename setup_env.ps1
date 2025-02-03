# PowerShell script to set environment variables
Write-Host "Setting up CryptoBot environment variables..." -ForegroundColor Green

# Function to prompt for secure input
function Get-SecureInput {
    param (
        [string]$prompt,
        [string]$defaultValue = ""
    )
    $input = Read-Host -Prompt $prompt
    if ([string]::IsNullOrWhiteSpace($input)) {
        return $defaultValue
    }
    return $input
}

# Get variables from user
$heliusKey = Get-SecureInput -prompt "Enter your Helius API key"
$walletAddress = Get-SecureInput -prompt "Enter your wallet address"
$network = Get-SecureInput -prompt "Enter network (press Enter for mainnet-beta)" -defaultValue "mainnet-beta"
$rpcUrl = Get-SecureInput -prompt "Enter RPC URL (press Enter for default)" -defaultValue "https://rpc.helius.xyz/?api-key=$heliusKey"

# Set environment variables for current session
$env:HELIUS_API_KEY = $heliusKey
$env:WALLET_ADDRESS = $walletAddress
$env:NETWORK = $network
$env:RPC_URL = $rpcUrl

# Create or update .env file
$envContent = @"
HELIUS_API_KEY=$heliusKey
WALLET_ADDRESS=$walletAddress
NETWORK=$network
RPC_URL=$rpcUrl
"@

# Save to .env file
$envContent | Out-File -FilePath ".env" -Encoding UTF8 -Force

# Create a backup of the environment variables
$backupDate = Get-Date -Format "yyyy-MM-dd"
Copy-Item ".env" ".env.backup.$backupDate" -Force

Write-Host "`nEnvironment variables set successfully!" -ForegroundColor Green
Write-Host "A backup has been created as .env.backup.$backupDate" -ForegroundColor Yellow

# Display current settings (masked for security)
Write-Host "`nCurrent Settings:" -ForegroundColor Cyan
Write-Host "HELIUS_API_KEY: " -NoNewline
Write-Host $heliusKey.Substring(0,4) -NoNewline -ForegroundColor Yellow
Write-Host "..." -ForegroundColor Yellow
Write-Host "WALLET_ADDRESS: " -NoNewline
Write-Host $walletAddress.Substring(0,4) -NoNewline -ForegroundColor Yellow
Write-Host "..." -ForegroundColor Yellow
Write-Host "NETWORK: $network" -ForegroundColor Yellow
Write-Host "RPC_URL: " -NoNewline
Write-Host $rpcUrl.Substring(0,20) -NoNewline -ForegroundColor Yellow
Write-Host "..." -ForegroundColor Yellow

# Optional: Set system-wide environment variables (requires admin privileges)
$setSystemWide = Get-SecureInput -prompt "`nWould you like to set these as system-wide environment variables? (y/N)"
if ($setSystemWide -eq "y") {
    try {
        [System.Environment]::SetEnvironmentVariable("HELIUS_API_KEY", $heliusKey, [System.EnvironmentVariableTarget]::User)
        [System.Environment]::SetEnvironmentVariable("WALLET_ADDRESS", $walletAddress, [System.EnvironmentVariableTarget]::User)
        [System.Environment]::SetEnvironmentVariable("NETWORK", $network, [System.EnvironmentVariableTarget]::User)
        [System.Environment]::SetEnvironmentVariable("RPC_URL", $rpcUrl, [System.EnvironmentVariableTarget]::User)
        Write-Host "System-wide environment variables set successfully!" -ForegroundColor Green
    }
    catch {
        Write-Host "Error setting system-wide variables. Try running as administrator." -ForegroundColor Red
    }
}

Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
