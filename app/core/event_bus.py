import asyncio
from typing import Callable, List, Dict, Any
from enum import Enum, IntEnum
from collections import deque
from datetime import datetime
import logging

logger = logging.getLogger("EventBus")

class EventPriority(IntEnum):
    """
    Event priority levels for the event bus.
    Lower numeric values = higher priority (processed first)
    """
    CRITICAL = 0  # Emergency stops, position closures
    HIGH = 1      # Trade signals, order requests
    NORMAL = 2    # Market data processing, regime changes
    LOW = 3       # Logging, statistics updates

class EventType(Enum):
    MARKET_DATA = "market_data"
    MARKET_DATA_REQUEST = "market_data_request"
    STRATEGY_SIGNAL = "strategy_signal"
    SIGNAL = "signal"
    ORDER_REQUEST = "order_request"
    ORDER_FILLED = "order_filled"
    REGIME_CHANGE = "regime_change"
    ANOMALY_ALERT = "anomaly_alert"
    ERROR = "error"
    SYSTEM_STATUS = "system_status"
    EMERGENCY_EXIT = "emergency_exit"

# Default priority mapping for event types
EVENT_PRIORITY_MAP = {
    EventType.EMERGENCY_EXIT: EventPriority.CRITICAL,
    EventType.ORDER_REQUEST: EventPriority.HIGH,
    EventType.ORDER_FILLED: EventPriority.HIGH,
    EventType.STRATEGY_SIGNAL: EventPriority.HIGH,
    EventType.SIGNAL: EventPriority.HIGH,
    EventType.ANOMALY_ALERT: EventPriority.HIGH,
    EventType.MARKET_DATA: EventPriority.NORMAL,
    EventType.MARKET_DATA_REQUEST: EventPriority.NORMAL,
    EventType.REGIME_CHANGE: EventPriority.NORMAL,
    EventType.ERROR: EventPriority.LOW,
    EventType.SYSTEM_STATUS: EventPriority.LOW,
}

class Event:
    """Wrapper for events with priority and metadata"""
    def __init__(self, event_type: EventType, data: Dict[str, Any], priority: EventPriority = None):
        self.event_type = event_type
        self.data = data
        self.priority = priority if priority is not None else EVENT_PRIORITY_MAP.get(event_type, EventPriority.NORMAL)
        self.timestamp = datetime.now()
        self.agent_name = data.get('agent', 'Unknown')
    
    def __lt__(self, other):
        """Compare events by priority for queue ordering"""
        return self.priority < other.priority

class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[Dict[str, Any]], None]]] = {}
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._processing = False
        self._event_history: deque = deque(maxlen=1000)  # Store last 1000 events
        self._agent_events: Dict[str, deque] = {}  # Events per agent

    def subscribe(self, event_type: EventType, callback: Callable[[Dict[str, Any]], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to {event_type.value}")

    def clear_subscribers(self):
        """Clears all subscribers across all event types. Useful for testing."""
        self._subscribers = {}
        logger.info("Cleared all event bus subscribers.")

    async def publish(self, event_type: EventType, data: Dict[str, Any], priority: EventPriority = None):
        """
        Publish an event to the event bus with optional priority override.
        Events are queued and processed in priority order.
        """
        event = Event(event_type, data, priority)
        
        # Store in history
        self._event_history.append(event)
        
        # Store in agent-specific history
        agent_name = event.agent_name
        if agent_name not in self._agent_events:
            self._agent_events[agent_name] = deque(maxlen=100)
        self._agent_events[agent_name].append(event)
        
        logger.info(f"Publishing {event_type.value} with priority {event.priority.name}: {data}")
        
        # Add to priority queue
        await self._event_queue.put((event.priority, event))
        
        # Start processing if not already running
        if not self._processing:
            asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Process events from the priority queue"""
        if self._processing:
            return
        
        self._processing = True
        try:
            while not self._event_queue.empty():
                try:
                    _, event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                    await self._dispatch_event(event)
                except asyncio.TimeoutError:
                    break
        finally:
            self._processing = False

    async def _dispatch_event(self, event: Event):
        """Dispatch an event to all subscribers"""
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event.data)
                    else:
                        callback(event.data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event.event_type.value}: {e}")

    def get_agent_events(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events created by a specific agent"""
        if agent_name not in self._agent_events:
            return []
        
        events = list(self._agent_events[agent_name])[-limit:]
        return [{
            'event_type': event.event_type.value,
            'data': self._convert_to_serializable(event.data),
            'timestamp': event.timestamp.isoformat(),
            'priority': event.priority.name,
            'agent_name': event.agent_name
        } for event in events]

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events from all agents"""
        events = list(self._event_history)[-limit:]
        return [{
            'event_type': event.event_type.value,
            'data': self._convert_to_serializable(event.data),
            'timestamp': event.timestamp.isoformat(),
            'priority': event.priority.name,
            'agent_name': event.agent_name
        } for event in events]
    
    def _convert_to_serializable(self, obj: Any) -> Any:
        """Convert numpy and other non-serializable types to native Python types"""
        import numpy as np
        
        if isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

# Global instance
event_bus = EventBus()
