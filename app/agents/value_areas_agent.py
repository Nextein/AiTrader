import asyncio
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager

logger = logging.getLogger("ValueAreasAgent")

class ValueAreasAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ValueAreasAgent")
        self.last_timestamps = {} # {symbol_tf: timestamp}
        self.states = {} # {symbol_tf: state}
        self.poc_history = {} # {symbol_tf: [pocs]} for naked poc tracking
        
        # New prompts for internal/external analysis reference
        self.value_areas_prompt = """
        You are an expert market profile analyst. Your task is to analyze Value Areas (VAH, VAL, POC).
        - VAH (Value Area High): The upper boundary of the range where 70% of volume occurred.
        - VAL (Value Area Low): The lower boundary of the range where 70% of volume occurred.
        - POC (Point of Control): The price level with the highest volume in the period.
        Analyzed state should consider if price is 'IN', 'OUT' (above/below), 'SFP' (Swing Failure Pattern), 'FA' (Failed Auction), or 'RETEST' (of POC).
        """
        
        self.vpvr_prompt = """
        You are an expert volume profile analyst. Your task is to analyze the Visible Range Volume Profile (VPVR).
        The VPVR provides a distribution of volume across price levels for the visible bars on the chart.
        High Volume Nodes (HVN) represent areas of high interest/consolidation, while Low Volume Nodes (LVN) represent areas of fast price movement/rejection.
        """

    async def run_loop(self):
        event_bus.subscribe(EventType.MARKET_DATA, self.on_market_data)
        while self.is_running:
            await asyncio.sleep(1)

    async def on_market_data(self, data: Dict[str, Any]):
        if not self.is_running:
            return

        symbol = data.get("symbol")
        timeframe = data.get("timeframe", "1h")
        ts = data.get("timestamp")

        lookup_key = f"{symbol}_{timeframe}"
        if self.last_timestamps.get(lookup_key) == ts:
            return
        self.last_timestamps[lookup_key] = ts

        try:
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            df = analysis_data.get("market_data", {}).get(timeframe)

            if df is None or not isinstance(df, pd.DataFrame) or len(df) < 50:
                return

            # Calculate Value Areas with course-specific granularity (188 rows)
            # Value Area Volume is usually 68-70%, we use 68 as per memo.md
            calc_result = self.calculate_value_areas(df, num_bins=188, va_pct=0.68)
            
            if not calc_result:
                return

            # Separate VPVR and Value Area data
            va_data = {
                "poc": calc_result['poc'],
                "vah": calc_result['vah'],
                "val": calc_result['val'],
                "last_updated": calc_result['last_updated']
            }
            
            vpvr_data = {
                "data": calc_result.get("volume_profile", []),
                "last_updated": calc_result['last_updated']
            }

            # Determine State
            latest_close = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            latest_high = df['High'].iloc[-1]
            latest_low = df['Low'].iloc[-1]
            
            vah = va_data['vah']
            val = va_data['val']
            poc = va_data['poc']

            state = "IN_VALUE_AREA"
            if latest_close > vah:
                state = "ABOVE_VALUE_AREA"
            elif latest_close < val:
                state = "BELOW_VALUE_AREA"

            # Swing Failure Pattern (SFP)
            # High above VAH but close inside
            if latest_high > vah and latest_close <= vah:
                state = "SWING_FAILURE_PATTERN"
            # Low below VAL but close inside
            elif latest_low < val and latest_close >= val:
                state = "SWING_FAILURE_PATTERN"

            # Failed Auction (Spans multiple candles)
            # Check last 3 candles: if any of them were ABOVE_VALUE_AREA but current is back in
            was_above = False
            for i in range(2, 5): # check -2, -3, -4
                if i <= len(df):
                    h = df['High'].iloc[-i]
                    c = df['Close'].iloc[-i]
                    if c > vah:
                        was_above = True
                        break
            
            if was_above and latest_close <= vah and state != "SWING_FAILURE_PATTERN":
                state = "FAILED_AUCTION"

            # Retest of POC
            # If price was away from POC and now touching it
            if (prev_close > poc and latest_low <= poc) or (prev_close < poc and latest_high >= poc):
                state = "RETEST_OF_POC"

            va_data['state'] = state
            
            # Naked POC Tracking (Refined)
            # A POC is naked if price leaves and hasn't touched it since.
            # We track historical POCs and check if current price action invalidates them.
            naked = self._is_poc_naked(df, poc)
            
            va_data['naked_poc'] = naked

            # Linear Regression on POC (Trend Detection)
            va_data['poc_slope'] = self._calculate_poc_slope(df)

            # Update Analysis Object
            # We follow the schema by separating these two sections
            await analysis.update_section("value_areas", va_data, timeframe)
            await analysis.update_section("vpvr", vpvr_data, timeframe)
            
            self.processed_count += 1
            self.log_market_action("CALCULATE_VALUE_AREAS", symbol, {"timeframe": timeframe, "state": state, "poc": va_data['poc']})
            logger.info(f"Updated value areas and VPVR for {symbol} {timeframe}")

            # Notify that value areas are updated so market structure can proceed
            await event_bus.publish(EventType.VALUE_AREAS_UPDATED, {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": ts
            })

            # --- Key Levels Calculation (Daily, Weekly, Monthly POCs Above/Below) ---
            # We use available timeframes to find historical POC levels
            key_levels = {
                "daily_poc_above": None,
                "daily_poc_below": None,
                "weekly_poc_above": None,
                "weekly_poc_below": None,
                "monthly_poc_above": None,
                "monthly_poc_below": None
            }
            
            latest_price = latest_close
            
            # 1. Daily POCs from 1h data (preferred) or 1d data
            df_1h = analysis_data.get("market_data", {}).get("1h")
            if df_1h is not None and len(df_1h) > 20:
                daily_pocs = self._find_period_pocs(df_1h, 'D')
                above, below = self._get_closest_from_list(latest_price, daily_pocs)
                key_levels["daily_poc_above"] = above
                key_levels["daily_poc_below"] = below
            
            # 2. Weekly POCs from 1d data
            df_1d = analysis_data.get("market_data", {}).get("1d")
            if df_1d is not None and len(df_1d) > 10:
                weekly_pocs = self._find_period_pocs(df_1d, 'W')
                above, below = self._get_closest_from_list(latest_price, weekly_pocs)
                key_levels["weekly_poc_above"] = above
                key_levels["weekly_poc_below"] = below
                
            # 3. Monthly POCs from 1w data or 1d data
            df_1w = analysis_data.get("market_data", {}).get("1w")
            if df_1w is not None and len(df_1w) > 4:
                monthly_pocs = self._find_period_pocs(df_1w, 'M')
                above, below = self._get_closest_from_list(latest_price, monthly_pocs)
                key_levels["monthly_poc_above"] = above
                key_levels["monthly_poc_below"] = below
            elif df_1d is not None and len(df_1d) > 20:
                monthly_pocs = self._find_period_pocs(df_1d, 'M')
                above, below = self._get_closest_from_list(latest_price, monthly_pocs)
                key_levels["monthly_poc_above"] = above
                key_levels["monthly_poc_below"] = below

            await analysis.update_section("key_levels", key_levels)
            # -----------------------------------------------------------------------

        except Exception as e:
            logger.error(f"Error in ValueAreasAgent for {symbol}: {e}", exc_info=True)

    def _find_period_pocs(self, df: pd.DataFrame, period: str) -> List[float]:
        """Resamples DF and calculates POC for each period"""
        try:
            # Basic check
            if df is None or df.empty:
                return []
            
            # Ensure we have a datetime index for groupby
            if not isinstance(df.index, pd.DatetimeIndex):
                if 'timestamp' in df.columns:
                    temp_df = df.set_index(pd.to_datetime(df['timestamp'], unit='ms'))
                else:
                    return []
            else:
                temp_df = df

            pocs = []
            # Group by period
            groups = temp_df.groupby(pd.Grouper(freq=period))
            for _, group in groups:
                if len(group) < 1:
                    continue
                # Calculate POC for this specific group
                group_res = self.calculate_value_areas(group, num_bins=100, lookback=len(group))
                if group_res:
                    pocs.append(group_res['poc'])
            return pocs
        except Exception as e:
            logger.error(f"Error finding period POCs for {period}: {e}")
            return []

    def _get_closest_from_list(self, price: float, levels: List[float]):
        """Finds the closest level above and below the given price"""
        if not levels:
            return None, None
        
        above = [l for l in levels if l > price + 1e-9]
        below = [l for l in levels if l < price - 1e-9]
        
        return (min(above) if above else None), (max(below) if below else None)

    def calculate_value_areas(self, df: pd.DataFrame, num_bins: int = 188, va_pct: float = 0.68, lookback: Optional[int] = None) -> Optional[Dict[str, Any]]:
        try:
            if lookback is None:
                lookback = 100
                
            actual_lookback = min(lookback, len(df))
            subset = df.iloc[-actual_lookback:]
            
            prices = subset['Close'].values
            volumes = subset['Volume'].values
            highs = subset['High'].values
            lows = subset['Low'].values

            min_p = np.min(lows)
            max_p = np.max(highs)
            
            if max_p == min_p: return None

            bin_size = (max_p - min_p) / num_bins
            bins = np.linspace(min_p, max_p, num_bins + 1)
            profile = np.zeros(num_bins)

            # Distribute volume across bins hit by the candle range
            for i in range(len(subset)):
                h, l, v = highs[i], lows[i], volumes[i]
                # Identify which bins the candle covers
                start_bin = int((l - min_p) / bin_size)
                end_bin = int((h - min_p) / bin_size)
                
                # Boundary checks
                start_bin = max(0, min(num_bins - 1, start_bin))
                end_bin = max(0, min(num_bins - 1, end_bin))
                
                num_bins_covered = (end_bin - start_bin) + 1
                vol_per_bin = v / num_bins_covered
                
                for b in range(start_bin, end_bin + 1):
                    profile[b] += vol_per_bin

            # POC
            poc_index = np.argmax(profile)
            poc = float(bins[poc_index] + bin_size / 2)

            # Value Area (68% Volume as per memo.md)
            total_vol = np.sum(profile)
            target_vol = total_vol * va_pct
            
            va_low_idx = poc_index
            va_high_idx = poc_index
            current_vol = profile[poc_index]

            while current_vol < target_vol:
                # Check neighbors
                low_vol = profile[va_low_idx - 1] if va_low_idx > 0 else 0
                high_vol = profile[va_high_idx + 1] if va_high_idx < num_bins - 1 else 0
                
                if low_vol == 0 and high_vol == 0:
                    break
                    
                if low_vol >= high_vol:
                    current_vol += low_vol
                    va_low_idx -= 1
                else:
                    current_vol += high_vol
                    va_high_idx += 1

            vah = float(bins[va_high_idx] + bin_size)
            val = float(bins[va_low_idx])

            return {
                "poc": poc,
                "vah": vah,
                "val": val,
                "volume_profile": [
                    {"price": float(bins[i] + bin_size/2), "volume": float(profile[i])} 
                    for i in range(num_bins)
                ],
                "last_updated": int(asyncio.get_event_loop().time())
            }
        except Exception as e:
            logger.error(f"VP Calc Error: {e}")
            return None

    def _is_poc_naked(self, df: pd.DataFrame, poc: float) -> bool:
        """Checks if the POC has been touched by candles after its period"""
        # For simplicity, we check if the current candle range includes the POC
        # In a full implementation, we'd track historical POCs and check against all subsequent data.
        curr = df.iloc[-1]
        if curr['Low'] <= poc <= curr['High']:
            return False
        return True

    def _calculate_poc_slope(self, df: pd.DataFrame, lookback: int = 20) -> float:
        """Calculates the linear regression slope of multiple recent POCs"""
        pocs = []
        # Calculate POC for last N windows
        for i in range(lookback):
            idx = len(df) - i
            if idx < 50: break
            # Each 'POC' here is a localized POC
            res = self.calculate_value_areas(df.iloc[:idx], lookback=30)
            if res:
                pocs.append(res['poc'])
        
        if len(pocs) < 5: return 0.0
        
        # Simple slope of POCs
        pocs = pocs[::-1] # chronological
        y = np.array(pocs)
        x = np.arange(len(y))
        slope, _ = np.polyfit(x, y, 1)
        return float(slope)

