"""Test script for token discovery using existing browser session."""

import asyncio
import yaml
import logging
import psutil
from bot.token_discovery import TokenMetrics
from bot.photon_trader import PhotonTrader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_browser_ready():
    """Check if Edge is running with remote debugging."""
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] == 'msedge.exe':
                cmdline = proc.info.get('cmdline', [])
                if any('--remote-debugging-port=9222' in arg for arg in cmdline):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

async def main():
    """Test token discovery using existing browser session."""
    trader = None
    try:
        # Check if browser is ready
        if not check_browser_ready():
            print("\nPlease start Edge with remote debugging first:")
            print("Run: python start_browser.py")
            return
            
        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            
        print("\nConnecting to existing browser session...")
        
        # Initialize trader
        trader = PhotonTrader(config)
        if not await trader.initialize(manual_auth=False):
            print("\nFailed to initialize trader. Please ensure you're logged in to Photon DEX")
            return
            
        print("\nStarting token discovery...")
        
        # Scan for opportunities
        opportunities = await trader.scan_for_opportunities()
        
        if not opportunities:
            print("\nNo trading opportunities found")
            return
            
        # Print results
        print("\nFound Trading Opportunities:")
        print("-" * 80)
        
        for token, score, reason in opportunities:
            print(f"\nToken: {token.symbol} ({token.name})")
            print(f"Address: {token.address}")
            print(f"Price: ${token.price:.4f}")
            print(f"24h Change: {token.price_change_24h:.1f}%")
            print(f"Volume: ${token.volume_24h:,.0f}")
            print(f"Liquidity: ${token.liquidity:,.0f}")
            print(f"Score: {score:.2f}")
            print(f"Reason: {reason}")
            print("-" * 40)
            
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        print(f"\nError: {str(e)}")
    finally:
        if trader:
            await trader.cleanup()
            print("\nBot resources cleaned up")
            
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
