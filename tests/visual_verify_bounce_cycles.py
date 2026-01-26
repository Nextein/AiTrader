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
from app.agents.bounce_strategy_agent import BounceStrategyAgent
from app.agents.cycles_strategy_agent import CyclesStrategyAgent

async def main():
    md = MarketDataAgent()
    bounce = BounceStrategyAgent()
    cycles = CyclesStrategyAgent()
    
    symbol = "BTC-USDT"
    timeframe = "1h"
    
    print(f"--- Visual Verification: Bounce & Cycles ({symbol}) ---")
    
    try:
        ohlcv = await md.exchange.fetch_ohlcv(symbol, timeframe, limit=300)
    except Exception as e:
        print(f"Error fetching data: {e}")
        await md.stop()
        return

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df_calc = md.calculate_indicators(df)
    
    # 1. Test Bounce Strategy
    bounce_input = {
        "symbol": symbol,
        "timeframe": timeframe,
        "market_context": bounce.format_market_context(df_calc, window=30, columns=['Open', 'High', 'Low', 'Close', 'Exponential Moving Average 21', 'Linear Regression Slope']),
        "analysis_summary": {
            "price": df_calc['Close'].iloc[-1],
            "macd_val": 10.0, "d1_trend": "UP", "h4_pullback": "YES", "regime": "BULLISH"
        }
    }
    
    print("Calling LLM for Bounce Strategy...")
    try:
        bounce_res = await bounce.analysis_chain.ainvoke(bounce_input)
    except Exception as e:
        bounce_res = {"signal": "ERROR", "conclusion": str(e), "confidence": 0}

    # 2. Test Cycles Strategy
    cycles_input = {
        "symbol": symbol,
        "timeframe": timeframe,
        "market_context": cycles.format_market_context(df_calc, window=30, columns=['Open', 'High', 'Low', 'Close', 'Heikin Ashi Close', 'Relative Candles Phase']),
        "analysis_summary": {
            "price": df_calc['Close'].iloc[-1],
            "ha_dir": "UP", "rel_phase": "UP", "trigger_activated": "YES", "regime": "BULLISH", "atr": 500.0
        }
    }
    
    print("Calling LLM for Cycles Strategy...")
    try:
        cycles_res = await cycles.analysis_chain.ainvoke(cycles_input)
    except Exception as e:
        cycles_res = {"signal": "ERROR", "conclusion": str(e), "confidence": 0}

    # Visualization
    fig = make_subplots(rows=3, cols=1, row_heights=[0.6, 0.2, 0.2], 
                        subplot_titles=('Price & HA/RCP Indicators', 'Bounce Decision', 'Cycles Decision'),
                        specs=[[{"type": "xy"}], [{"type": "table"}], [{"type": "table"}]])
    
    df_calc['dt'] = pd.to_datetime(df_calc['timestamp'], unit='ms')
    fig.add_trace(go.Candlestick(x=df_calc['dt'], open=df_calc['Open'], high=df_calc['High'], low=df_calc['Low'], close=df_calc['Close'], name='Price'), row=1, col=1)
    
    # Decisions
    bounce_table = [["Agent", "Signal", "Confidence", "Conclusion"], ["Bounce", bounce_res.get('signal'), bounce_res.get('confidence'), str(bounce_res.get('conclusion', ''))[:150]]]
    cycles_table = [["Agent", "Signal", "Confidence", "Conclusion"], ["Cycles", cycles_res.get('signal'), cycles_res.get('confidence'), str(cycles_res.get('conclusion', ''))[:150]]]
    
    fig.add_trace(go.Table(header=dict(values=bounce_table[0]), cells=dict(values=bounce_table[1:])), row=2, col=1)
    fig.add_trace(go.Table(header=dict(values=cycles_table[0]), cells=dict(values=cycles_table[1:])), row=3, col=1)
    
    fig.update_layout(title='Bounce & Cycles Visual Verification', template='plotly_dark', height=1200)
    fig.write_html("tests/bounce_cycles_verify.html")
    print("Saved to tests/bounce_cycles_verify.html")
    await md.stop()

if __name__ == "__main__":
    asyncio.run(main())
