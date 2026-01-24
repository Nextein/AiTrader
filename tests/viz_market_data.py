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
    print("Plotly not found. Please run: pip install plotly")
    sys.exit(1)

from app.agents.market_data_agent import MarketDataAgent

async def main():
    agent = MarketDataAgent()
    print("Fetching data for BTC-USDT...")
    
    # Ensure exchange is loaded
    await agent.initialize_symbols()
    
    symbol = "BTC-USDT"
    timeframe = "1h"
    
    # Fetch raw
    try:
        # Using fetch_ohlcv directly from exchange to bypass cache mechanism for this valid test
        # or we could use fetch_and_publish but that publishes events.
        # Direct fetch allows us to test "apply multiple indicators to the data when it fetches it" logic
        # by calling the calc method manually or verifying it.
        # But wait, the user said "Market data agent should apply... when it fetches it".
        # So internally `fetch_and_publish` does the fetch AND calc.
        # So I should test `fetch_and_publish` but capture the event?
        # Or I can just call the `calculate_indicators` method which I just added, 
        # which is the core logic the user wants verified.
        # I'll fetch raw and calc, mimicking the internal logic.
        
        ohlcv = await agent.exchange.fetch_ohlcv(symbol, timeframe, limit=1000)
    except Exception as e:
        print(f"Error fetching data: {e}")
        await agent.stop()
        return

    if not ohlcv:
        print("No data received.")
        await agent.stop()
        return
    
    # Mimic the DataFrame creation in the agent
    print("Received raw data. Applying indicators...")
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    
    # Apply indicators using the Agent's methods
    df_calc = agent.calculate_indicators(df)
    
    await agent.stop()
    
    # Plotting
    print("Generating detailed plot...")
    
    # Create subplots
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        subplot_titles=('Price & EMAs & Support/Resistance', 'Volume & Weis Waves & CVD', 'ADX/DI', 'Heikin Ashi'),
                        row_heights=[0.5, 0.2, 0.15, 0.15])

    # Convert timestamp to datetime
    df_calc['dt'] = pd.to_datetime(df_calc['timestamp'], unit='ms')

    # 1. Candlestick
    fig.add_trace(go.Candlestick(x=df_calc['dt'],
                                 open=df_calc['Open'], high=df_calc['High'],
                                 low=df_calc['Low'], close=df_calc['Close'],
                                 name='Price'), row=1, col=1)

    # EMAs
    ema_colors = {'9': 'yellow', '21': 'orange', '55': 'purple', '144': 'blue', '252': 'white'}
    for length, color in ema_colors.items():
        col = f'Exponential Moving Average {length}'
        if col in df_calc.columns:
            fig.add_trace(go.Scatter(x=df_calc['dt'], y=df_calc[col], 
                                     line=dict(width=1, color=color), name=f'EMA {length}'), row=1, col=1)

    # Fractals (Scatter)
    for n in [5, 7, 9]:
        col_name = f'Williams Fractals {n}'
        if col_name in df_calc.columns:
            fr = df_calc[df_calc[col_name].notna()]
            # Cycle colors or symbols
            colors = {5: 'cyan', 7: 'magenta', 9: 'yellow'}
             # Use a slight offset in marker size or symbol to distinguish if they overlap?
            fig.add_trace(go.Scatter(x=pd.to_datetime(fr['timestamp'], unit='ms'), y=fr[col_name],
                                     mode='markers', marker=dict(symbol='triangle-up' if n==5 else 'circle', size=8 + (n-5), color=colors.get(n, 'white')),
                                     name=f'Fractals ({n})'), row=1, col=1)
    
    # Pivot Points
    if 'Pivot Points' in df_calc.columns:
         fig.add_trace(go.Scatter(x=df_calc['dt'], y=df_calc['Pivot Points'],
                                  mode='lines', line=dict(color='pink', width=1, dash='dash'),
                                  name='Pivot'), row=1, col=1)

    # S/R
    if 'Closest Support' in df_calc.columns:
        fig.add_trace(go.Scatter(x=df_calc['dt'], y=df_calc['Closest Support'],
                                 mode='lines', line=dict(color='green', dash='dot', width=2),
                                 name='Closest Support'), row=1, col=1)
    if 'Closest Resistance' in df_calc.columns:
        fig.add_trace(go.Scatter(x=df_calc['dt'], y=df_calc['Closest Resistance'],
                                 mode='lines', line=dict(color='red', dash='dot', width=2),
                                 name='Closest Resistance'), row=1, col=1)

    # 2. Volume & Waves & CVD
    # Volume
    fig.add_trace(go.Bar(x=df_calc['dt'], y=df_calc['Volume'], marker_color='grey', name='Volume', opacity=0.3), row=2, col=1)
    
    # Weis Waves
    if 'Weis Waves Volume' in df_calc.columns and 'Weis Waves Direction' in df_calc.columns:
         colors = list(map(lambda d: 'green' if d > 0 else 'red', df_calc['Weis Waves Direction']))
         fig.add_trace(go.Bar(x=df_calc['dt'], y=df_calc['Weis Waves Volume'], name='Weis Waves', marker_color=colors, opacity=0.5), row=2, col=1)
    elif 'Weis Waves Volume' in df_calc.columns:
         fig.add_trace(go.Bar(x=df_calc['dt'], y=df_calc['Weis Waves Volume'], name='Weis Waves', marker_color='blue', opacity=0.5), row=2, col=1)

    # CVD (Scatter line)
    if 'Cumulative Volume Delta' in df_calc.columns:
         # Use a separate axis if necessary, but plot tries to fit.
         fig.add_trace(go.Scatter(x=df_calc['dt'], y=df_calc['Cumulative Volume Delta'], name='CVD', line=dict(color='yellow')), row=2, col=1)

    # 3. ADX
    if 'Average Directional Index' in df_calc.columns:
        fig.add_trace(go.Scatter(x=df_calc['dt'], y=df_calc['Average Directional Index'], line=dict(color='white'), name='ADX'), row=3, col=1)
    if 'Positive Directional Indicator' in df_calc.columns:
        fig.add_trace(go.Scatter(x=df_calc['dt'], y=df_calc['Positive Directional Indicator'], line=dict(color='green'), name='DI+'), row=3, col=1)
    if 'Negative Directional Indicator' in df_calc.columns:
        fig.add_trace(go.Scatter(x=df_calc['dt'], y=df_calc['Negative Directional Indicator'], line=dict(color='red'), name='DI-'), row=3, col=1)
        
    # 4. Heikin Ashi
    if 'Heikin Ashi Open' in df_calc.columns:
         fig.add_trace(go.Candlestick(x=df_calc['dt'],
                                 open=df_calc['Heikin Ashi Open'], high=df_calc['Heikin Ashi High'],
                                 low=df_calc['Heikin Ashi Low'], close=df_calc['Heikin Ashi Close'],
                                 name='Heikin Ashi'), row=4, col=1)
    
    fig.update_layout(title=f'Market Data Verification: {symbol} {timeframe}', 
                      height=1600, width=1200, template='plotly_dark')
    fig.update_xaxes(rangeslider_visible=False)
    
    output_file = "market_data_verification.html"
    fig.write_html(output_file)
    print(f"Plot saved to {output_file}")
    
    # Print a small sample of columns
    print("\nSample Data (Last 5 rows):")
    print(df_calc[['timestamp', 'Close', 'Exponential Moving Average 9', 'Williams Fractals 5', 'Closest Support']].tail())

if __name__ == "__main__":
    asyncio.run(main())
