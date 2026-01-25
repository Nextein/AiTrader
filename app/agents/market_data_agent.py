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
from app.core.analysis import AnalysisManager
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
        # Symbol management: now handled by Governor + SYMBOL_APPROVED events
        self.symbols = []
        
        # Task 6: Prioritized timeframes (higher to lower)
        self.timeframes = getattr(settings, 'TIMEFRAMES', [settings.TIMEFRAME]) if hasattr(settings, 'TIMEFRAMES') else [settings.TIMEFRAME]
        self.timeframe = settings.TIMEFRAME  # Default timeframe
        
        # Task 5: Cache tracking
        self.cache_enabled = True
        
        # Retry configuration
        self.max_retries = 6
        self.retry_delays = [1, 2, 5]  # Exponential backoff delays in seconds
        self.retry_tracker = {}  # Track retries per symbol-timeframe: {(symbol, tf): retry_count}

    async def handle_symbol_approved(self, data: Dict[str, Any]):
        """Callback for when a symbol is approved by SanityAgent"""
        symbol = data.get("symbol")
        if symbol and symbol not in self.symbols:
            logger.info(f"MarketDataAgent: Adding approved symbol {symbol}")
            self.symbols.append(symbol)

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
        # Subscribe to events
        event_bus.subscribe(EventType.MARKET_DATA_REQUEST, self.handle_data_request)
        event_bus.subscribe(EventType.SYMBOL_APPROVED, self.handle_symbol_approved)
        
        while self.is_running and self.is_active:
            if not self.symbols:
                # Wait for some symbols to be approved
                logger.debug("MarketDataAgent: Waiting for approved symbols...")
                await asyncio.sleep(5)
                continue

            # Task 6: Fetch in order from higher timeframe to lower
            for timeframe in sorted(self.timeframes, key=lambda x: self._timeframe_to_minutes(x), reverse=True):
                if not self.is_running or not self.is_active:
                    break
                    
                for symbol in self.symbols:
                    if not self.is_running or not self.is_active:
                        break
                    await self.fetch_and_publish(symbol, timeframe)
            
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

            # 2. Relative Candles (Logic from TODO.md)
            # We strictly implement the state machine and phase logic provided.
            # Convert to numpy for faster access
            opens = df['Open'].values
            highs = df['High'].values
            lows = df['Low'].values
            closes = df['Close'].values
            n = len(df)
            
            # Helper lambdas (using numpy array indexing)
            # Note: i is index
            def is_HH(i): return i > 0 and highs[i] > highs[i-1]
            def is_HL(i): return i > 0 and lows[i] > lows[i-1]
            def is_LH(i): return i > 0 and highs[i] < highs[i-1]
            def is_LL(i): return i > 0 and lows[i] < lows[i-1]
            def is_green(i): return closes[i] > opens[i]
            def is_red(i): return closes[i] < opens[i]

            states = ['X'] * n
            
            for i in range(2, n):
                prev_state = states[i-1]
                
                # Logic from TODO.md
                if prev_state == 'X':
                    if is_HH(i) and is_HL(i): states[i] = 'U'
                    elif is_LH(i) and is_LL(i): states[i] = 'D'
                    elif is_LH(i) and is_HL(i):
                        if is_LH(i-1) and is_HL(i-1): states[i] = 'I2'
                        else: states[i] = 'I'
                    elif is_HH(i) and is_LL(i):
                        if is_green(i): states[i] = 'RU2'
                        elif is_red(i): states[i] = 'RD2'

                elif prev_state == 'U':
                    if is_HH(i) and is_HL(i): states[i] = 'U'
                    elif is_LH(i) and is_LL(i): states[i] = 'RD'
                    elif is_LH(i) and is_HL(i):
                        if is_LH(i-1) and is_HL(i-1): states[i] = 'I2'
                        else: states[i] = 'I'
                    elif is_HH(i) and is_LL(i): states[i] = 'RU'

                elif prev_state == 'D':
                    if is_HH(i) and is_HL(i): states[i] = 'RU'
                    elif is_LH(i) and is_LL(i): states[i] = 'D'
                    elif is_LH(i) and is_HL(i):
                        if is_LH(i-1) and is_HL(i-1): states[i] = 'I2'
                        else: states[i] = 'I'
                    elif is_HH(i) and is_LL(i): states[i] = 'RU' # Code says RU for both? line 107
                
                elif prev_state in ['RU', 'RU2']:
                    if is_HH(i) and is_HL(i): states[i] = 'U'
                    elif is_LH(i) and is_LL(i): states[i] = 'RD'
                    elif is_LH(i) and is_HL(i):
                        if is_LH(i-1) and is_HL(i-1): states[i] = 'I2'
                        else: states[i] = 'I'
                    elif is_HH(i) and is_LL(i):
                        if is_green(i): states[i] = 'RU2'
                        elif is_red(i): states[i] = 'RD2'

                elif prev_state in ['RD', 'RD2']:
                    if is_HH(i) and is_HL(i): states[i] = 'RU'
                    elif is_LH(i) and is_LL(i): states[i] = 'D'
                    elif is_LH(i) and is_HL(i): states[i] = 'I'
                    elif is_HH(i) and is_LL(i):
                        if is_green(i): states[i] = 'RU2'
                        elif is_red(i): states[i] = 'RD2'
                
                elif prev_state == 'I':
                    if is_HH(i) and is_HL(i): states[i] = 'RU'
                    elif is_LH(i) and is_LL(i): states[i] = 'RD'
                    elif is_LH(i) and is_HL(i): states[i] = 'I2'
                    elif is_HH(i) and is_LL(i):
                        if is_green(i): states[i] = 'RU2'
                        elif is_red(i): states[i] = 'RD2'

                elif prev_state == 'I2':
                    if is_HH(i) and is_HL(i): states[i] = 'RU'
                    elif is_LH(i) and is_LL(i): states[i] = 'RD'
                    elif is_LH(i) and is_HL(i): states[i] = 'I2'
                    elif is_HH(i) and is_LL(i):
                        if is_green(i): states[i] = 'RU2'
                        elif is_red(i): states[i] = 'RD2'
                else:
                    states[i] = 'X'

            # Calculate Phases
            phases = np.zeros(n)
            # Initialize first phase (0)
            phases[0] = 1 if is_green(0) else -1
            for i in range(1, 3):
                phases[i] = phases[i-1]

            for i in range(3, n):
                s2, s1, s0 = states[i-2], states[i-1], states[i]
                
                up_seq = (
                    (s1 == 'D' and s0 == 'RU') or
                    (s2 == 'D' and s1 == 'I' and s0 == 'RU') or
                    (s1 == 'D' and s0 == 'RU2') or
                    (s2 == 'D' and s1 == 'I' and s0 == 'RU2') or
                    (s1 == 'RD' and s0 == 'RU') or
                    (s2 == 'RD' and s1 == 'I' and s0 == 'RU') or
                    (s1 == 'RD' and s0 == 'RU2') or
                    (s2 == 'RD' and s1 == 'I' and s0 == 'RU2') or
                    (s1 == 'RD2' and s0 == 'RU') or
                    (s2 == 'RD2' and s1 == 'I' and s0 == 'RU') or
                    (s1 == 'RD2' and s0 == 'RU2') or
                    (s2 == 'RD2' and s1 == 'I' and s0 == 'RU2') or
                    (s2 == 'I' and s1 == 'I2' and s0 == 'RU') or
                    (s2 == 'I' and s1 == 'I2' and s0 == 'RU2')
                )
                
                down_seq = (
                    (s1 == 'U' and s0 == 'RD') or
                    (s2 == 'U' and s1 == 'I' and s0 == 'RD') or
                    (s1 == 'U' and s0 == 'RD2') or
                    (s2 == 'U' and s1 == 'I' and s0 == 'RD2') or
                    (s1 == 'RU' and s0 == 'RD') or
                    (s2 == 'RU' and s1 == 'I' and s0 == 'RD') or
                    (s1 == 'RU' and s0 == 'RD2') or
                    (s2 == 'RU' and s1 == 'I' and s0 == 'RD2') or
                    (s1 == 'RU2' and s0 == 'RD') or
                    (s2 == 'RU2' and s1 == 'I' and s0 == 'RD') or
                    (s1 == 'RU2' and s0 == 'RD2') or
                    (s2 == 'RU2' and s1 == 'I' and s0 == 'RD2') or
                    (s2 == 'I' and s1 == 'I2' and s0 == 'RD') or
                    (s2 == 'I' and s1 == 'I2' and s0 == 'RD2')
                )
                
                if up_seq:
                    phases[i] = 1
                elif down_seq:
                    phases[i] = -1
                else:
                    phases[i] = phases[i-1]

            # Calculate Relative Candles Open/Close (Drawing Logic)
            # Logic provided by user:
            # HH & !LL -> Bullish (O=L, C=H)
            # LL & !HH -> Bearish (O=H, C=L)
            # HH & LL -> Outside (Follows original candle color: Red->Full Red, Green->Full Green)
            # Else (Inside/Equal) -> Bearish Full (O=H, C=L)
            
            rel_opens = np.copy(opens)
            rel_closes = np.copy(closes)
            rel_modes = np.array(['Standard'] * n, dtype=object)
            
            # Vectorize or Loop? Loop is strictly safer for exact logic match, n is small (100-1000)
            for i in range(1, n):
                prev_h = highs[i-1]
                prev_l = lows[i-1]
                curr_h = highs[i]
                curr_l = lows[i]
                curr_o = opens[i]
                curr_c = closes[i]
                
                hh = curr_h > prev_h
                ll = curr_l < prev_l
                
                if hh and not ll:
                    rel_opens[i] = curr_l
                    rel_closes[i] = curr_h
                elif ll and not hh:
                    rel_opens[i] = curr_h
                    rel_closes[i] = curr_l
                elif hh and ll:
                    if curr_o > curr_c: # Original Red
                        rel_opens[i] = curr_h
                        rel_closes[i] = curr_l
                    else: # Original Green/Doji
                        rel_opens[i] = curr_l
                        rel_closes[i] = curr_h
                else:
                    # Inside or exact -> O=High, C=Low (Red in basic logic, but marked Inside for Gray)
                    rel_opens[i] = curr_h
                    rel_closes[i] = curr_l
                    rel_modes[i] = 'Inside'

            df['Relative Candles Open'] = rel_opens
            df['Relative Candles Close'] = rel_closes
            df['Relative Candles Mode'] = rel_modes
            df['Relative Candles Phase'] = phases

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
            df['On Balance Volume'] = df.ta.obv()

            # 4. Weis Waves
            def calculate_weis_waves(direction_series, vol_s):
                # direction_series: 1 for UP, -1 for DOWN, 0 for Neutral
                # We replace 0 with NaN and ffill to maintain previous wave direction
                direction = direction_series.replace(0, np.nan).ffill().fillna(1)
                
                # Identify blocks of consecutive direction
                block_id = (direction != direction.shift(1)).cumsum()
                
                # Group by block and cumsum volume
                waves = vol_s.groupby(block_id).cumsum()
                
                return waves, direction

            # Standard Weis Waves: Direction based on Candle Color (Close > Open)
            # If Close == Open, 0
            std_dir = np.sign(df['Close'] - df['Open'])
            df['Weis Waves Volume'], df['Weis Waves Direction'] = calculate_weis_waves(std_dir, df['Volume'])

            # Heikin Ashi Weis Waves: Direction based on HA Candle Color
            # Note: We calculated HA columns earlier
            ha_dir = np.sign(df['Heikin Ashi Close'] - df['Heikin Ashi Open'])
            df['Heikin Ashi Weis Waves Volume'], _ = calculate_weis_waves(ha_dir, df['Volume'])

            # Relative Weis Waves: Direction based on Relative Candles Phase
            # phases is already 1 or -1
            rel_dir = pd.Series(phases, index=df.index)
            df['Relative Weis Waves Volume'], _ = calculate_weis_waves(rel_dir, df['Volume'])
            
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
            # 5, 7, 9.
            # Custom implementation for robustness and S/R logic
            
            def get_fractals(high, low, n):
                # Center index is offset. n=5 -> offset=2.
                # We need to look forward, so we can only know fractal N/2 candles ago.
                # But for indicators, we often repaint or flag it when confirmed.
                # Repainting is bad for trading.
                # BUT, "Closest Support... based on Williams Fractals 7".
                # If we are at time T, we can only see fractals confirmed up to T-(n//2).
                # I will calculate fractals based on available data. The most recent n//2 values will be NaN.
                
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
            for n_val in [5, 7, 9]:
                fh, fl = get_fractals(df['High'], df['Low'], n_val)
                # Store the Price if it matches either, else NaN.
                merged = fh.fillna(fl)
                df[f'Williams Fractals {n_val}'] = merged


            # 9. Closest Support/Resistance (Using Williams Fractals 9)
            # Strategy: Separate Support (Low Fractals) and Resistance (High Fractals) pools.
            # Support Pool = All Highs/Lows of confirmed Down Fractals
            # Resistance Pool = All Highs/Lows of confirmed Up Fractals
            # Actually, standard S/R uses the fractal price itself:
            # Down Fractal Low = Support level
            # Up Fractal High = Resistance level
            
            fh9, fl9 = get_fractals(df['High'], df['Low'], 9)
            fh9_vals = fh9.values
            fl9_vals = fl9.values
            
            highs = df['High'].values
            lows = df['Low'].values
            closes = df['Close'].values
            n = len(df)
            
            supports = [None] * n
            resistances = [None] * n
            
            # Pools of confirmed levels
            support_pool = []
            resistance_pool = []
            
            offset = 9 // 2 # 4
            
            body_bottom = np.minimum(df['Open'].values, df['Close'].values)
            body_top = np.maximum(df['Open'].values, df['Close'].values)
            
            for i in range(n):
                # 1. Update pools with fractals confirmed at index i
                # A fractal at conf_idx is confirmed when we have offset candles after it.
                conf_idx = i - offset
                
                if conf_idx >= 0:
                    # New Resistance confirmed (High Fractal) -> Use Body Top
                    if not np.isnan(fh9_vals[conf_idx]):
                        resistance_pool.append(body_top[conf_idx])
                    
                    # New Support confirmed (Low Fractal) -> Use Body Bottom
                    if not np.isnan(fl9_vals[conf_idx]):
                        support_pool.append(body_bottom[conf_idx])
                
                current_price = closes[i]
                
                # 2. Find Closest Support (Max Level < Price)
                below = [l for l in support_pool if l < current_price]
                if below:
                    supports[i] = max(below)
                else:
                    # Fallback to older levels if broken? 
                    # user said: "If price breaks a support, the closest support should immediately be the next fractal down."
                    # This is naturally handled by max(below) if we keep all historical levels.
                    supports[i] = None
                    
                # 3. Find Closest Resistance (Min Level > Price)
                above = [l for l in resistance_pool if l > current_price]
                if above:
                    resistances[i] = min(above)
                else:
                    resistances[i] = None

            df['Closest Support'] = supports
            df['Closest Resistance'] = resistances

            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}", exc_info=True)
            return df

    async def fetch_and_publish(self, symbol: str, timeframe: str):
        """Fetch data with caching support and retry logic"""
        retry_key = (symbol, timeframe)
        
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
                
                # Update Analysis Object
                analysis = await AnalysisManager.get_analysis(symbol)
                await analysis.update_section("market_data", df_with_ind, timeframe)

                # Serialize for event bus
                columns = df_with_ind.columns.tolist()
                values = df_with_ind.replace({np.nan: None}).values.tolist()
                
                data = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": float(df_cache['timestamp'].values[-1]),
                    "latest_close": float(df_cache['Close'].iloc[-1]),
                    "agent": self.name,
                    "from_cache": True
                }
                self.log_market_action("FETCH_DATA_CACHE", symbol, {"timeframe": timeframe})
                await event_bus.publish(EventType.MARKET_DATA, data)
                self.processed_count += 1
                
                # Reset retry counter on successful cache hit
                if retry_key in self.retry_tracker:
                    del self.retry_tracker[retry_key]
                    
                return
        
        # Get current retry count
        retry_count = self.retry_tracker.get(retry_key, 0)
        
        # Fetch fresh data with retry logic
        try:
            if not self.is_running:
                return
                
            logger.debug(f"Fetching {symbol} {timeframe} (attempt {retry_count + 1}/{self.max_retries + 1})")
            
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            
            if not ohlcv or not self.is_running:
                raise ValueError(f"Empty OHLCV data returned for {symbol} {timeframe}")
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df_with_ind = self.calculate_indicators(df)
            
            # Update Analysis Object
            analysis = await AnalysisManager.get_analysis(symbol)
            await analysis.update_section("market_data", df_with_ind, timeframe)

            columns = df_with_ind.columns.tolist()
            values = df_with_ind.replace({np.nan: None}).values.tolist()
            
            data = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": df_with_ind['timestamp'].iloc[-1],
                "latest_close": float(df_with_ind['Close'].iloc[-1]),
                "agent": self.name,
                "from_cache": False
            }
            
            self.log_market_action("FETCH_DATA_LIVE", symbol, {"timeframe": timeframe})
            await event_bus.publish(EventType.MARKET_DATA, data)
            self.processed_count += 1

            # Persist to DB/cache -> Only persist RAW OHLCV to save space and re-calc on load?
            # Or persist everything?
            # `persist_candles` currently only handles OHLCV logic. 
            # I will keep persisting only OHLCV to maintain schema compatibility.
            self.persist_candles(symbol, timeframe, ohlcv)
            
            # Success - reset retry counter
            if retry_key in self.retry_tracker:
                logger.info(f"Successfully fetched {symbol} {timeframe} after {retry_count + 1} attempts")
                del self.retry_tracker[retry_key]
            
        except Exception as e:
            # During shutdown, some exchange methods might fail with attribute errors
            # which we can safely ignore if the agent is stopping.
            if not self.is_running:
                return
            
            # Increment retry counter
            self.retry_tracker[retry_key] = retry_count + 1
            
            # Check if we should retry
            if self.retry_tracker[retry_key] <= self.max_retries:
                # Calculate delay with exponential backoff
                delay_index = min(retry_count, len(self.retry_delays) - 1)
                delay = self.retry_delays[delay_index]
                
                logger.warning(
                    f"Error fetching {symbol} {timeframe} (attempt {retry_count + 1}/{self.max_retries + 1}): {e}. "
                    f"Retrying in {delay}s..."
                )
                
                # Wait before retry
                await asyncio.sleep(delay)
                
                # Retry the fetch
                await self.fetch_and_publish(symbol, timeframe)
            else:
                # Max retries exceeded
                logger.error(
                    f"Failed to fetch {symbol} {timeframe} after {self.max_retries + 1} attempts. "
                    f"Last error: {e}. Will retry in next cycle."
                )
                
                # Reset counter so it can retry in the next main loop cycle
                del self.retry_tracker[retry_key]
                
                await event_bus.publish(EventType.ERROR, {
                    "agent": self.name, 
                    "symbol": symbol, 
                    "timeframe": timeframe,
                    "error": str(e),
                    "retry_count": retry_count + 1
                })

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
        multipliers = {'m': 1, 'h': 60, 'd': 1440, 'w': 10080, 'M': 43200}
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
