import asyncio
import pandas as pd
import sys
import os
sys.path.append(os.getcwd())
from app.agents.market_data_agent import MarketDataAgent

async def debug_sr():
    agent = MarketDataAgent()
    await agent.initialize_symbols()
    ohlcv = await agent.exchange.fetch_ohlcv("BTC-USDT", "1h", limit=50)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df_calc = agent.calculate_indicators(df)
    
    print("Comparison of Low and Closest Support:")
    cols = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Closest Support', 'Closest Resistance']
    print(df_calc[cols].tail(10))
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(debug_sr())
