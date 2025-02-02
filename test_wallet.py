"""Test Phantom wallet connection and balance."""

import asyncio
import logging
from decimal import Decimal
import os
from dotenv import load_dotenv

from exchanges.solana import SolanaExchange
from exchanges.jupiter import JupiterDEX

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_wallet():
    """Test wallet connection and balance."""
    try:
        print("\n=== Phantom Wallet Connection Test ===")
        
        # Initialize exchange
        exchange = SolanaExchange({
            'rpc_url': os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        })
        
        # Initialize Jupiter DEX
        dex = JupiterDEX({
            'rpc_url': os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        })
        
        print("\n1. Connecting to Phantom wallet...")
        await exchange.connect()
        print("✓ Connected successfully!")
        
        print("\n2. Checking SOL balance...")
        balance = await exchange.get_balance('SOL')
        sol_balance = balance['SOL']['free']
        print(f"✓ SOL Balance: {sol_balance} SOL")
        
        # Check if balance is sufficient
        min_balance = Decimal('0.1')  # Minimum 0.1 SOL recommended
        if sol_balance < min_balance:
            print(f"⚠ Warning: Low SOL balance. Recommended minimum: {min_balance} SOL")
        else:
            print("✓ Balance is sufficient for trading")
            
        print("\n3. Testing Jupiter DEX connection...")
        tokens = await dex.get_token_list()
        print(f"✓ Connected to Jupiter DEX. {len(tokens)} tokens available")
        
        # Test getting a quote
        print("\n4. Testing price quote...")
        test_amount = int(Decimal('0.1') * 1e9)  # 0.1 SOL in lamports
        route = await dex.get_price(
            'So11111111111111111111111111111111111111112',  # Wrapped SOL
            'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',  # BONK
            test_amount
        )
        
        if route:
            print("✓ Successfully got price quote from Jupiter")
            print(f"  - Price impact: {route.price_impact_pct:.2f}%")
            print(f"  - Slippage: {route.slippage_bps/100:.2f}%")
        else:
            print("⚠ Failed to get price quote")
            
        print("\n=== Test Summary ===")
        print("1. Wallet Connection: ✓")
        print(f"2. SOL Balance: {sol_balance} SOL")
        print("3. Jupiter DEX: ✓")
        print("4. Price Quotes: " + ("✓" if route else "✗"))
        
        if sol_balance >= min_balance and route:
            print("\n✅ All systems ready for trading!")
            print("""
Trading capabilities:
- Can trade any token listed on Jupiter DEX
- Automatic slippage protection
- Real-time price monitoring
- Stop-loss and take-profit orders
- Performance tracking
            """)
        else:
            print("\n⚠ Some issues need to be resolved before trading")
            if sol_balance < min_balance:
                print("- Add more SOL to your wallet")
            if not route:
                print("- Check Jupiter DEX connection")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("""
Common solutions:
1. Make sure Phantom wallet is installed and unlocked
2. Check your internet connection
3. Verify RPC URL in .env file
4. Try using a different RPC provider
""")
        
    finally:
        # Clean up
        await exchange.close()
        await dex.close()
        
if __name__ == '__main__':
    asyncio.run(test_wallet())
