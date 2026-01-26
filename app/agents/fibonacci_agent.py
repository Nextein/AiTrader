import pandas as pd
import numpy as np
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager

logger = logging.getLogger("FibonacciAgent")

class FibonacciAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="FibonacciAgent")
        self.last_processed = {} # {symbol_tf: timestamp}

    async def run_loop(self):
        event_bus.subscribe(EventType.ANALYSIS_UPDATE, self.handle_analysis_update)
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_analysis_update(self, data: Dict[str, Any]):
        if not self.is_running or not self.is_active:
            return
            
        if data.get("section") != "market_structure":
            return
            
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        
        if not symbol or not timeframe:
            return

        try:
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            
            df = analysis_data.get("market_data", {}).get(timeframe)
            if df is None or len(df) < 50:
                return
                
            ts = df['timestamp'].iloc[-1]
            lookup_key = f"{symbol}_{timeframe}"
            if self.last_processed.get(lookup_key) == ts:
                return
            self.last_processed[lookup_key] = ts

            # 1. Identify Swing High/Low for Fibonacci
            # We use Williams Fractals or simple rolling extremes
            lookback = 100
            subset = df.iloc[-lookback:]
            swing_high = subset['High'].max()
            swing_low = subset['Low'].min()
            
            if swing_high == swing_low: return

            # 2. Calculate Retracement Levels
            diff = swing_high - swing_low
            
            # Standard Levels
            levels = {
                "0.0": swing_low,
                "0.236": swing_high - 0.236 * diff,
                "0.382": swing_high - 0.382 * diff,
                "0.5": swing_high - 0.5 * diff,
                "0.618": swing_high - 0.618 * diff,
                "0.786": swing_high - 0.786 * diff,
                "1.0": swing_high
            }
            
            # CC Channel (Chain Champion specialty)
            # 66.6% and 70.6%
            cc_channel = {
                "low": swing_high - 0.706 * diff,
                "high": swing_high - 0.666 * diff
            }

            # 3. Check for Confluence with current price
            curr_price = df['Close'].iloc[-1]
            in_cc_channel = cc_channel["low"] <= curr_price <= cc_channel["high"]
            
            # 4. Update Analysis Object
            fib_data = {
                "swing_high": float(swing_high),
                "swing_low": float(swing_low),
                "levels": levels,
                "cc_channel": cc_channel,
                "in_cc_channel": in_cc_channel,
                "last_updated": int(time.time())
            }
            
            await analysis.update_section("fibonacci", fib_data, timeframe)
            
            self.processed_count += 1
            logger.info(f"Updated Fibonacci analysis for {symbol} {timeframe}")

        except Exception as e:
            logger.error(f"Error in FibonacciAgent for {symbol}: {e}", exc_info=True)
