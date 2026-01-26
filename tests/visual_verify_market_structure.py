import asyncio
import pandas as pd
import json
import os
import sys

# Add app to path
sys.path.append(os.getcwd())

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    sys.exit(1)

from app.agents.market_data_agent import MarketDataAgent
from app.agents.market_structure_agent import MarketStructureAgent

async def main():
    md = MarketDataAgent()
    ms = MarketStructureAgent()
    
    symbol = "BTC-USDT"
    timeframe = "1h"
    
    try:
        ohlcv = await md.exchange.fetch_ohlcv(symbol, timeframe, limit=300)
    except Exception as e:
        print(f"Error fetching data: {e}")
        await md.stop()
        return

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df_calc = md.calculate_indicators(df)
    
    ema_cols = [f'Exponential Moving Average {l}' for l in [9, 21, 55, 144, 252]]
    
    # Prepare input for structure LLM
    input_data = {
        "symbol": symbol,
        "timeframe": timeframe,
        "market_context": ms.format_market_context(df_calc, window=50, columns=['Open', 'High', 'Low', 'Close'] + ema_cols),
        "analysis_summary": {
            "highs_state": "HIGHER", "lows_state": "HIGHER", "pivot_state": "UP", "va_state": "ASCENDING"
        }
    }
    
    print("Calling LLM for Market Structure...")
    try:
        res = await ms.ema_chain.ainvoke(input_data)
        print(f"Agent Output: {res.get('performance')}")
    except Exception as e:
        print(f"LLM Error: {e}")
        res = {"performance": "ERROR", "reasoning": str(e)}
    
    fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], specs=[[{"type": "xy"}], [{"type": "table"}]])
    df_calc['dt'] = pd.to_datetime(df_calc['timestamp'], unit='ms')
    fig.add_trace(go.Candlestick(x=df_calc['dt'], open=df_calc['Open'], high=df_calc['High'], low=df_calc['Low'], close=df_calc['Close']), row=1, col=1)
    
    # Plot 5 EMAs
    for l in [9, 21, 55, 144, 252]:
        fig.add_trace(go.Scatter(x=df_calc['dt'], y=df_calc[f'Exponential Moving Average {l}'], name=f'EMA {l}', line=dict(width=1)), row=1, col=1)

    table_data = [
        ["Order", "Fanning", "Performance", "Reasoning"],
        [res.get('emas_in_order'), res.get('emas_fanning'), res.get('performance'), res.get('reasoning')]
    ]
    fig.add_trace(go.Table(header=dict(values=table_data[0]), cells=dict(values=table_data[1:])), row=2, col=1)
    
    fig.update_layout(title='Market Structure Visual Verification', template='plotly_dark', height=1000)
    fig.write_html("tests/ms_verify.html")
    print("Saved to tests/ms_verify.html")
    await md.stop()

if __name__ == "__main__":
    asyncio.run(main())
