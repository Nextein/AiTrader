import pandas as pd
import numpy as np
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
from app.core.validation import validate_llm_response, safe_transfer

logger = logging.getLogger("SFPStrategyAgent")

class SFPStrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="SFPStrategyAgent")
        self.strategy_id = "SFP_STRATEGY"
        self.last_processed = {} # {symbol_tf: timestamp}
        
        self.llm = ChatOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
            model=settings.OLLAMA_MODEL,
            temperature=0
        )
        
        self.analysis_prompt = PromptLoader.load("strategies", "sfp_strategy")
        self.analysis_chain = self.analysis_prompt | self.llm | JsonOutputParser()

    def get_status(self):
        status = super().get_status()
        status["config"] = {
            "strategy_id": self.strategy_id
        }
        return status

    async def run_loop(self):
        # Triggered by ValueAreasAgent update (it already has initial SFP detection)
        event_bus.subscribe(EventType.VALUE_AREAS_UPDATED, self.handle_value_areas_update)
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_value_areas_update(self, data: Dict[str, Any]):
        if not self.is_running or not self.is_active:
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

            # 1. Gather SFP Detection from ValueAreas
            va = analysis_data.get("value_areas", {}).get(timeframe, {})
            va_state = va.get("state")
            
            # 2. Gather Supporting Data (Volume Imbalances, POC location in wick)
            curr = df.iloc[-1]
            latest_high = curr['High']
            latest_low = curr['Low']
            latest_close = curr['Close']
            latest_open = curr['Open']
            
            # Heuristic for wick POC (We don't have sub-candle volume yet, but we can look at Relative Candles)
            rel_mode = curr.get('Relative Candles Mode')
            
            # 3. LLM Analysis
            input_data = {
                "symbol": symbol,
                "timeframe": timeframe,
                "market_context": self.format_market_context(
                    df, 
                    window=50, 
                    columns=['Open', 'High', 'Low', 'Close', 'Volume', 'Weis Waves Volume', 'Weis Waves Direction']
                ),
                "analysis_summary": {
                    "vah": va.get("vah"),
                    "val": va.get("val"),
                    "va_state": va_state,
                    "regime": analysis_data.get("market_regime", {}).get(timeframe, "UNKNOWN"),
                    "market_structure": analysis_data.get("market_structure", {}).get(timeframe, {})
                }
            }
            
            res = await self.analysis_chain.ainvoke(input_data)
            
            if validate_llm_response(res, ["signal", "reasoning"]):
                # 4. Populate Analysis Object
                analysis_entry = {
                    "reasoning": res.get("reasoning"),
                    "signal": res.get("signal", "HOLD").upper(),
                    "confidence": res.get("confidence", 0.0),
                    "last_updated": int(time.time())
                }
                
                await safe_transfer(analysis, "sfp_strategy", {"analysis": analysis_entry}, timeframe)
                
                # 5. Generate Trade Setup if signal
                if analysis_entry["signal"] != "HOLD" and analysis_entry["confidence"] >= 0.75:
                    trade_setup = {
                        "strategy_id": self.strategy_id,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "signal": analysis_entry["signal"],
                        "entry_price": latest_close,
                        "sl_price": res.get("sl_price"),
                        "tp_price": res.get("tp_price"),
                        "rationale": res.get("rationale") or res.get("reasoning"),
                        "confidence": analysis_entry["confidence"],
                        "timestamp": int(time.time())
                    }
                    
                    if trade_setup["sl_price"] and trade_setup["tp_price"]:
                        await event_bus.publish(EventType.STRATEGY_SIGNAL, trade_setup)
                        self.log(f"Generated SIGNAL: {trade_setup['signal']} for {symbol}", level="INFO", data=trade_setup)

                self.processed_count += 1
                await self.log_llm_call("sfp_strategy_analysis", symbol, {"signal": analysis_entry["signal"]})
            else:
                logger.error(f"Invalid SFP strategy output for {symbol} {timeframe}: {res}")

        except Exception as e:
            logger.error(f"Error in SFPStrategyAgent for {symbol}: {e}", exc_info=True)
