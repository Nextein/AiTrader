import asyncio
import pandas as pd
import pandas_ta as ta
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
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
        timeframe = data.get("timeframe", "1h")
        
        # Unique key for symbol+tf
        lookup_key = f"{symbol}_{timeframe}"
        if self.last_timestamps.get(lookup_key) == ts:
            return
        self.last_timestamps[lookup_key] = ts

        try:
            # Get analysis object
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            
            # Get candles from AnalysisObject (updated by MarketDataAgent)
            df = analysis_data.get("market_data", {}).get(timeframe)
            
            if df is None or not isinstance(df, pd.DataFrame):
                return
            
            if len(df) < 30:
                return

            # ADX is already calculated by MarketDataAgent!
            # We can just use it.
            if 'Average Directional Index' not in df.columns:
                # Fallback calculation if not present
                df.ta.adx(append=True)
                adx = df['ADX_14'].iloc[-1]
            else:
                adx = df['Average Directional Index'].iloc[-1]
            
            current_regime = self.regimes.get(lookup_key, "UNKNOWN")
            
            new_regime = "RANGING"
            if adx > 25:
                new_regime = "TRENDING"
            
            if new_regime != current_regime:
                logger.info(f"Regime Change Detected [{symbol} {timeframe}]: {current_regime} -> {new_regime} (ADX: {adx:.2f})")
                self.regimes[lookup_key] = new_regime
                
                # Update Analysis Object
                await analysis.update_section("market_regime", new_regime, timeframe)
                
                await event_bus.publish(EventType.REGIME_CHANGE, {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "regime": new_regime,
                    "adx": adx,
                    "timestamp": ts,
                    "agent": self.name
                })
        except Exception as e:
            logger.error(f"Error in RegimeDetectionAgent: {e}")
