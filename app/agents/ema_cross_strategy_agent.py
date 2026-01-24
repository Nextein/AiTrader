import pandas as pd
import pandas_ta as ta
import asyncio
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
import logging

logger = logging.getLogger("EMACrossStrategy")

class EMACrossStrategyAgent(BaseAgent):
    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        strategy_id = f"EMA_{fast_period}_{slow_period}"
        super().__init__(name=f"StrategyAgent_{strategy_id}")
        self.strategy_id = strategy_id
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.last_timestamp = None

    def get_status(self):
        status = super().get_status()
        status["config"] = {
            "strategy_id": self.strategy_id,
            "fast_period": self.fast_period,
            "slow_period": self.slow_period
        }
        return status

    async def run_loop(self):
        event_bus.subscribe(EventType.MARKET_DATA, self.on_market_data)
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
        columns = data.get("columns", ['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        if len(candles) > 0 and len(candles[0]) != len(columns):
             if len(columns) == 6 and len(candles[0]) > 6:
                 df = pd.DataFrame([c[:6] for c in candles], columns=columns)
             else:
                 df = pd.DataFrame(candles)
                 if len(df.columns) == len(columns):
                     df.columns = columns
        else:
            df = pd.DataFrame(candles, columns=columns)
        
        # EMA Cross Strategy
        fast_ema_col = f"EMA_{self.fast_period}"
        slow_ema_col = f"EMA_{self.slow_period}"
        
        df[fast_ema_col] = ta.ema(df['close'], length=self.fast_period)
        df[slow_ema_col] = ta.ema(df['close'], length=self.slow_period)
        
        if len(df) < self.slow_period + 1:
            return

        fast_now = df[fast_ema_col].iloc[-1]
        fast_prev = df[fast_ema_col].iloc[-2]
        slow_now = df[slow_ema_col].iloc[-1]
        slow_prev = df[slow_ema_col].iloc[-2]
        
        # logger.info(f"[{self.strategy_id}] Indicators >> Fast: {fast_now:.2f} | Slow: {slow_now:.2f}")
        # Make this more debug friendly but less spammy if not crossing?
        # Actually user wants "much more in depth".
        logger.info(f"[{self.strategy_id}] {data.get('symbol')} | FastEMA({self.fast_period}): {fast_now:.5f} (prev: {fast_prev:.5f}) | SlowEMA({self.slow_period}): {slow_now:.5f} (prev: {slow_prev:.5f})")
        
        signal = "HOLD"
        confidence = 0.0
        rationale = ""

        # Bullish Cross
        if fast_prev <= slow_prev and fast_now > slow_now:
            signal = "BUY"
            confidence = 0.6
            rationale = f"EMA Cross: {fast_ema_col} crossed above {slow_ema_col}"
            logger.info(f"[{self.strategy_id}] BULLISH CROSS DETECTED!")
        
        # Bearish Cross
        elif fast_prev >= slow_prev and fast_now < slow_now:
            signal = "SELL"
            confidence = 0.6
            rationale = f"EMA Cross: {fast_ema_col} crossed below {slow_ema_col}"
            logger.info(f"[{self.strategy_id}] BEARISH CROSS DETECTED!")

        if signal != "HOLD":
            logger.info(f"[{self.strategy_id}] Generated Signal: {signal}")
            price = data.get("latest_close")
            sl = price * 0.98 if signal == "BUY" else price * 1.02
            tp = price * 1.05 if signal == "BUY" else price * 0.95
            
            await event_bus.publish(EventType.STRATEGY_SIGNAL, {
                "strategy_id": self.strategy_id,
                "symbol": data.get("symbol"),
                "signal": signal,
                "confidence": confidence,
                "rationale": rationale,
                "price": price,
                "sl_price": sl,
                "tp_price": tp,
                "timestamp": timestamp
            })
