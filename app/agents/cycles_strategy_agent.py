import pandas as pd
import pandas_ta as ta
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
from app.core.config import settings
from app.core.prompt_loader import PromptLoader
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger("CyclesStrategyAgent")

class CyclesStrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="CyclesStrategyAgent")
        self.strategy_id = "CYCLES_STRATEGY"
        self.last_processed = {} # {symbol_tf: timestamp}
        
        self.llm = ChatOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
            model=settings.OLLAMA_MODEL,
            temperature=0
        )
        
        self.analysis_prompt = PromptLoader.load("strategies", "cycles_strategy")
        self.analysis_chain = self.analysis_prompt | self.llm | JsonOutputParser()

    def get_status(self):
        status = super().get_status()
        status["config"] = {
            "strategy_id": self.strategy_id
        }
        return status

    async def run_loop(self):
        # Triggered by analysis updates to ensure regime/structure context is available
        event_bus.subscribe(EventType.ANALYSIS_UPDATE, self.handle_analysis_update)
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_analysis_update(self, data: Dict[str, Any]):
        if not self.is_running or not self.is_active:
            return
            
        if data.get("section") != "market_regime":
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

            # 1. Gather Candle and Phase Data
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Heikin Ashi Color
            ha_dir = "UP" if curr['Heikin Ashi Close'] > curr['Heikin Ashi Open'] else "DOWN"
            ha_prev_dir = "UP" if prev['Heikin Ashi Close'] > prev['Heikin Ashi Open'] else "DOWN"
            
            # Relative Candle Phase
            rel_phase = "UP" if curr.get('Relative Candles Phase') == 1 else "DOWN"
            rel_prev_phase = "UP" if prev.get('Relative Candles Phase') == 1 else "DOWN"
            
            # Trigger: Phase Change
            trigger_activated = "YES" if (rel_phase != rel_prev_phase) or (ha_dir != ha_prev_dir) else "NO"
            
            # 2. Context from Market Structure and Regime
            ms = analysis_data.get("market_structure", {}).get(timeframe, {})
            regime = analysis_data.get("market_regime", {}).get(timeframe, "UNKNOWN")
            overall_regime = analysis_data.get("market_regime", {}).get("overall", "UNKNOWN")
            
            # 3. Higher Timeframe Alignment
            tfs = settings.TIMEFRAMES
            h1_regime = "N/A"
            if timeframe in tfs:
                idx = tfs.index(timeframe)
                if idx > 0:
                    h1_tf = tfs[idx-1]
                    h1_regime = analysis_data.get("market_regime", {}).get(h1_tf, "UNKNOWN")

            # 4. ATR for SL
            atr = curr.get('Average True Range', 0)
            
            # 5. LLM Analysis
            input_data = {
                "symbol": symbol,
                "timeframe": timeframe,
                "market_context": self.format_market_context(
                    df, 
                    window=50,
                    columns=['Open', 'High', 'Low', 'Close', 'Heikin Ashi Close', 'Relative Candles Phase']
                ),
                "analysis_summary": {
                    "price": curr['Close'],
                    "ha_dir": ha_dir,
                    "rel_phase": rel_phase,
                    "trigger_activated": trigger_activated,
                    "market_structure": ms,
                    "regime": regime,
                    "overall_regime": overall_regime,
                    "h1_regime": h1_regime,
                    "atr": atr
                }
            }
            
            res = await self.analysis_chain.ainvoke(input_data)
            
            # 6. Populate Analysis Object
            analysis_entry = {
                "conclusion": res.get("conclusion"),
                "signal": res.get("signal", "HOLD").upper(),
                "confidence": res.get("confidence", 0.0),
                "last_updated": int(time.time())
            }
            
            await analysis.update_section("cycles_strategy", {"analysis": analysis_entry}, timeframe)
            
            # 7. Generate Trade Setup if signal
            if analysis_entry["signal"] != "HOLD" and analysis_entry["confidence"] >= 0.7:
                trade_setup = {
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "signal": analysis_entry["signal"],
                    "entry_price": curr['Close'],
                    "sl_price": res.get("sl_price"),
                    "tp_price": res.get("tp_price"),
                    "rationale": res.get("rationale"),
                    "confidence": analysis_entry["confidence"],
                    "timestamp": int(time.time())
                }
                
                if trade_setup["sl_price"] and trade_setup["tp_price"]:
                    await event_bus.publish(EventType.STRATEGY_SIGNAL, trade_setup)
                    self.log(f"Generated SIGNAL: {trade_setup['signal']} for {symbol}", level="INFO", data=trade_setup)

            self.processed_count += 1
            await self.log_llm_call("cycles_strategy_analysis", symbol, {"signal": analysis_entry["signal"]})

        except Exception as e:
            logger.error(f"Error in CyclesStrategyAgent for {symbol}: {e}", exc_info=True)
