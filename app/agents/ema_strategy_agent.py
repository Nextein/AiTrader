import pandas as pd
import pandas_ta as ta
import asyncio
import time
import logging
from typing import Dict, Any, Optional
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
from app.core.config import settings
from app.core.prompt_loader import PromptLoader
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from app.core.validation import validate_llm_response, safe_transfer

logger = logging.getLogger("EMAStrategyAgent")

class EMAStrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="EMAStrategyAgent")
        self.strategy_id = "EMA_STRATEGY"
        self.last_processed = {} # {symbol_tf: timestamp}
        
        self.llm = ChatOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
            model=settings.OLLAMA_MODEL,
            temperature=0
        )
        
        # We'll use a specific prompt for EMA strategy analysis
        self.analysis_prompt = PromptLoader.load("strategies", "ema_strategy")
        self.analysis_chain = self.analysis_prompt | self.llm | JsonOutputParser()

    def get_status(self):
        status = super().get_status()
        status["config"] = {
            "strategy_id": self.strategy_id,
            "periods": [9, 21, 55]
        }
        return status

    async def run_loop(self):
        # Triggered by market structure updates to ensure context is available
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
            if df is None or len(df) < 60:
                return
            
            ts = df['timestamp'].iloc[-1]
            lookup_key = f"{symbol}_{timeframe}"
            if self.last_processed.get(lookup_key) == ts:
                return
            self.last_processed[lookup_key] = ts

            # 1. Gather EMA Data
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            ema9_curr = curr.get('Exponential Moving Average 9')
            ema21_curr = curr.get('Exponential Moving Average 21')
            ema55_curr = curr.get('Exponential Moving Average 55')
            
            ema9_prev = prev.get('Exponential Moving Average 9')
            ema21_prev = prev.get('Exponential Moving Average 21')
            ema55_prev = prev.get('Exponential Moving Average 55')
            
            if any(pd.isna(v) for v in [ema9_curr, ema21_curr, ema55_curr, ema9_prev, ema21_prev, ema55_prev]):
                return

            # 2. Detect Crossovers
            cross_9_21 = "UP" if (ema9_prev <= ema21_prev and ema9_curr > ema21_curr) else ("DOWN" if (ema9_prev >= ema21_prev and ema9_curr < ema21_curr) else "NONE")
            cross_21_55 = "UP" if (ema21_prev <= ema55_prev and ema21_curr > ema55_curr) else ("DOWN" if (ema21_prev >= ema55_prev and ema21_curr < ema55_curr) else "NONE")
            
            # 3. Context from Market Structure and Regime
            ms = analysis_data.get("market_structure", {}).get(timeframe, {})
            regime = analysis_data.get("market_regime", {}).get(timeframe, "UNKNOWN")
            overall_regime = analysis_data.get("market_regime", {}).get("overall", "UNKNOWN")
            
            # 4. LLM Analysis
            input_data = {
                "symbol": symbol,
                "timeframe": timeframe,
                "market_context": self.format_market_context(df, window=50),
                "analysis_summary": {
                    "price": curr['Close'],
                    "cross_9_21": cross_9_21,
                    "cross_21_55": cross_21_55,
                    "market_structure": ms,
                    "regime": regime,
                    "overall_regime": overall_regime,
                    "value_areas": analysis_data.get("value_areas", {}).get(timeframe)
                }
            }
            
            res = await self.analysis_chain.ainvoke(input_data)
            
            if validate_llm_response(res, ["signal", "reasoning"]):
                # 5. Populate Analysis Object
                analysis_entry = {
                    "reasoning": res.get("reasoning"),
                    "signal": res.get("signal", "HOLD").upper(),
                    "confidence": res.get("confidence", 0.0),
                    "last_updated": int(time.time())
                }
                
                await safe_transfer(analysis, "ema_strategy", {"analysis": analysis_entry}, timeframe)
                
                # 6. Generate Trade Setup if signal
                if analysis_entry["signal"] != "HOLD" and analysis_entry["confidence"] >= 0.7:
                    trade_setup = {
                        "strategy_id": self.strategy_id,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "signal": analysis_entry["signal"],
                        "entry_price": curr['Close'],
                        "sl_price": res.get("sl_price"),
                        "tp_price": res.get("tp_price"),
                        "rationale": res.get("rationale") or res.get("reasoning"),
                        "confidence": analysis_entry["confidence"],
                        "timestamp": int(time.time())
                    }
                    
                    # Check validity of SL/TP
                    if trade_setup["sl_price"] and trade_setup["tp_price"]:
                        await event_bus.publish(EventType.STRATEGY_SIGNAL, trade_setup)
                        self.log(f"Generated SIGNAL: {trade_setup['signal']} for {symbol}", level="INFO", data=trade_setup)

                self.processed_count += 1
                await self.log_llm_call("ema_strategy_analysis", symbol, {"signal": analysis_entry["signal"]})
            else:
                logger.error(f"Invalid EMA strategy output for {symbol} {timeframe}: {res}")

        except Exception as e:
            logger.error(f"Error in EMAStrategyAgent for {symbol}: {e}", exc_info=True)
