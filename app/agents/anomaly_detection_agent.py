import asyncio
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
import logging
import pandas as pd

logger = logging.getLogger("AnomalyDetection")

class AnomalyDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="AnomalyDetectionAgent")
        self.signal_count_window = [] # List of timestamps
        self.max_signals_per_minute = 10

    async def run_loop(self):
        event_bus.subscribe(EventType.SIGNAL, self.on_signal)
        event_bus.subscribe(EventType.MARKET_DATA, self.on_market_data)
        while self.is_running:
            await asyncio.sleep(1)

    async def on_signal(self, data):
        # ... logic for signal frequency ...
        if not self.is_running:
            return

        now = asyncio.get_event_loop().time()
        self.signal_count_window = [t for t in self.signal_count_window if now - t < 60]
        self.signal_count_window.append(now)

        if len(self.signal_count_window) > self.max_signals_per_minute:
            logger.error(f"Anomaly Detected: Excessive signal frequency ({len(self.signal_count_window)} sig/min)")
            await event_bus.publish(EventType.ANOMALY_ALERT, {
                "type": "EXCESSIVE_SIGNALS",
                "count": len(self.signal_count_window),
                "agent": self.name
            })

    async def on_market_data(self, data):
        if not self.is_running:
            return
        
        symbol = data.get("symbol")
        timeframe = data.get("timeframe", "1h")
        
        try:
            # Get analysis object (Single source of truth)
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            
            # Get candles from AnalysisObject
            df = analysis_data.get("market_data", {}).get(timeframe)
            
            if df is None or not isinstance(df, pd.DataFrame) or len(df) < 2:
                return
            
            # Detect Flash Crashes (e.g. > 5% move in 1 candle)
            latest = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            
            change = abs(latest - prev) / prev
            if change > 0.05:
                self.log(f"Extreme Price Move ({change*100:.2f}%) on {symbol} {timeframe}", level="ERROR")
                await event_bus.publish(EventType.ANOMALY_ALERT, {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "type": "EXTREME_VOLATILITY",
                    "change_pct": change * 100,
                    "agent": self.name
                })
        except Exception as e:
            self.log(f"Error in AnomalyDetectionAgent: {e}", level="ERROR")

