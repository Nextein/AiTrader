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
from app.core.validation import validate_llm_response, safe_transfer

logger = logging.getLogger("BounceStrategyAgent")

class BounceStrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="BounceStrategyAgent")
        self.strategy_id = "BOUNCE_STRATEGY"
        self.last_processed = {} # {symbol_tf: timestamp}
        
        self.llm = ChatOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
            model=settings.OLLAMA_MODEL,
            temperature=0
        )
        
        self.analysis_prompt = PromptLoader.load("strategies", "bounce_strategy")
        self.analysis_chain = self.analysis_prompt | self.llm | JsonOutputParser()

    def get_status(self):
        status = super().get_status()
        status["config"] = {
            "strategy_id": self.strategy_id,
            "ema_periods": [9, 21, 55]
        }
        return status

    async def run_loop(self):
        # Triggered by analysis updates
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

            # 1. Gather Data for Bounce Logic
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            ema9 = curr.get('Exponential Moving Average 9')
            ema21 = curr.get('Exponential Moving Average 21')
            ema55 = curr.get('Exponential Moving Average 55')
            lr_slope = curr.get('Linear Regression Slope', 0)
            
            # MACD Alignment (MarketDataAgent calculates it? Let's check)
            # MarketDataAgent doesn't seem to calculate generic MACD, but I'll add it if missing or compute here.
            # StrategyAgent had it. I'll compute it here for simplicity if missing.
            macd_df = df.ta.macd(fast=12, slow=26, signal=9)
            macd_val = 0
            if macd_df is not None:
                macd_val = macd_df.iloc[-1][0] # MACD_12_26_9
            
            # 2. Multi-Timeframe Alignment (D1 and H4)
            d1_data = analysis_data.get("market_data", {}).get("1d")
            h4_data = analysis_data.get("market_data", {}).get("4h")
            
            d1_trend = "UNKNOWN"
            if d1_data is not None and len(d1_data) > 0:
                d1_curr = d1_data.iloc[-1]
                d1_ema9 = d1_curr.get('Exponential Moving Average 9')
                d1_ema21 = d1_curr.get('Exponential Moving Average 21')
                if d1_ema9 and d1_ema21:
                    d1_trend = "UP" if d1_ema9 > d1_ema21 else "DOWN"

            h4_pullback = "NO"
            if h4_data is not None and len(h4_data) >= 2:
                h4_curr = h4_data.iloc[-1]
                h4_prev = h4_data.iloc[-2]
                h4_ema21 = h4_curr.get('Exponential Moving Average 21')
                if h4_ema21:
                    # Pullback below 20 EMA followed by immediate recovery (simplification)
                    if h4_prev['Close'] < h4_ema21 and h4_curr['Close'] > h4_ema21:
                        h4_pullback = "YES"

            # 3. LLM Analysis
            input_data = {
                "symbol": symbol,
                "timeframe": timeframe,
                "market_context": self.format_market_context(
                    df, 
                    window=50, 
                    columns=['Open', 'High', 'Low', 'Close', 'Exponential Moving Average 21', 'Linear Regression Slope']
                ),
                "analysis_summary": (
                    f"- Price: {curr['Close']}\n"
                    f"- MACD Value: {macd_val}\n"
                    f"- D1 Trend: {d1_trend}\n"
                    f"- H4 Pullback: {h4_pullback}\n"
                    f"- Regime: {analysis_data.get('market_regime', {}).get(timeframe, 'UNKNOWN')}"
                )
            }
            
            res = await self.call_llm_with_retry(self.analysis_chain, input_data, required_keys=["signal", "reasoning"])
            
            if res:
                # 4. Populate Analysis Object
                analysis_entry = {
                    "reasoning": res.get("reasoning"),
                    "signal": res.get("signal", "HOLD").upper(),
                    "confidence": res.get("confidence", 0.0),
                    "last_updated": int(time.time())
                }
                
                await safe_transfer(analysis, "bounce_strategy", {"analysis": analysis_entry}, timeframe)
                
                # 5. Generate Trade Setup if signal
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
                    
                    if trade_setup["sl_price"] and trade_setup["tp_price"]:
                        await event_bus.publish(EventType.STRATEGY_SIGNAL, trade_setup)
                        self.log(f"Generated SIGNAL: {trade_setup['signal']} for {symbol}", level="INFO", data=trade_setup)

                self.processed_count += 1
                await self.log_llm_call("bounce_strategy_analysis", symbol, {"signal": analysis_entry["signal"]})
            else:
                 logger.warning(f"Failed to get Bounce strategy output for {symbol} {timeframe}")

        except Exception as e:
            logger.error(f"Error in BounceStrategyAgent for {symbol}: {e}", exc_info=True)
