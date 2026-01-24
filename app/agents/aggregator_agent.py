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
        logger.debug(f"AggregatorAgent initialized with window_seconds={window_seconds}")

    async def run_loop(self):
        logger.info("AggregatorAgent polling loop started")
        event_bus.subscribe(EventType.STRATEGY_SIGNAL, self.on_strategy_signal)
        event_bus.subscribe(EventType.REGIME_CHANGE, self.on_regime_change)
        while self.is_running:
            await asyncio.sleep(1)

    async def on_regime_change(self, data):
        prev_regime = self.current_regime
        self.current_regime = data.get("regime", "UNKNOWN")
        logger.info(f"Regime Change Detected: {prev_regime} -> {self.current_regime}")

    async def on_strategy_signal(self, data):
        if not self.is_running:
            return

        ts = data.get("timestamp") or int(asyncio.get_event_loop().time())
        strategy = data.get('strategy_id', data.get('agent', 'Unknown'))
        symbol = data.get('symbol', 'Unknown')
        signal_type = data.get('signal', 'HOLD')
        confidence = data.get('confidence', 0.0)

        logger.info(f"Received Signal: [{strategy}] {signal_type} {symbol} (Conf: {confidence}) | TS: {ts}")
        
        if ts not in self.signal_buffer:
            self.signal_buffer[ts] = []
            # Start a timer to process signals for this timestamp after a delay
            self.processing_tasks[ts] = asyncio.create_task(self.delayed_process(ts))
            logger.debug(f"Started new signal buffer for timestamp {ts}")
        
        self.signal_buffer[ts].append(data)
        logger.debug(f"Buffered signal. Current buffer size for {ts}: {len(self.signal_buffer[ts])}")

    async def delayed_process(self, ts: int):
        logger.debug(f"Processing delayed signals for timestamp {ts} (waiting {self.window_seconds}s)...")
        # Wait for other strategies to chime in
        await asyncio.sleep(self.window_seconds)
        
        signals = self.signal_buffer.get(ts, [])
        if not signals:
            logger.debug(f"No signals found for timestamp {ts} after wait.")
            return

        logger.info(f"Processing aggregation for TS {ts}. Total Signals: {len(signals)}")

        # Simple Weighted Voting logic
        total_weight = 0
        weighted_sum = 0 # BUY = 1, SELL = -1
        
        for s in signals:
            strategy_id = s.get("strategy_id", "")
            base_confidence = s.get("confidence", 0.5)
            signal_direction_str = s.get("signal")
            
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
            direction = 1 if signal_direction_str == "BUY" else -1
            weighted_sum += direction * weight
            total_weight += weight

            logger.debug(f"  > Strategy: {strategy_id} | Signal: {signal_direction_str} | BaseConf: {base_confidence:.2f} | Multiplier: {multiplier} | Contrib: {direction * weight:.2f}")
        
        # Consensus
        final_signal = "HOLD"
        final_confidence = 0.0
        avg_score = 0.0
        
        if total_weight > 0:
            avg_score = weighted_sum / total_weight
            logger.debug(f"Agg logic: WeightedSum={weighted_sum:.2f}, TotalWeight={total_weight:.2f}, AvgScore={avg_score:.2f}")

            if avg_score > 0.3:
                final_signal = "BUY"
                final_confidence = avg_score
            elif avg_score < -0.3:
                final_signal = "SELL"
                final_confidence = abs(avg_score)
            else:
                logger.debug(f"Agg logic: Score {avg_score:.2f} within neutral threshold (-0.3 to 0.3). HOLDing.")
        else:
            logger.warning("Agg logic: Total weight is 0. No decision.")

        if final_signal != "HOLD":
            # Find a source signal that matches the final decision to get SL/TP
            representative_signal = next((s for s in signals if s.get("signal") == final_signal), signals[0])
            
            logger.info(f"AGGREGATED DECISION: {final_signal} | Confidence: {final_confidence:.2f} | Sources: {len(signals)} | Rationale: Consensus Score {avg_score:.2f}")
            await event_bus.publish(EventType.SIGNAL, {
                "symbol": representative_signal.get("symbol"),
                "signal": final_signal,
                "confidence": final_confidence,
                "rationale": f"Consensus of {len(signals)} strategies. Avg Score: {avg_score:.2f}",
                "price": representative_signal.get("price"),
                "sl_price": representative_signal.get("sl_price"),
                "tp_price": representative_signal.get("tp_price"),
                "timestamp": ts,
                "agent": self.name
            })
        else:
            logger.info(f"AGGREGATED DECISION: HOLD (Score: {avg_score:.2f} insufficient)")

        # Cleanup
        if ts in self.signal_buffer:
            del self.signal_buffer[ts]
        if ts in self.processing_tasks:
            del self.processing_tasks[ts]

