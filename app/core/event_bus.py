import asyncio
from typing import Callable, List, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger("EventBus")

class EventType(Enum):
    MARKET_DATA = "market_data"
    STRATEGY_SIGNAL = "strategy_signal"
    SIGNAL = "signal"
    ORDER_REQUEST = "order_request"
    ORDER_FILLED = "order_filled"
    REGIME_CHANGE = "regime_change"
    ANOMALY_ALERT = "anomaly_alert"
    ERROR = "error"
    SYSTEM_STATUS = "system_status"
    EMERGENCY_EXIT = "emergency_exit"

class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[Dict[str, Any]], None]]] = {}

    def subscribe(self, event_type: EventType, callback: Callable[[Dict[str, Any]], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to {event_type.value}")

    async def publish(self, event_type: EventType, data: Dict[str, Any]):
        logger.debug(f"Publishing {event_type.value}: {data}")
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                # If callback is async, await it
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)

# Global instance
event_bus = EventBus()
