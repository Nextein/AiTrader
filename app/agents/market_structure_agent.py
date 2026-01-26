import asyncio
import pandas as pd
import numpy as np
import time
import logging
from typing import Dict, Any, Optional
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from app.core.config import settings
from app.core.prompt_loader import PromptLoader

logger = logging.getLogger("MarketStructureAgent")

class MarketStructureAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MarketStructureAgent")
        self.processed_count = 0
        self.llm = ChatOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
            model=settings.OLLAMA_MODEL,
            temperature=0
        )
        self.ema_prompt = PromptLoader.load("market_structure", "ema_analysis")
        self.ema_chain = self.ema_prompt | self.llm | JsonOutputParser()

    async def run_loop(self):
        """Subscribe to value areas updates and react"""
        event_bus.subscribe(EventType.VALUE_AREAS_UPDATED, self.handle_market_data)
        
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_market_data(self, data: Dict[str, Any]):
        """React to value areas updates for a symbol + timeframe"""
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        logger.info(f"Received value areas update for {symbol} {timeframe}")
        
        if not symbol or not timeframe:
            return

        try:
            # 1. Access Analysis Object
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            
            # 2. Get DataFrame from market_data
            df = analysis_data.get("market_data", {}).get(timeframe)
            
            if df is None or not isinstance(df, pd.DataFrame) or len(df) < 50:
                logger.warning(f"Insufficient data for {symbol} {timeframe}")
                return

            # 3. Calculate Market Structure fields
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

            # Value Areas Trend Analysis
            # Look at the last 3 "windows" of 100 bars each, shifted by 10 bars
            poc1 = self._calculate_poc(df, lookback=100, offset=0)
            poc2 = self._calculate_poc(df, lookback=100, offset=10)
            poc3 = self._calculate_poc(df, lookback=100, offset=20)
            
            va_state = "NEUTRAL"
            if poc1 and poc2 and poc3:
                if poc1 > poc2 > poc3:
                    va_state = "ASCENDING"
                elif poc1 < poc2 < poc3:
                    va_state = "DESCENDING"
                else:
                    va_state = "NEUTRAL"

            # EMAs analysis via LLM
            ema_cols = [
                'Exponential Moving Average 9',
                'Exponential Moving Average 21',
                'Exponential Moving Average 55',
                'Exponential Moving Average 144',
                'Exponential Moving Average 252'
            ]
            
            curr_emas = {col: curr[col] for col in ema_cols if col in df.columns}
            prev_emas = {col: prev[col] for col in ema_cols if col in df.columns}
            
            emas_in_order = "NEUTRAL"
            emas_fanning = "NEUTRAL"
            
            if len(curr_emas) == 5 and not any(pd.isna(v) for v in curr_emas.values()):
                try:
                    res = await self.ema_chain.ainvoke({
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "market_context": self.format_market_context(
                            df, 
                            window=50,
                            columns=['Open', 'High', 'Low', 'Close'] + ema_cols
                        ),
                        "analysis_summary": {
                            "highs_state": highs_state,
                            "lows_state": lows_state,
                            "pivot_state": pivot_state,
                            "va_state": va_state
                        }
                    })
                    emas_in_order = res.get("emas_in_order", "NEUTRAL").upper()
                    emas_fanning = res.get("emas_fanning", "NEUTRAL").upper()
                    
                    if emas_in_order not in ["ASCENDING", "DESCENDING", "NEUTRAL"]:
                        emas_in_order = "NEUTRAL"
                    if emas_fanning not in ["EXPANDING", "NEUTRAL"]:
                        emas_fanning = "NEUTRAL"
                except Exception as e:
                    logger.error(f"LLM Error in MarketStructureAgent for {symbol}: {e}")

            # ADX State
            latest_adx = curr.get('Average Directional Index')
            adx_state = "TRENDING" if latest_adx is not None and latest_adx >= 23 else "NEUTRAL"
            
            # Weis Waves Analysis
            weis_dir = curr.get('Weis Waves Direction', 0)
            weis_vol = curr.get('Weis Waves Volume', 0)
            weis_state = "UP" if weis_dir > 0 else ("DOWN" if weis_dir < 0 else "NEUTRAL")
            
            # Relative Candle Phase
            rel_phase_val = curr.get('Relative Candles Phase', 0)
            rel_phase = "UP" if rel_phase_val == 1 else ("DOWN" if rel_phase_val == -1 else "NEUTRAL")
            
            # Global vs Local (Simplification: using different lookbacks)
            local_poc = poc1
            global_poc = self._calculate_poc(df, lookback=min(len(df), 300), offset=0)
            structure_scale = "GLOBAL_ALIGNED" if (va_state == "ASCENDING" and curr['Close'] > global_poc) else "LOCAL_ONLY"

            # 4. Update Analysis Object
            updates = {
                "highs": highs_state,
                "lows": lows_state,
                "value_areas": va_state,
                "pivot_points": pivot_state,
                "emas_in_order": emas_in_order,
                "emas_fanning": emas_fanning,
                "adx": adx_state,
                "weis_waves": {"direction": weis_state, "volume": float(weis_vol)},
                "relative_phase": rel_phase,
                "structure_scale": structure_scale,
                "last_updated": int(time.time())
            }
            
            await analysis.update_section("market_structure", updates, timeframe)
            
            # 5. LLM Reasoning for structure (Brief summary)
            # (Optional: can add more fields if needed)
            await event_bus.publish(EventType.ANALYSIS_UPDATE, {
                "symbol": symbol,
                "timeframe": timeframe,
                "section": "market_structure",
                "agent": self.name,
                "timestamp": int(time.time())
            })

            self.processed_count += 1
            self.log_market_action("UPDATE_STRUCTURE", symbol, {"timeframe": timeframe, "va_state": va_state})
            logger.info(f"Updated market structure for {symbol} {timeframe} (VA: {va_state})")

        except Exception as e:
            logger.error(f"Error in MarketStructureAgent for {symbol} {timeframe}: {e}", exc_info=True)

    def _calculate_poc(self, df: pd.DataFrame, lookback: int, offset: int = 0) -> Optional[float]:
        """Calculates POC for a specific window in the dataframe"""
        try:
            end = len(df) - offset
            start = max(0, end - lookback)
            if end <= start:
                return None
            
            subset = df.iloc[start:end]
            num_bins = 100
            
            highs = subset['High'].values
            lows = subset['Low'].values
            volumes = subset['Volume'].values

            min_p = np.min(lows)
            max_p = np.max(highs)
            
            if max_p == min_p: return None

            bin_size = (max_p - min_p) / num_bins
            profile = np.zeros(num_bins)

            for i in range(len(subset)):
                h, l, v = highs[i], lows[i], volumes[i]
                start_bin = int((l - min_p) / bin_size)
                end_bin = int((h - min_p) / bin_size)
                start_bin = max(0, min(num_bins - 1, start_bin))
                end_bin = max(0, min(num_bins - 1, end_bin))
                
                num_bins_covered = (end_bin - start_bin) + 1
                vol_per_bin = v / num_bins_covered if num_bins_covered > 0 else 0
                for b in range(start_bin, end_bin + 1):
                    profile[b] += vol_per_bin

            poc_index = np.argmax(profile)
            poc = float(min_p + (poc_index + 0.5) * bin_size)
            return poc
        except Exception:
            return None
