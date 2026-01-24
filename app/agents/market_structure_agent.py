import asyncio
import pandas as pd
import numpy as np
import time
import logging
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager

logger = logging.getLogger("MarketStructureAgent")

class MarketStructureAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MarketStructureAgent")
        self.processed_count = 0

    async def run_loop(self):
        """Subscribe to market data updates and react"""
        event_bus.subscribe(EventType.MARKET_DATA, self.handle_market_data)
        
        # Keep alive - base class run_loop is abstract, but we just need to wait here
        # as we are event-driven
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_market_data(self, data: Dict[str, Any]):
        """React to market data updates for a symbol + timeframe"""
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        logger.info(f"Received market data event for {symbol} {timeframe}")
        
        if not symbol or not timeframe:
            return

        try:
            # 1. Access Analysis Object
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            
            # 2. Get DataFrame from market_data
            df = analysis_data.get("market_data", {}).get(timeframe)
            
            if df is None:
                logger.warning(f"DataFrame for {symbol} {timeframe} is None in AnalysisObject")
                return
            
            if not isinstance(df, pd.DataFrame):
                logger.warning(f"Data for {symbol} {timeframe} is not a DataFrame: {type(df)}")
                return

            if len(df) < 2:
                logger.warning(f"Insufficient data in DataFrame for {symbol} {timeframe}: {len(df)} rows")
                return

            # 3. Calculate Market Structure fields
            # We compare the last two confirmed candles (or latest vs prev)
            # Latest candle is usually index -1, previous is -2
            curr = df.iloc[-1]
            prev = df.iloc[-2]

            # Highs/Lows
            highs_state = "HIGHER" if curr['High'] > prev['High'] else ("LOWER" if curr['High'] < prev['High'] else "NEUTRAL")
            lows_state = "HIGHER" if curr['Low'] > prev['Low'] else ("LOWER" if curr['Low'] < prev['Low'] else "NEUTRAL")

            # Pivot Points
            curr_pivot = curr.get('Pivot Points')
            prev_pivot = prev.get('Pivot Points')
            pivot_state = "NEUTRAL"
            if curr_pivot is not None and prev_pivot is not None:
                pivot_state = "UP" if curr_pivot > prev_pivot else ("DOWN" if curr_pivot < prev_pivot else "NEUTRAL")

            # EMAs (Using EMA 21 as benchmark)
            ema_col = 'Exponential Moving Average 21'
            ema_state = "NEUTRAL"
            if ema_col in df.columns:
                curr_ema = curr[ema_col]
                prev_ema = prev[ema_col]
                if not pd.isna(curr_ema) and not pd.isna(prev_ema):
                    ema_state = "UP" if curr_ema > prev_ema else ("DOWN" if curr_ema < prev_ema else "NEUTRAL")

            # ADX State
            latest_adx = curr.get('Average Directional Index')
            adx_state = "NEUTRAL"
            if latest_adx is not None:
                adx_state = "TRENDING" if latest_adx >= 23 else "NEUTRAL"

            # 4. Update Analysis Object
            updates = {
                "highs": highs_state,
                "lows": lows_state,
                "pivot_points": pivot_state,
                "emas": ema_state,
                "adx": adx_state,
                "last_updated": int(time.time())
            }
            
            await analysis.update_section("market_structure", updates, timeframe)
            
            self.processed_count += 1
            logger.info(f"Updated market structure for {symbol} {timeframe}")

        except Exception as e:
            logger.error(f"Error in MarketStructureAgent for {symbol} {timeframe}: {e}", exc_info=True)
