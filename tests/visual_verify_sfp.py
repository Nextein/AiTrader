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
    import numpy as np
except ImportError:
    print("Plotly not found.")
    sys.exit(1)

from app.agents.market_data_agent import MarketDataAgent
from app.agents.sfp_strategy_agent import SFPStrategyAgent
from app.core.analysis import AnalysisManager

async def main():
    md_agent = MarketDataAgent()
    sfp_agent = SFPStrategyAgent()
    
    symbol = "BTC-USDT"
    timeframe = "1h"
    
    print(f"--- Visual Verification: SFP Strategy ({symbol}) ---")
    
    try:
        ohlcv = await md_agent.exchange.fetch_ohlcv(symbol, timeframe, limit=300)
    except Exception as e:
        print(f"Error fetching data: {e}")
        await md_agent.stop()
        return

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df_calc = md_agent.calculate_indicators(df)
    
    # Mock context
    analysis = await AnalysisManager.get_analysis(symbol)
    await analysis.update_section("market_data", df_calc, timeframe)
    await analysis.update_section("value_areas", {"vah": 88000, "val": 86000, "state": "RANGING"}, timeframe)
    
    input_data = {
        "symbol": symbol,
        "timeframe": timeframe,
        "market_context": sfp_agent.format_market_context(df_calc, window=30),
        "analysis_summary": {
            "vah": 88000, "val": 86000, "va_state": "RANGING",
            "regime": "RANGING", "market_structure": {"highs": "NEUTRAL"}
        }
    }
    
    print("Calling LLM...")
    try:
        res = await sfp_agent.analysis_chain.ainvoke(input_data)
        print(f"Agent Output: {res.get('signal')}")
    except Exception as e:
        print(f"LLM Error: {e}")
        res = {"signal": "ERROR", "conclusion": str(e), "confidence": 0}
    
    # Visualization
    fig = make_subplots(rows=2, cols=1, subplot_titles=('Price & Volume', 'Agent Decision'),
                        row_heights=[0.7, 0.3], specs=[[{"type": "xy"}], [{"type": "table"}]])
    
    df_calc['dt'] = pd.to_datetime(df_calc['timestamp'], unit='ms')
    fig.add_trace(go.Candlestick(x=df_calc['dt'], open=df_calc['Open'], high=df_calc['High'], low=df_calc['Low'], close=df_calc['Close']), row=1, col=1)
    
    # Lines for VAH/VAL
    fig.add_hline(y=88000, line_dash="dash", line_color="red", annotation_text="VAH", row=1, col=1)
    fig.add_hline(y=86000, line_dash="dash", line_color="green", annotation_text="VAL", row=1, col=1)

    table_data = [
        ["Signal", "Confidence", "Conclusion"],
        [res.get('signal'), res.get('confidence'), str(res.get('conclusion', ''))[:150]]
    ]
    fig.add_trace(go.Table(header=dict(values=table_data[0]), cells=dict(values=table_data[1:])), row=2, col=1)

    fig.update_layout(title='SFP Strategy Visual Verification', template='plotly_dark', height=900)
    fig.write_html("tests/sfp_verify.html")
    print("Saved to tests/sfp_verify.html")
    await md_agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
