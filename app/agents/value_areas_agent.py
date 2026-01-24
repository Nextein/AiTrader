import asyncio
import pandas as pd
import numpy as np
import logging
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

            # Calculate Value Areas using fixed number of bins (e.g., 24 for intraday)
            calc_result = self.calculate_value_areas(df)
            
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
            
            # Naked POC Tracking
            # A POC is naked if price leaves the VA without touching the POC again
            # We track if current POC has been touched by price since it was established
            naked = True
            # Check price action since स्थापित? This requires history.
            # Simplified: if current price is at POC, it's not naked.
            if latest_low <= poc <= latest_high:
                naked = False
            
            va_data['naked_poc'] = naked

            # Update Analysis Object
            # We follow the schema by separating these two sections
            await analysis.update_section("value_areas", va_data, timeframe)
            await analysis.update_section("vpvr", vpvr_data, timeframe)
            
            self.processed_count += 1

        except Exception as e:
            logger.error(f"Error in ValueAreasAgent for {symbol}: {e}", exc_info=True)

    def calculate_value_areas(self, df: pd.DataFrame, num_bins: int = 50) -> Optional[Dict[str, Any]]:
        try:
            # We use the entire lookback for the profile (e.g., last 100 candles)
            lookback = min(100, len(df))
            subset = df.iloc[-lookback:]
            
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

            # Value Area (70% Volume)
            total_vol = np.sum(profile)
            target_vol = total_vol * 0.7
            
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

