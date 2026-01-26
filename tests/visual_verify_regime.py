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
from app.agents.regime_detection_agent import RegimeDetectionAgent

async def main():
    md = MarketDataAgent()
    rd = RegimeDetectionAgent()
    
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
    
    input_data = {
        "symbol": symbol,
        "timeframe": timeframe,
        "market_context": rd.format_market_context(df_calc, window=50, columns=['Open', 'High', 'Low', 'Close', 'Volume', 'Average Directional Index', 'Relative Candles Phase']),
        "analysis_summary": {
            "adx_trending": "TRENDING", "highs": "HIGHER", "lows": "HIGHER", "emas_in_order": "ASCENDING"
        }
    }
    
    print("Calling LLM for Regime...")
    try:
        res = await rd.regime_chain.ainvoke(input_data)
        print(f"Agent Output: {res.get('regime')}")
    except Exception as e:
        print(f"LLM Error: {e}")
        res = {"regime": "ERROR", "reasoning": str(e), "confidence": 0}
    
    fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], specs=[[{"type": "xy"}], [{"type": "table"}]])
    df_calc['dt'] = pd.to_datetime(df_calc['timestamp'], unit='ms')
    fig.add_trace(go.Candlestick(x=df_calc['dt'], open=df_calc['Open'], high=df_calc['High'], low=df_calc['Low'], close=df_calc['Close']), row=1, col=1)
    
    table_data = [
        ["Regime", "Confidence", "Reasoning"],
        [res.get('regime'), res.get('confidence'), res.get('reasoning')]
    ]
    fig.add_trace(go.Table(header=dict(values=table_data[0]), cells=dict(values=table_data[1:])), row=2, col=1)
    
    fig.update_layout(title='Regime Detection Visual Verification', template='plotly_dark', height=900)
    fig.write_html("tests/regime_verify.html")
    print("Saved to tests/regime_verify.html")
    await md.stop()

if __name__ == "__main__":
    asyncio.run(main())
