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
        candles = data.get("candles")
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Simple RSI + MACD Strategy
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        
        # Get latest values
        rsi = df['RSI_14'].iloc[-1]
        macd = df['MACD_12_26_9'].iloc[-1]
        macd_signal = df['MACDs_12_26_9'].iloc[-1]
        
        logger.info(f"[{self.strategy_id}] Indicators >> RSI: {rsi:.2f} | MACD: {macd:.4f} | Signal: {macd_signal:.4f}")
        
        signal = "HOLD"
        confidence = 0.0
        rationale = ""

        # Basic Long Condition: RSI < 30 (oversold) and MACD cross up
        if rsi < 35 and macd > macd_signal:
            signal = "BUY"
            confidence = 0.7
            rationale = f"RSI is oversold ({rsi:.2f}) and MACD has crossed up."
        
        # Basic Short Condition: RSI > 70 (overbought) and MACD cross down
        elif rsi > 65 and macd < macd_signal:
            signal = "SELL"
            confidence = 0.7
            rationale = f"RSI is overbought ({rsi:.2f}) and MACD has crossed down."

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
