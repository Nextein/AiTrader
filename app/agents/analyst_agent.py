import asyncio
import time
import logging
import pandas as pd
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
from app.core.config import settings
from app.core.prompt_loader import PromptLoader
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger("AnalystAgent")

class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="AnalystAgent")
        self.llm = ChatOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
            model=settings.OLLAMA_MODEL,
            temperature=0
        )
        self.analyst_prompt = PromptLoader.load("analyst", "top_down_analysis")
        self.analyst_chain = self.analyst_prompt | self.llm | JsonOutputParser()

    async def run_loop(self):
        # Triggered by analysis updates (overall regime or major strategy update)
        event_bus.subscribe(EventType.ANALYSIS_UPDATE, self.handle_analysis_update)
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_analysis_update(self, data: Dict[str, Any]):
        if not self.is_running or not self.is_active:
            return
            
        # We only run overall analysis periodically or on major triggers
        if data.get("timeframe") != "overall" and data.get("section") not in ["market_regime", "ema_strategy", "cycles_strategy"]:
            return
            
        symbol = data.get("symbol")
        if not symbol: return

        try:
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            
            # 1. OBV Divergence Check (15m timeframe as requested)
            obv_div = self._check_obv_divergence(analysis_data, "15m")
            
            # 2. Gather top-down data
            top_down_data = {
                "symbol": symbol,
                "overall_regime": analysis_data.get("market_regime", {}).get("overall", "UNKNOWN"),
                "timeframe_data": {},
                "obv_divergence_15m": obv_div
            }
            
            for tf in settings.TIMEFRAMES:
                top_down_data["timeframe_data"][tf] = {
                    "regime": analysis_data.get("market_regime", {}).get(tf),
                    "structure": analysis_data.get("market_structure", {}).get(tf),
                    "ema_signal": analysis_data.get("ema_strategy", {}).get(tf, {}).get("analysis", {}).get("signal"),
                    "cycles_signal": analysis_data.get("cycles_strategy", {}).get(tf, {}).get("analysis", {}).get("signal"),
                    "sfp_signal": analysis_data.get("sfp_strategy", {}).get(tf, {}).get("analysis", {}).get("signal"),
                }

            # 3. LLM Synthesis
            res = await self.analyst_chain.ainvoke(top_down_data)
            
            # 4. Update Analysis Object
            analysis_update = {
                "summary": res.get("summary"),
                "primary_bias": res.get("primary_bias", "NEUTRAL").upper(),
                "top_setups": res.get("top_setups", []),
                "obv_divergence": obv_div,
                "last_updated": int(time.time())
            }
            
            await analysis.update_section("unified_analysis", analysis_update)
            
            self.processed_count += 1
            logger.info(f"Updated Unified Analysis for {symbol}: {analysis_update['primary_bias']}")
            
            # Publish completion event for Governor to move to next symbol
            await event_bus.publish(EventType.ANALYSIS_COMPLETED, {
                "symbol": symbol,
                "agent": self.name,
                "timestamp": int(time.time()),
                "bias": analysis_update['primary_bias']
            })

        except Exception as e:
            logger.error(f"Error in AnalystAgent for {symbol}: {e}", exc_info=True)

    def _check_obv_divergence(self, analysis_data: Dict[str, Any], timeframe: str) -> str:
        """Heuristic for OBV Divergence detection on specified timeframe"""
        df = analysis_data.get("market_data", {}).get(timeframe)
        if df is None or len(df) < 20 or 'On Balance Volume' not in df.columns:
            return "UNKNOWN"
            
        recent = df.tail(20)
        # Check if price is making Higher Highs while OBV is making Lower Highs (Bearish Div)
        # Check if price is making Lower Lows while OBV is making Higher Lows (Bullish Div)
        
        p = recent['Close'].values
        obv = recent['On Balance Volume'].values
        
        # Simple slope comparison
        p_slope, _ = np.polyfit(np.arange(len(p)), p, 1)
        obv_slope, _ = np.polyfit(np.arange(len(obv)), obv, 1)
        
        if p_slope > 0 and obv_slope < 0: return "BEARISH_DIVERGENCE"
        if p_slope < 0 and obv_slope > 0: return "BULLISH_DIVERGENCE"
        
        return "NEUTRAL"
