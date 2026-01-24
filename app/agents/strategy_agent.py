import pandas as pd
import pandas_ta as ta
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
import logging

logger = logging.getLogger("StrategyAgent")

class StrategyAgent(BaseAgent):
    def __init__(self, strategy_id: str = "RSI_MACD"):
        super().__init__(name=f"StrategyAgent_{strategy_id}")
        self.strategy_id = strategy_id
        # Optimization: track last processed timestamp to avoid duplicate signals for same candle
        self.last_timestamp = None

    def get_status(self):
        status = super().get_status()
        status["config"] = {
            "strategy_id": self.strategy_id
        }
        return status

    async def run_loop(self):
        # Subscribe to market data
        event_bus.subscribe(EventType.MARKET_DATA, self.on_market_data)
        logger.info("Subscribed to market data")
        # The run_loop just keeps it alive; processing is event-driven
        while self.is_running:
            await asyncio.sleep(1)

    async def on_market_data(self, data):
        if not self.is_running:
            return

        timestamp = data.get("timestamp")
        if timestamp == self.last_timestamp:
            return
        
        self.last_timestamp = timestamp
        self.processed_count += 1
        candles = data.get("candles")
        columns = data.get("columns", ['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Robust DataFrame creation
        if len(candles) > 0 and len(candles[0]) != len(columns):
            # If mismatch, fallback to slicing or basic columns if possible
            if len(columns) == 6 and len(candles[0]) > 6:
                 # Assume first 6 are OHLCV
                 df = pd.DataFrame([c[:6] for c in candles], columns=columns)
            else:
                 # Try to use whatever matches
                 # But usually we should trust 'columns' from the event if it matches candle width
                 df = pd.DataFrame(candles) # Let pandas handle default int columns
                 # Assign columns if length matches
                 if len(df.columns) == len(columns):
                     df.columns = columns
        else:
            df = pd.DataFrame(candles, columns=columns)
        
        # Simple RSI + MACD Strategy
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        
        # Get latest values
        if 'RSI_14' not in df.columns or 'MACD_12_26_9' not in df.columns or 'MACDs_12_26_9' not in df.columns:
            logger.warning(f"[{self.strategy_id}] Indicators not yet available.")
            return

        rsi = df['RSI_14'].iloc[-1]
        macd = df['MACD_12_26_9'].iloc[-1]
        macd_signal = df['MACDs_12_26_9'].iloc[-1]
        
        logger.info(f"[{self.strategy_id}] {data.get('symbol')} | RSI: {rsi:.2f} | MACD: {macd:.4f} | Signal: {macd_signal:.4f} | Diff: {macd - macd_signal:.5f}")
        
        signal = "HOLD"
        confidence = 0.0
        rationale = ""

        # Basic Long Condition: RSI < 35 (oversold) and MACD cross up
        if rsi < 35 and macd > macd_signal:
            signal = "BUY"
            confidence = 0.7
            rationale = f"RSI is oversold ({rsi:.2f}) and MACD has crossed up."
            logger.info(f"[{self.strategy_id}] BUY SIGNAL: {rationale}")
        
        # Basic Short Condition: RSI > 65 (overbought) and MACD cross down
        elif rsi > 65 and macd < macd_signal:
            signal = "SELL"
            confidence = 0.7
            rationale = f"RSI is overbought ({rsi:.2f}) and MACD has crossed down."
            logger.info(f"[{self.strategy_id}] SELL SIGNAL: {rationale}")

        if signal != "HOLD":
            logger.info(f"[{self.strategy_id}] Generated Signal: {signal} | Confidence: {confidence}")
            await event_bus.publish(EventType.STRATEGY_SIGNAL, {
                "strategy_id": self.strategy_id,
                "symbol": data.get("symbol"),
                "signal": signal,
                "confidence": confidence,
                "rationale": rationale,
                "price": data.get("latest_close"),
                "timestamp": timestamp
            })

import asyncio # Needs to be imported for run_loop's sleep
