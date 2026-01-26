import asyncio
import pandas as pd
import json
import os
import sys
import time

# Add app to path
sys.path.append(os.getcwd())

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
except ImportError:
    print("Plotly not found. Please run: pip install plotly")
    sys.exit(1)

from app.agents.market_data_agent import MarketDataAgent
from app.agents.ema_strategy_agent import EMAStrategyAgent
from app.core.analysis import AnalysisManager

async def main():
    # 1. Initialize Agents
    md_agent = MarketDataAgent()
    ema_agent = EMAStrategyAgent()
    
    symbol = "BTC-USDT"
    timeframe = "1h"
    
    print(f"--- Visual Verification: EMA Strategy ({symbol} {timeframe}) ---")
    
    # 2. Fetch/Prepare Data
    try:
        ohlcv = await md_agent.exchange.fetch_ohlcv(symbol, timeframe, limit=300)
    except Exception as e:
        print(f"Error fetching data: {e}")
        await md_agent.stop()
        return

    if not ohlcv:
        print("No data received.")
        await md_agent.stop()
        return
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df_calc = md_agent.calculate_indicators(df)
    
    # 3. Populate Sham Analysis Object
    analysis = await AnalysisManager.get_analysis(symbol)
    await analysis.update_section("market_data", df_calc, timeframe)
    
    # Mock some structure data for the agent
    await analysis.update_section("market_structure", {
        "emas_in_order": "ASCENDING",
        "emas_fanning": "EXPANDING"
    }, timeframe)
    await analysis.update_section("market_regime", "BULLISH", timeframe)
    await analysis.update_section("market_regime", {"overall": "BULLISH"})

    # 4. Run Agent Logic
    curr = df_calc.iloc[-1]
    prev = df_calc.iloc[-2]
    
    ema9_curr = curr.get('Exponential Moving Average 9')
    ema21_curr = curr.get('Exponential Moving Average 21')
    
    cross_9_21 = "UP" if (prev.get('Exponential Moving Average 9', 0) <= prev.get('Exponential Moving Average 21', 0) and ema9_curr > ema21_curr) else "NONE"
    
    input_data = {
        "symbol": symbol,
        "timeframe": timeframe,
        "market_context": ema_agent.format_market_context(df_calc, window=30),
        "analysis_summary": {
            "price": curr['Close'],
            "cross_9_21": cross_9_21,
            "market_structure": {"emas_in_order": "ASCENDING", "emas_fanning": "EXPANDING"},
            "regime": "BULLISH",
            "overall_regime": "BULLISH"
        }
    }
    
    print("Calling LLM...")
    try:
        res = await ema_agent.analysis_chain.ainvoke(input_data)
        print(f"Agent Output: {res.get('signal')} ({res.get('confidence')})")
    except Exception as e:
        print(f"LLM Error: {e}")
        res = {"signal": "ERROR", "confidence": 0, "conclusion": str(e), "sl_price": 0, "tp_price": 0}

    # 5. Visualization
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        subplot_titles=(f'Chart: {symbol} {timeframe}', 'Agent Decision Context'),
                        row_heights=[0.7, 0.3],
                        specs=[[{"type": "xy"}], [{"type": "table"}]])

    df_calc['dt'] = pd.to_datetime(df_calc['timestamp'], unit='ms')
    
    # Main Chart
    fig.add_trace(go.Candlestick(x=df_calc['dt'],
                                 open=df_calc['Open'], high=df_calc['High'],
                                 low=df_calc['Low'], close=df_calc['Close'],
                                 name='Price'), row=1, col=1)
    
    # EMAs
    for length, color in {'9': 'yellow', '21': 'orange', '55': 'purple'}.items():
        col = f'Exponential Moving Average {length}'
        if col in df_calc.columns:
            fig.add_trace(go.Scatter(x=df_calc['dt'], y=df_calc[col], 
                                     line=dict(width=1, color=color), name=f'EMA {length}'), row=1, col=1)

    # Decision Table
    table_data = [
        ["Signal", "Confidence", "Conclusion", "SL Price", "TP Price"],
        [res.get('signal'), f"{res.get('confidence', 0):.2f}", str(res.get('conclusion', ''))[:100] + "...", res.get('sl_price'), res.get('tp_price')]
    ]
    
    fig.add_trace(go.Table(
        header=dict(values=table_data[0], fill_color='paleturquoise', align='left'),
        cells=dict(values=table_data[1:], fill_color='lavender', align='left')
    ), row=2, col=1)

    fig.update_layout(title=f'EMA Strategy Visual Verification', height=1000, template='plotly_dark')
    fig.update_xaxes(rangeslider_visible=False)
    
    output_html = "tests/ema_verify.html"
    fig.write_html(output_html)
    print(f"Result saved to {output_html}")
    
    await md_agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
