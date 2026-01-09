import asyncio
import pandas as pd
import pandas_ta as ta
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
import logging

logger = logging.getLogger("RegimeDetection")

class RegimeDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="RegimeDetectionAgent")
        self.regimes = {} # {symbol: regime}
        self.last_timestamps = {} # {symbol: timestamp}

    def get_status(self):
        status = super().get_status()
        status["data"] = {
            "regimes": self.regimes
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
        ts = data.get("timestamp")
        
        if self.last_timestamps.get(symbol) == ts:
            return
        self.last_timestamps[symbol] = ts

        candles = data.get("candles")
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Calculate ADX (Average Directional Index) for trend strength
        # And ATR (Average True Range) for volatility
        df.ta.adx(append=True)
        df.ta.atr(append=True)
        
        if len(df) < 30:
            return

        adx = df['ADX_14'].iloc[-1]
        current_regime = self.regimes.get(symbol, "UNKNOWN")
        logger.info(f"Market Monitoring [{symbol}]: ADX={adx:.2f} | Current Regime={current_regime}")
        
        new_regime = "RANGING"
        if adx > 25:
            new_regime = "TRENDING"
        
        if new_regime != current_regime:
            logger.info(f"Regime Change Detected [{symbol}]: {current_regime} -> {new_regime} (ADX: {adx:.2f})")
            self.regimes[symbol] = new_regime
            await event_bus.publish(EventType.REGIME_CHANGE, {
                "symbol": symbol,
                "regime": new_regime,
                "adx": adx,
                "timestamp": ts,
                "agent": self.name
            })
