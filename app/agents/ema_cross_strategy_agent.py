import pandas as pd
import pandas_ta as ta
import asyncio
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
import logging

logger = logging.getLogger("EMACrossStrategy")

class EMACrossStrategyAgent(BaseAgent):
    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        strategy_id = f"EMA_{fast_period}_{slow_period}"
        super().__init__(name=f"StrategyAgent_{strategy_id}")
        self.strategy_id = strategy_id
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.last_timestamps = {} # {symbol_tf: timestamp}

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

        symbol = data.get("symbol")
        timeframe = data.get("timeframe", "1h")
        timestamp = data.get("timestamp")
        
        lookup_key = f"{symbol}_{timeframe}"
        if self.last_timestamps.get(lookup_key) == timestamp:
            return
        
        self.last_timestamps[lookup_key] = timestamp

        try:
            # Get analysis object (Single source of truth)
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            
            # Get candles from AnalysisObject
            df = analysis_data.get("market_data", {}).get(timeframe)
            
            if df is None or not isinstance(df, pd.DataFrame) or len(df) < self.slow_period + 1:
                return
            
            # EMA Cross Strategy
            fast_ema_col = f"EMA_{self.fast_period}"
            slow_ema_col = f"EMA_{self.slow_period}"
            
            # Indicators are already calculated by MarketDataAgent!
            # We use the existing EMA columns if present, fallback otherwise
            f_col = f'Exponential Moving Average {self.fast_period}'
            s_col = f'Exponential Moving Average {self.slow_period}'
            
            if f_col in df.columns and s_col in df.columns:
                fast_val = df[f_col]
                slow_val = df[s_col]
            else:
                fast_val = ta.ema(df['Close'], length=self.fast_period)
                slow_val = ta.ema(df['Close'], length=self.slow_period)

        
            fast_now = fast_val.iloc[-1]
            fast_prev = fast_val.iloc[-2]
            slow_now = slow_val.iloc[-1]
            slow_prev = slow_val.iloc[-2]
            
            logger.info(f"[{self.strategy_id}] {symbol} {timeframe} | FastEMA({self.fast_period}): {fast_now:.5f} (prev: {fast_prev:.5f}) | SlowEMA({self.slow_period}): {slow_now:.5f} (prev: {slow_prev:.5f})")
            
            signal = "HOLD"
            confidence = 0.0
            rationale = ""
    
            # Bullish Cross
            if fast_prev <= slow_prev and fast_now > slow_now:
                signal = "BUY"
                confidence = 0.6
                rationale = f"EMA Cross: {self.fast_period} crossed above {self.slow_period} on {timeframe}"
                logger.info(f"[{self.strategy_id}] BULLISH CROSS DETECTED!")
            
            # Bearish Cross
            elif fast_prev >= slow_prev and fast_now < slow_now:
                signal = "SELL"
                confidence = 0.6
                rationale = f"EMA Cross: {self.fast_period} crossed below {self.slow_period} on {timeframe}"
                logger.info(f"[{self.strategy_id}] BEARISH CROSS DETECTED!")
    
            if signal != "HOLD":
                logger.info(f"[{self.strategy_id}] Generated Signal: {signal}")
                price = data.get("latest_close")
                sl = price * 0.98 if signal == "BUY" else price * 1.02
                tp = price * 1.05 if signal == "BUY" else price * 0.95
                
                await event_bus.publish(EventType.STRATEGY_SIGNAL, {
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "signal": signal,
                    "confidence": confidence,
                    "rationale": rationale,
                    "price": price,
                    "sl_price": sl,
                    "tp_price": tp,
                    "timestamp": timestamp
                })
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")

