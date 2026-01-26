import pandas as pd
import numpy as np
import asyncio
import time
import logging
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager

logger = logging.getLogger("SupportResistanceAgent")

class SupportResistanceAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="SupportResistanceAgent")
        self.last_processed = {} # {symbol_tf: timestamp}

    async def run_loop(self):
        # Listen for analysis updates from MarketStructure and ValueAreas
        event_bus.subscribe(EventType.ANALYSIS_UPDATE, self.handle_analysis_update)
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_analysis_update(self, data: Dict[str, Any]):
        if not self.is_running or not self.is_active:
            return
            
        # We need both structure and value areas to look for confluence
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        
        if not symbol or not timeframe:
            return

        try:
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            
            # Check if we have required data
            df = analysis_data.get("market_data", {}).get(timeframe)
            if df is None: return
            
            va = analysis_data.get("value_areas", {}).get(timeframe, {})
            ms = analysis_data.get("market_structure", {}).get(timeframe, {})
            
            ts = df['timestamp'].iloc[-1]
            lookup_key = f"{symbol}_{timeframe}"
            if self.last_processed.get(lookup_key) == ts:
                return
            self.last_processed[lookup_key] = ts

            # 1. Consolidate Levels
            levels = []
            
            # Value Area Edges
            if va.get("vah"): levels.append({"price": va["vah"], "type": "RESISTANCE", "source": "VAH"})
            if va.get("val"): levels.append({"price": va["val"], "type": "SUPPORT", "source": "VAL"})
            if va.get("poc"): levels.append({"price": va["poc"], "type": "CONFLUENCE", "source": "POC"})
            
            # Williams Fractals (Already in DF)
            curr = df.iloc[-1]
            closest_supp = curr.get('Closest Support')
            closest_res = curr.get('Closest Resistance')
            
            if closest_supp: levels.append({"price": float(closest_supp), "type": "SUPPORT", "source": "FRACTAL"})
            if closest_res: levels.append({"price": float(closest_res), "type": "RESISTANCE", "source": "FRACTAL"})
            
            # 2. Confluence Detection
            confluences = []
            price_now = curr['Close']
            
            # Sort and group levels that are very close (within 0.1%)
            sorted_levels = sorted(levels, key=lambda x: x["price"])
            for i in range(len(sorted_levels)):
                for j in range(i + 1, len(sorted_levels)):
                    p1 = sorted_levels[i]["price"]
                    p2 = sorted_levels[j]["price"]
                    if abs(p1 - p2) / p1 < 0.001:
                        confluences.append({
                            "price": (p1 + p2) / 2,
                            "sources": [sorted_levels[i]["source"], sorted_levels[j]["source"]],
                            "strength": 2
                        })

            # 3. Global vs Local (Multi-Timeframe check)
            global_levels = analysis_data.get("key_levels", {}) # From ValueAreasAgent (D/W/M POCs)
            
            # 4. Update Analysis Object
            sr_data = {
                "current_levels": levels,
                "confluences": confluences,
                "global_context": global_levels,
                "closest_support": closest_supp,
                "closest_resistance": closest_res,
                "last_updated": int(time.time())
            }
            
            await analysis.update_section("support_resistance", sr_data, timeframe)
            
            self.processed_count += 1
            logger.info(f"Updated S/R analysis for {symbol} {timeframe}")

        except Exception as e:
            logger.error(f"Error in SupportResistanceAgent for {symbol}: {e}", exc_info=True)
