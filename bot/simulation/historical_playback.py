import pandas as pd
import asyncio
from pathlib import Path

class HistoricalPriceEngine:
    def __init__(self, data_path: str):
        self.data = pd.read_parquet(Path(data_path))
        self.current_idx = 0
        
    async def stream_prices(self):
        while self.current_idx < len(self.data):
            yield self.data.iloc[self.current_idx]
            self.current_idx += 1
            await asyncio.sleep(1)
