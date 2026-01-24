import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.core.event_bus import event_bus, EventType
from app.core.database import SessionLocal
from app.models.models import CandleModel
import logging

logger = logging.getLogger("MarketDataAgent")

class MarketDataAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MarketDataAgent")
        self.exchange = ccxt.bingx({
            'apiKey': settings.BINGX_API_KEY,
            'secret': settings.BINGX_SECRET_KEY,
            'options': {
                'defaultType': 'swap',  # Trading perps
                'sandbox': settings.BINGX_IS_SANDBOX, 
            }
        })
        # Task 4: Fetch all symbols or use configured ones
        self.symbols = settings.TRADING_SYMBOLS if hasattr(settings, 'TRADING_SYMBOLS') else []
        self.fetch_all_symbols = getattr(settings, 'FETCH_ALL_SYMBOLS', False)
        
        # Task 6: Prioritized timeframes (higher to lower)
        self.timeframes = getattr(settings, 'TIMEFRAMES', [settings.TIMEFRAME]) if hasattr(settings, 'TIMEFRAMES') else [settings.TIMEFRAME]
        self.timeframe = settings.TIMEFRAME  # Default timeframe
        
        # Task 5: Cache tracking
        self.cache_enabled = True

    async def initialize_symbols(self):
        """Task 4: Fetch all available symbols from exchange"""
        if self.fetch_all_symbols:
            try:
                markets = await self.exchange.load_markets()
                # Filter for USDT perpetual contracts
                self.symbols = [symbol for symbol in markets.keys() if '/USDT' in symbol and ':USDT' in symbol]
                logger.info(f"Loaded {len(self.symbols)} symbols from exchange")
            except Exception as e:
                logger.error(f"Failed to load symbols: {e}. Using configured symbols.")
                self.symbols = settings.TRADING_SYMBOLS

    def get_status(self):
        status = super().get_status()
        status["config"] = {
            "symbols": self.symbols[:5] if len(self.symbols) > 5 else self.symbols,  # Show first 5
            "total_symbols": len(self.symbols),
            "timeframes": self.timeframes,
            "cache_enabled": self.cache_enabled
        }
        return status

    async def run_loop(self):
        """Main loop with prioritized fetching"""
        # Initialize symbols if needed
        if self.fetch_all_symbols or not self.symbols:
            await self.initialize_symbols()
        
        # Subscribe to market data requests
        event_bus.subscribe(EventType.MARKET_DATA_REQUEST, self.handle_data_request)
        
        while self.is_running and self.is_active:
            # Task 6: Fetch in order from higher timeframe to lower
            for timeframe in sorted(self.timeframes, key=lambda x: self._timeframe_to_minutes(x), reverse=True):
                if not self.is_running or not self.is_active:
                    break
                    
                for symbol in self.symbols:
                    if not self.is_running or not self.is_active:
                        break
                    try:
                        await self.fetch_and_publish(symbol, timeframe)
                    except Exception as e:
                        logger.error(f"Error fetching {symbol} {timeframe}: {e}")
                        await asyncio.sleep(0.1)  # Brief pause on error
            
            # Sleep between cycles
            await asyncio.sleep(10)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies all requested indicators to the DataFrame"""
        try:
            # ensure standard columns
            df.columns = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
            
            # Ensure proper types
            df['timestamp'] = df['timestamp'].astype('int64')
            
            # Set index for pandas-ta (some indicators like Pivots require it)
            # We keep the 'timestamp' column as well for export
            df.set_index(pd.to_datetime(df['timestamp'], unit='ms'), inplace=True, drop=False)
            
            # 1. Heikin Ashi
            ha = ta.ha(df['Open'], df['High'], df['Low'], df['Close'])
            df['Heikin Ashi Open'] = ha['HA_open']
            df['Heikin Ashi High'] = ha['HA_high']
            df['Heikin Ashi Low'] = ha['HA_low']
            df['Heikin Ashi Close'] = ha['HA_close']

            # 2. Relative Candles (Open - PrevClose, Close - PrevClose)
            # Assuming 'Relative' means relative to previous close to determine 'Gap' or absolute move
            # If TODO implies something else, this is the best reasonable interpretation for "Relative Candles Open/Close"
            prev_close = df['Close'].shift(1)
            df['Relative Candles Open'] = df['Open'] - prev_close
            df['Relative Candles Close'] = df['Close'] - prev_close
            df['Relative Candles Open'] = df['Relative Candles Open'].fillna(0)
            df['Relative Candles Close'] = df['Relative Candles Close'].fillna(0)

            # 3. Trends/Oscillators
            # ADX
            adx_df = df.ta.adx(length=14)
            if adx_df is not None:
                df['Average Directional Index'] = adx_df.get('ADX_14', 0)
                df['Positive Directional Indicator'] = adx_df.get('DMP_14', 0)
                df['Negative Directional Indicator'] = adx_df.get('DMN_14', 0)
            
            # ATR
            df['Average True Range'] = df.ta.atr(length=14)
            
            # OBV
            df['On-Balance Volume'] = df.ta.obv()

            # 4. Weis Waves Helper
            def calculate_weis_waves(close_s, open_s, vol_s, method='standard'):
                # Determine phase
                # standard: close > open is UP
                # relative: close > prev_close (which is what we approximated with Relative Candles Close > 0, if RelOpen=Open-PrevClose, RelClose=Close-PrevClose)
                # But wait, Relative Phase in TODO line 29: "Relative Phase: NOT INCLUDED...".
                # But "Relative Weis Waves... phases determined by relative candles".
                # If RelativeCandleClose > RelativeCandleOpen <=> (Close-Prev) > (Open-Prev) <=> Close > Open.
                # So relative candles phase must utilize the "Gap".
                # Let's assume:
                # Standard: Green if Close > Open.
                # Heikin Ashi: Green if HA_Close > HA_Open.
                # Relative: Green if Close > Prev Close? (Common "solid/hollow" logic).
                
                direction = pd.Series(0, index=close_s.index)
                
                if method == 'standard':
                    direction = np.sign(close_s - open_s)
                elif method == 'heikin':
                    direction = np.sign(close_s - open_s) # Pass HA series
                elif method == 'relative':
                     # Use Change from previous Close
                     # If Close > PrevClose => Up.
                     prev = close_s.shift(1)
                     direction = np.sign(close_s - prev)
                
                # Replace 0 with prev direction to maintain wave? Or 0 is neutral?
                # Usually 0 (doji) continues previous wave or is ignored.
                direction = direction.replace(0, np.nan).ffill().fillna(1) # Default to 1

                # Calculate Wave Volume
                # Use a loop for correctness (or vectorization with groupby)
                # Group by consecutive blocks of same direction
                # ID = (Direction != Direction.shift()).cumsum()
                block_id = (direction != direction.shift(1)).cumsum()
                
                # Sum volume by block
                # But we want the CUMULATIVE volume AT EACH CANDLE for the CURRENT wave
                # So it's a transform with cumsum
                waves = vol_s.groupby(block_id).cumsum()
                
                # Signed Weis Wave? Or just Volume? Weis Waves are usually signed or plotted histogram.
                # TODO says "Weis Waves Volume". I'll keep it absolute volume for the wave, maybe signed by direction?
                # Usually it's positive, color indicates direction.
                return waves

            df['Weis Waves Volume'] = calculate_weis_waves(df['Close'], df['Open'], df['Volume'], 'standard')
            df['Relative Weis Waves Volume'] = calculate_weis_waves(df['Close'], df['Open'], df['Volume'], 'relative')
            df['Heikin Ashi Weis Waves Volume'] = calculate_weis_waves(df['Heikin Ashi Close'], df['Heikin Ashi Open'], df['Volume'], 'heikin')
            
            # 5. EMAs
            for length in [9, 21, 55, 144, 252]:
                if len(df) >= length:
                    df[f'Exponential Moving Average {length}'] = ta.ema(df['Close'], length=length)
                else:
                    df[f'Exponential Moving Average {length}'] = float('nan')

            # 6. Pivot Points (Using Standard or Fibonacci? Defaulting to Traditional)
            # pivots returns dataframe with columns P, S1...
            pivots = df.ta.pivots(open='Open', high='High', low='Low', close='Close')
            if pivots is not None:
                # Pivot Points in DataFrame usually implies the Point P.
                # We will simplify and maybe just take P? The user said "Pivot Points" (plural).
                # But we can't add 10 columns if only one requested.
                # Let's add 'Pivot Points' as the main Pivot.
                # Check column names: usually 'PIVOT_F_P', 'PIVOT_T_P' etc depending on method.
                # Default is Traditional: PIVOT_T_P
                if 'PIVOT_T_P' in pivots.columns:
                     df['Pivot Points'] = pivots['PIVOT_T_P']
                else:
                     # Fallback, just take the first column
                     df['Pivot Points'] = pivots.iloc[:, 0]
            
            # 7. Williams Fractals and Closest S/R
            # Fractal(n): High is max of range n.
            # 3, 5, 7.
            # Custom implementation for robustness and S/R logic
            
            def get_fractals(high, low, n):
                # Center index is offset. n=5 -> offset=2.
                # We need to look forward, so we can only know fractal N/2 candles ago.
                # But for indicators, we often repaint or flag it when confirmed.
                # Repainting is bad for trading.
                # BUT, "Closest Support... based on Williams Fractals 7".
                # If we are at time T, we can only see fractals confirmed up to T-3.
                # I will calculate fractals based on available data. The most recent 3 values will be NaN (for n=7).
                
                offset = n // 2
                
                # Rolling max centered was deprecated? Or use shift.
                # Construct condition.
                
                # Efficient way:
                # is_high = (high == high.rolling(n, center=True).max()) 
                # strictly greater? Williams usually distinct.
                # Using pandas centered rolling is easiest, but it looks ahead.
                # We have the data, so we can calculate it. 
                # The "Latest" candle cannot be a fractal yet.
                
                # For plotting/analysis (TODO context), we mark past fractals.
                
                up_fractals = (high == high.rolling(window=n, center=True).max())
                down_fractals = (low == low.rolling(window=n, center=True).min())
                
                # Mask unconfirmed (last offset candles)
                # But rolling center=True with defaults produces NaNs at ends anyway?
                # No, pandas rolling min_periods.
                
                # Values: Price or NaN
                fractal_highs = pd.Series(np.nan, index=high.index)
                fractal_lows = pd.Series(np.nan, index=low.index)
                
                fractal_highs[up_fractals] = high[up_fractals]
                fractal_lows[down_fractals] = low[down_fractals]
                
                return fractal_highs, fractal_lows

            # Calculate and store
            for n in [3, 5, 7]:
                fh, fl = get_fractals(df['High'], df['Low'], n)
                # TODO asks for "Williams Fractals N". It's a single column? 
                # Fractals split into Up/Down. 
                # Maybe string "Bearish/Bullish"? 
                # Or maybe the Price?
                # I'll add two columns per N? Or one combined?
                # "Williams Fractals 3" -> Suggests one column.
                # I will store the Price if it matches either, else NaN.
                # If both (rare/impossible for odd n?), prefer one.
                merged = fh.fillna(fl)
                df[f'Williams Fractals {n}'] = merged

            # 8. CVD
            # Approx: Vol if Close > Open else -Vol
            # direction = np.sign(df['Close'] - df['Open']).replace(0, 1) # Treat doji as buy? or 0? 0 is safe.
            direction = np.where(df['Close'] >= df['Open'], 1, -1)
            df['Cumulative Volume Delta'] = (df['Volume'] * direction).cumsum()

            # 9. Closest Support/Resistance (Fractals 7)
            # Support: Max(FractalLow) < current_price (using body)
            # Resistance: Min(FractalHigh) > current_price (using body)
            # "The price is obtained from the body... Usually it is the body..."
            # Refinement: For the fractal CANDLE, use Body High/Low.
            # Fractal 7 Lows -> Use Min(Open, Close) of that candle.
            # Fractal 7 Highs -> Use Max(Open, Close) of that candle.
            
            f7_highs, f7_lows = get_fractals(df['High'], df['Low'], 7)
            
            # Map fractal prices to BODY prices
            # We need the index of fractals
            # f7_lows has values at indices where low is fractal.
            # We want the body bottom at those indices.
            body_bottom = list(np.minimum(df['Open'], df['Close']))
            body_top = list(np.maximum(df['Open'], df['Close']))
            
            # We need to iterate to simulate "Closest at time T"
            # Vectorizing "closest past value" is hard. Use loop.
            
            supports = []
            resistances = []
            
            # Maintain sorted lists of active S/R levels observed so far?
            # Or just brute force lookback? 100 candles is small. Brute force is fine.
            
            valid_supports = [] # list of prices
            valid_resistances = [] # list of prices
            
            # We can pre-calculate the Body values for fractal points
            # is_f7_low = f7_lows.notna()
            # is_f7_high = f7_highs.notna()
            
            # Convert to list for speed
            f7_low_vals = f7_lows.values
            f7_high_vals = f7_highs.values
            closes = df['Close'].values
            
            for i in range(len(df)):
                # 1. Update valid levels with NEW fractals confirmed at i
                # Note: Fractal 7 is confirmed at i-3.
                # So at step i, we look if i-3 was a fractal.
                
                conf_idx = i - 3
                if conf_idx >= 0:
                    if not np.isnan(f7_low_vals[conf_idx]):
                        # Add Body Low of conf_idx
                        valid_supports.append(body_bottom[conf_idx])
                    if not np.isnan(f7_high_vals[conf_idx]):
                        # Add Body High of conf_idx
                        valid_resistances.append(body_top[conf_idx])
                
                current_price = closes[i] # "Closest ... to current price ... from body ... THIS can be open or close"
                # The TODO says "The price is obtained from the body... for the william fractal".
                # It says "Closest ... level to the current price". Current price is Close (or Open if forming? Close is fine).
                
                # Support: Closest value in valid_supports < current_price?
                # Or just absolute closest?
                # "Support" implies BELOW. "Resistance" implies ABOVE.
                # I will filter valid_supports < current_price, then take Max.
                
                # Filter strictly below
                below = [s for s in valid_supports if s < current_price]
                if below:
                    supports.append(max(below))
                else:
                    supports.append(None) # No support found
                    
                # Filter strictly above
                above = [r for r in valid_resistances if r > current_price]
                if above:
                    resistances.append(min(above))
                else:
                    resistances.append(None)

            df['Closest Support'] = supports
            df['Closest Resistance'] = resistances

            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}", exc_info=True)
            return df

    async def fetch_and_publish(self, symbol: str, timeframe: str):
        """Fetch data with caching support (Task 5)"""
        # Check cache first
        if self.cache_enabled:
            cached_data = self.get_cached_data(symbol, timeframe)
            if cached_data and self.is_cache_valid(cached_data, timeframe):
                # We need to reconstruct DF to calc indicators? 
                # Yes, because cached data might be just raw OHLCV or old format.
                # For now assume cached data is OHLCV. 
                # Calculating indicators on every fetch is okay.
                
                df_cache = pd.DataFrame(cached_data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df_with_ind = self.calculate_indicators(df_cache)
                
                # Serialize
                # We can pass the whole DF content as 'candles' (list of lists) and 'columns'
                columns = df_with_ind.columns.tolist()
                values = df_with_ind.replace({np.nan: None}).values.tolist()
                
                data = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "candles": values,
                    "columns": columns,
                    "latest_close": df_cache['Close'].values[-1],
                    "timestamp": float(df_cache['timestamp'].values[-1]),
                    "agent": self.name,
                    "from_cache": True
                }
                await event_bus.publish(EventType.MARKET_DATA, data)
                self.processed_count += 1
                return
        
        # Fetch fresh data
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            
            if not ohlcv:
                return
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df_with_ind = self.calculate_indicators(df)
            
            columns = df_with_ind.columns.tolist()
            values = df_with_ind.replace({np.nan: None}).values.tolist()
            
            data = {
                "symbol": symbol,
                "timeframe": timeframe,
                "candles": values,
                "columns": columns,
                "latest_close": df_with_ind['Close'].iloc[-1],
                "timestamp": df_with_ind['timestamp'].iloc[-1],
                "agent": self.name,
                "from_cache": False
            }
            
            await event_bus.publish(EventType.MARKET_DATA, data)
            self.processed_count += 1

            # Persist to DB/cache -> Only persist RAW OHLCV to save space and re-calc on load?
            # Or persist everything?
            # `persist_candles` currently only handles OHLCV logic. 
            # I will keep persisting only OHLCV to maintain schema compatibility.
            self.persist_candles(symbol, timeframe, ohlcv)
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol} {timeframe}: {e}")
            await event_bus.publish(EventType.ERROR, {"agent": self.name, "symbol": symbol, "error": str(e)})

    async def handle_data_request(self, data: Dict[str, Any]):
        """Handle on-demand data requests from other agents (Task 5)"""
        if not self.is_active:
            return
            
        symbol = data.get('symbol')
        timeframe = data.get('timeframe', self.timeframe)
        requester = data.get('requester', 'Unknown')
        
        if symbol:
            logger.info(f"Received data request from {requester} for {symbol} {timeframe}")
            await self.fetch_and_publish(symbol, timeframe)

    def get_cached_data(self, symbol: str, timeframe: str) -> List:
        """Retrieve cached candles from database (Task 5)"""
        try:
            with SessionLocal() as db:
                candles = db.query(CandleModel).filter(
                    CandleModel.symbol == symbol,
                    CandleModel.timeframe == timeframe
                ).order_by(CandleModel.timestamp.asc()).limit(100).all()
                
                if candles:
                    return [[
                        int(c.timestamp.timestamp() * 1000),
                        c.open, c.high, c.low, c.close, c.volume
                    ] for c in candles]
                return None
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def is_cache_valid(self, cached_data: List, timeframe: str) -> bool:
        """Check if cached data contains the current candle (Task 5)"""
        if not cached_data:
            return False
        
        last_candle_time = cached_data[-1][0]  # timestamp in ms
        current_time = datetime.now().timestamp() * 1000
        
        # Get timeframe duration in ms
        tf_minutes = self._timeframe_to_minutes(timeframe)
        tf_ms = tf_minutes * 60 * 1000
        
        # Check if last candle is the current one
        # If time_diff < tf_ms, it means we are still in the same candle window (approx)
        time_diff = current_time - last_candle_time
        return time_diff < tf_ms

    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes"""
        multipliers = {'m': 1, 'h': 60, 'd': 1440, 'w': 10080}
        if len(timeframe) < 2:
            return 60  # Default
        try:
            # Handle '15m' -> 15 * 1
            unit = timeframe[-1]
            if unit in multipliers:
                 val = int(timeframe[:-1])
                 return val * multipliers[unit]
            return 60
        except:
            return 60

    def persist_candles(self, symbol: str, timeframe: str, candles: List):
        """Persist candles to database cache (Task 5)"""
        try:
            with SessionLocal() as db:
                for c in candles:
                    # c is raw OHLCV list: [ts, o, h, l, c, v]
                    ts = datetime.fromtimestamp(c[0] / 1000.0)
                    
                    # Optimization: only check last? or merge?
                    # For now keep naive merge loop
                    existing = db.query(CandleModel).filter(
                        CandleModel.symbol == symbol,
                        CandleModel.timestamp == ts,
                        CandleModel.timeframe == timeframe
                    ).first()
                    
                    if not existing:
                        candle = CandleModel(
                            symbol=symbol,
                            timeframe=timeframe,
                            timestamp=ts,
                            open=c[1],
                            high=c[2],
                            low=c[3],
                            close=c[4],
                            volume=c[5]
                        )
                        db.add(candle)
                db.commit()
        except Exception as e:
             logger.error(f"Error persisting candles: {e}")

    async def stop(self):
        await super().stop()
        await self.exchange.close()
