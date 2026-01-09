import asyncio
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
import logging

logger = logging.getLogger("DummyStrategyAgent")

class DummyStrategyAgent(BaseAgent):
    """
    A dummy strategy agent for testing the event bus and agent system.
    Generates predictable signals based on market data event count.
    """
    def __init__(self, signal_interval: int = 5, name: str = "DummyStrategyAgent"):
        """
        Args:
            signal_interval: Emit a signal every N market data events
            name: Agent name
        """
        super().__init__(name=name)
        self.signal_interval = signal_interval
        self.market_data_count = 0
        self.signals_generated = 0
        
    def get_status(self):
        status = super().get_status()
        status["config"] = {
            "signal_interval": self.signal_interval,
            "market_data_received": self.market_data_count,
            "signals_generated": self.signals_generated
        }
        return status

    async def run_loop(self):
        """Subscribe to market data and generate test signals"""
        event_bus.subscribe(EventType.MARKET_DATA, self.handle_market_data)
        
        # Keep running while active
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_market_data(self, data: dict):
        """Handle incoming market data and generate signals at intervals"""
        if not self.is_running:
            return
        
        self.market_data_count += 1
        self.processed_count += 1
        
        # Generate signal every N market data events
        if self.market_data_count % self.signal_interval == 0:
            signal_price = data.get("latest_close", 0)
            signal_data = {
                "strategy_id": self.name,
                "symbol": data.get("symbol", "UNKNOWN"),
                "signal": "BUY" if self.signals_generated % 2 == 0 else "SELL",
                "confidence": 1.0, # Dummy confidence
                "reason": f"Test signal #{self.signals_generated + 1}",
                "price": signal_price,
                "sl_price": signal_price * 0.95 if self.signals_generated % 2 == 0 else signal_price * 1.05,
                "tp_price": signal_price * 1.10 if self.signals_generated % 2 == 0 else signal_price * 0.90,
                "timestamp": data.get("timestamp"),
                "agent": self.name
            }
            
            await event_bus.publish(EventType.STRATEGY_SIGNAL, signal_data)
            self.signals_generated += 1
            
            logger.info(f"[{self.name}] Generated test signal #{self.signals_generated} "
                       f"after {self.market_data_count} market data events")
