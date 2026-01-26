import asyncio
import pandas as pd
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
from app.agents.analyst_agent import AnalystAgent

async def main():
    md = MarketDataAgent()
    analyst = AnalystAgent()
    
    symbol = "BTC-USDT"
    
    try:
        # Fetch 4H and 1H for top-down
        h4_ohlcv = await md.exchange.fetch_ohlcv(symbol, "4h", limit=100)
        h1_ohlcv = await md.exchange.fetch_ohlcv(symbol, "1h", limit=100)
    except Exception as e:
        print(f"Error fetching data: {e}")
        await md.stop()
        return

    df4 = md.calculate_indicators(pd.DataFrame(h4_ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']))
    df1 = md.calculate_indicators(pd.DataFrame(h1_ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']))
    
    combined_context = "### 4H Context\n" + analyst.format_market_context(df4, window=20)
    combined_context += "\n\n### 1H Context\n" + analyst.format_market_context(df1, window=20)
    
    input_data = {
        "symbol": symbol,
        "market_context": combined_context,
        "analysis_summary": {
            "overall_regime": "BULLISH",
            "timeframe_data": {
                "4h": {"regime": "BULLISH", "ema_signal": "BUY"},
                "1h": {"regime": "BULLISH", "ema_signal": "BUY", "sfp_signal": "HOLD"}
            }
        }
    }
    
    print("Calling LLM for Top-Down Analyst...")
    try:
        res = await analyst.analyst_chain.ainvoke(input_data)
        print(f"Agent Output: {res.get('primary_bias')}")
    except Exception as e:
        print(f"LLM Error: {e}")
        res = {"primary_bias": "ERROR", "summary": str(e), "top_setups": []}
    
    fig = make_subplots(rows=2, cols=1, row_heights=[0.6, 0.4], specs=[[{"type": "xy"}], [{"type": "table"}]])
    df1['dt'] = pd.to_datetime(df1['timestamp'], unit='ms')
    fig.add_trace(go.Candlestick(x=df1['dt'], open=df1['Open'], high=df1['High'], low=df1['Low'], close=df1['Close'], name='1H Chart'), row=1, col=1)
    
    setups_list = res.get('top_setups', [])
    setups = setups_list[0] if setups_list else {}
    table_data = [
        ["Bias", "Summary", "Top Setup Strategy", "Setup Reasoning"],
        [res.get('primary_bias'), str(res.get('summary', ''))[:100], setups.get('strategy', 'N/A'), str(setups.get('reasoning', 'N/A'))[:150]]
    ]
    fig.add_trace(go.Table(header=dict(values=table_data[0]), cells=dict(values=table_data[1:])), row=2, col=1)
    
    fig.update_layout(title='Analyst Agent Visual Verification', template='plotly_dark', height=1000)
    fig.write_html("tests/analyst_verify.html")
    print("Saved to tests/analyst_verify.html")
    await md.stop()

if __name__ == "__main__":
    asyncio.run(main())
