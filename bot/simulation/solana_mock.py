from solders.transaction import Transaction
from solders.signature import Signature
import asyncio
import time

class MockSolanaNetwork:
    def __init__(self):
        self.accounts = {}
        self.transaction_log = []
        self.block_time = 0.5

    async def simulate_transaction(self, tx: Transaction):
        await asyncio.sleep(self.block_time)
        sig = Signature.default()
        self.transaction_log.append({
            'signature': sig,
            'transaction': tx,
            'block_time': time.time()
        })
        return sig
