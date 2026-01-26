import asyncio
import pandas as pd
import numpy as np
import time
import logging
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
from app.core.config import settings
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from app.core.prompt_loader import PromptLoader

logger = logging.getLogger("RegimeDetection")

class RegimeDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="RegimeDetectionAgent")
        self.description = "Analyzes market structure and indicators to determine the current trading regime (Trending/Ranging)."
        self.tasks = [
            "Classify market regime per timeframe (1H, 15m, 5m)",
            "Identify candlestick phases (Phase 1, Phase -1, etc.)",
            "Synthesize per-timeframe regimes into an overall market bias",
            "Detect multi-cycle trends"
        ]
        self.responsibilities = [
            "Providing accurate regime classification to strategy agents",
            "Ensuring higher-timeframe context is respected in lower-timeframe analysis",
            "Alerting the system of major regime shifts"
        ]
        self.prompts = [
            "regime_detection/phase",
            "regime_detection/regime_decision",
            "regime_detection/overall_regime"
        ]
        
        self.llm = ChatOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
            model=settings.OLLAMA_MODEL,
            temperature=0
        )
        
        # Phase prompt for higher timeframes
        self.phase_prompt = PromptLoader.load("regime_detection", "phase")
        self.phase_chain = self.phase_prompt | self.llm | StrOutputParser()

        # Regime decision prompt
        self.regime_prompt = PromptLoader.load("regime_detection", "regime_decision")
        self.regime_chain = self.regime_prompt | self.llm | JsonOutputParser()

        # Overall regime prompt
        self.overall_prompt = PromptLoader.load("regime_detection", "overall_regime")
        self.overall_chain = self.overall_prompt | self.llm | JsonOutputParser()

    async def run_loop(self):
        """Triggered by ANALYSIS_UPDATE from MarketStructureAgent"""
        event_bus.subscribe(EventType.ANALYSIS_UPDATE, self.handle_analysis_update)
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_analysis_update(self, data: Dict[str, Any]):
        if data.get("section") != "market_structure":
            return
        
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        logger.info(f"RegimeDetectionAgent: Triggered for {symbol} {timeframe}")
        
        try:
            analysis = await AnalysisManager.get_analysis(symbol)
            
            # 1. Determine Regime for the current timeframe
            regime = await self.determine_timeframe_regime(analysis, timeframe)
            
            # Update Analysis Object
            await analysis.update_section("market_regime", regime, timeframe)
            
            # 2. Check if we should update overall regime (Rate limited to once per minute per symbol)
            now = time.time()
            if not hasattr(self, 'last_overall_update'):
                self.last_overall_update = {}
            
            if now - self.last_overall_update.get(symbol, 0) > 60:
                await self.determine_overall_regime(analysis)
                self.last_overall_update[symbol] = now
            
            self.processed_count += 1
            
        except Exception as e:
            logger.error(f"Error in RegimeDetectionAgent for {symbol} {timeframe}: {e}", exc_info=True)

    async def determine_timeframe_regime(self, analysis, timeframe: str) -> str:
        data = await analysis.get_data()
        ms = data.get("market_structure", {}).get(timeframe, {})
        df = data.get("market_data", {}).get(timeframe)
        
        if df is None:
            return "UNDEFINED"
            
        # Gather info
        curr = df.iloc[-1]
        
        # 1. Higher Timeframe Phases
        tfs = settings.TIMEFRAMES
        idx = tfs.index(timeframe)
        h1_phase = "N/A"
        h2_phase = "N/A"
        
        if idx > 0:
            h1_tf = tfs[idx-1]
            h1_phase = await self._get_tf_phase(analysis, h1_tf)
        if idx > 1:
            h2_tf = tfs[idx-2]
            h2_phase = await self._get_tf_phase(analysis, h2_tf)
            
        # 2. 2 Cycles Status
        two_cycles = self._check_two_cycles(df)
        
        # 3. Directional Indicators
        di_plus = curr.get('Positive Directional Indicator', 0)
        di_minus = curr.get('Negative Directional Indicator', 0)
        di_diff = di_plus - di_minus
        
        info = {
            "adx_trending": ms.get("adx"),
            "highs": ms.get("highs"),
            "lows": ms.get("lows"),
            "emas_in_order": ms.get("emas_in_order"),
            "emas_fanning": ms.get("emas_fanning"),
            "h1_phase": h1_phase,
            "h2_phase": h2_phase,
            "two_cycles": two_cycles,
            "pivot_points": ms.get("pivot_points"),
            "di_plus": di_plus,
            "di_minus": di_minus,
            "di_diff": di_diff,
            "above_zero": "DI+" if di_diff > 0 else ("DI-" if di_diff < 0 else "NEUTRAL"),
            "higher_di": "DI+" if di_plus > di_minus else "DI-"
        }
        
        try:
            res = await self.regime_chain.ainvoke({
                "symbol": analysis.symbol,
                "timeframe": timeframe,
                "data": info
            })
            regime = res.get("regime", "UNKNOWN").upper()
            await self.log_llm_call("regime_decision", analysis.symbol, {"timeframe": timeframe, "regime": regime})
            return regime
        except Exception as e:
            logger.error(f"LLM Error in determine_timeframe_regime: {e}")
            return "UNKNOWN"

    async def _get_tf_phase(self, analysis, timeframe: str) -> str:
        data = await analysis.get_data()
        df = data.get("market_data", {}).get(timeframe)
        if df is None or len(df) < 10:
            return "UNKNOWN"
            
        last_n = df.tail(10)
        formatted_data = last_n[['Heikin Ashi Open', 'Heikin Ashi High', 'Heikin Ashi Low', 'Heikin Ashi Close', 
                                'Relative Candles Open', 'Relative Candles Close', 'Relative Candles Phase']].to_string()
        
        try:
            res = await self.phase_chain.ainvoke({"data": formatted_data})
            return res.strip().upper()
        except:
            return "UNKNOWN"

    def _check_two_cycles(self, df: pd.DataFrame) -> str:
        """
        A trend is defined as 2 cycles in one direction.
        A cycle is identified by 'Relative Candles Phase' (1 or -1).
        We look for: [Prev Cycle Direction] -> [Correction] -> [Current Cycle Direction (same as Prev)]
        """
        if 'Relative Candles Phase' not in df.columns:
            return "UNKNOWN"
            
        phases = df['Relative Candles Phase'].values
        # Compress phases to identify changes
        compressed = []
        if len(phases) > 0:
            curr_v = phases[0]
            compressed.append(curr_v)
            for i in range(1, len(phases)):
                if phases[i] != curr_v:
                    curr_v = phases[i]
                    compressed.append(curr_v)
        
        # We need at least 3 segments: Up, Down, Up (or Down, Up, Down)
        if len(compressed) >= 3:
            last_3 = compressed[-3:] # [seg1, seg2, seg3]
            if last_3[0] == last_3[2]:
                direction = "UP" if last_3[0] == 1 else "DOWN"
                return f"2_{direction}_CYCLES"
        
        return "NEUTRAL"

    async def determine_overall_regime(self, analysis):
        data = await analysis.get_data()
        regimes = data.get("market_regime", {})
        
        # Gather weekly/monthly price action
        pa_data = {}
        for tf in ["1M", "1w"]:
            df = data.get("market_data", {}).get(tf)
            if df is not None:
                pa_data[tf] = df.tail(5)[['Open', 'High', 'Low', 'Close']].to_dict()
        
        try:
            res = await self.overall_chain.ainvoke({
                "symbol": analysis.symbol,
                "regimes": {k: v for k, v in regimes.items() if k != "last_updated" and k != "overall"},
                "pa_data": pa_data
            })
            
            overall = res.get("overall_regime", "UNKNOWN").upper()
            
            # Update overall and last_updated
            updates = {
                "overall": overall,
                "last_updated": int(time.time())
            }
            await analysis.update_section("market_regime", updates)
            
            logger.info(f"Updated Overall Regime for {analysis.symbol}: {overall}")
            
            # Publish REGIME_CHANGE event for overall regime
            await event_bus.publish(EventType.REGIME_CHANGE, {
                "symbol": analysis.symbol,
                "timeframe": "overall",
                "regime": overall,
                "timestamp": int(time.time()),
                "agent": self.name
            })
            
        except Exception as e:
            logger.error(f"LLM Error in determine_overall_regime: {e}")
