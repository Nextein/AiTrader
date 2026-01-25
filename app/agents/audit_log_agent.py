import asyncio
import numpy as np
from typing import Any
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.database import SessionLocal
from app.models.models import AuditLogModel
import logging

logger = logging.getLogger("AuditLogAgent")

class AuditLogAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="AuditLogAgent")

    async def run_loop(self):
        # Subscribe to all event types
        for event_type in EventType:
            event_bus.subscribe(event_type, self.handle_event(event_type))
        
        logger.info("AuditLogAgent monitoring all system events.")
        while self.is_running:
            await asyncio.sleep(1)

    def sanitize_data(self, data: Any) -> Any:
        """Recursively convert NumPy types to Python primitives for JSON serialization."""
        if isinstance(data, dict):
            return {k: self.sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_data(v) for v in data]
        elif isinstance(data, (np.int64, np.int32, np.integer)):
            return int(data)
        elif isinstance(data, (np.float64, np.float32, np.floating)):
            return float(data)
        elif isinstance(data, np.ndarray):
            return self.sanitize_data(data.tolist())
        return data

    def handle_event(self, event_type: EventType):
        # Closure to capture event_type
        async def callback(data):
            if not self.is_running:
                return
            
            try:
                # Sanitize data to handle NumPy types from pandas/ta
                clean_data = self.sanitize_data(data)
                agent_name = clean_data.get("agent", "unknown")
                
                # We use a new session for each log entry to ensure isolation
                with SessionLocal() as db:
                    log_entry = AuditLogModel(
                        event_type=event_type.value,
                        agent_name=agent_name,
                        data=clean_data
                    )
                    db.add(log_entry)
                    db.commit()
                
                # Terminal output for visibility - use local variable, not detached object
                self.log(f"EVENT_PERSISTED: {event_type.value} from {agent_name}", level="DEBUG", data=clean_data)
            except Exception as e:
                self.log(f"Failed to log event {event_type.value}: {e}", level="ERROR")

        return callback
