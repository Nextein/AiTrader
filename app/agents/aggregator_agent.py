import asyncio
from typing import Dict, List
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
import logging

logger = logging.getLogger("AggregatorAgent")

class AggregatorAgent(BaseAgent):
    def __init__(self, window_seconds: float = 5.0):
        super().__init__(name="AggregatorAgent")
        self.window_seconds = window_seconds
        self.current_regime = "TRENDING" # Default
        # Buffer to store signals for the current candle/timestamp
        # key: timestamp, value: list of signals
        self.signal_buffer: Dict[int, List[Dict]] = {}
        self.processing_tasks: Dict[int, asyncio.Task] = {}

    async def run_loop(self):
        event_bus.subscribe(EventType.STRATEGY_SIGNAL, self.on_strategy_signal)
        event_bus.subscribe(EventType.REGIME_CHANGE, self.on_regime_change)
        while self.is_running:
            await asyncio.sleep(1)

    async def on_regime_change(self, data):
        self.current_regime = data.get("regime", "UNKNOWN")
        logger.info(f"Aggregator updated with new regime: {self.current_regime}")

    async def on_strategy_signal(self, data):
        if not self.is_running:
            return

        ts = data.get("timestamp") or int(asyncio.get_event_loop().time())
        if ts not in self.signal_buffer:
            self.signal_buffer[ts] = []
            # Start a timer to process signals for this timestamp after a delay
            self.processing_tasks[ts] = asyncio.create_task(self.delayed_process(ts))
        
        self.signal_buffer[ts].append(data)
        logger.info(f"Buffered signal from {data.get('strategy_id', data.get('agent', 'Unknown'))} for processing.")

    async def delayed_process(self, ts: int):
        # Wait for other strategies to chime in
        await asyncio.sleep(self.window_seconds)
        
        signals = self.signal_buffer.get(ts, [])
        if not signals:
            return

        # Simple Weighted Voting logic
        total_weight = 0
        weighted_sum = 0 # BUY = 1, SELL = -1
        
        for s in signals:
            strategy_id = s.get("strategy_id", "")
            base_confidence = s.get("confidence", 0.5)
            
            # Regime-Adaptive Weighting
            multiplier = 1.0
            if self.current_regime == "TRENDING":
                if "EMA" in strategy_id:
                    multiplier = 1.5
                elif "RSI" in strategy_id:
                    multiplier = 0.5
            elif self.current_regime == "RANGING":
                if "RSI" in strategy_id:
                    multiplier = 1.5
                elif "EMA" in strategy_id:
                    multiplier = 0.5
            
            weight = base_confidence * multiplier
            direction = 1 if s.get("signal") == "BUY" else -1
            weighted_sum += direction * weight
            total_weight += weight
        
        # Consensus
        final_signal = "HOLD"
        final_confidence = 0.0
        
        if total_weight > 0:
            avg_score = weighted_sum / total_weight
            if avg_score > 0.3:
                final_signal = "BUY"
                final_confidence = avg_score
            elif avg_score < -0.3:
                final_signal = "SELL"
                final_confidence = abs(avg_score)

        if final_signal != "HOLD":
            logger.info(f"Aggregated Signal: {final_signal} | Confidence: {final_confidence:.2f} | Sources: {len(signals)}")
            await event_bus.publish(EventType.SIGNAL, {
                "symbol": signals[0].get("symbol"),
                "signal": final_signal,
                "confidence": final_confidence,
                "rationale": f"Consensus of {len(signals)} strategies. Avg Score: {avg_score:.2f}",
                "price": signals[0].get("price"),
                "timestamp": ts,
                "agent": self.name
            })

        # Cleanup
        del self.signal_buffer[ts]
        if ts in self.processing_tasks:
            del self.processing_tasks[ts]
