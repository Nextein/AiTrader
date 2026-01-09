from abc import ABC, abstractmethod
import asyncio
from app.core.event_bus import event_bus, EventType

import time

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.is_running = False
        self.start_time = None
        self.processed_count = 0

    async def start(self):
        self.is_running = True
        self.start_time = time.time()
        print(f"[{self.name}] Started")
        await self.run_loop()

    async def stop(self):
        self.is_running = False
        print(f"[{self.name}] Stopped")

    @abstractmethod
    async def run_loop(self):
        pass

    def get_status(self):
        uptime = 0
        if self.is_running and self.start_time:
            uptime = int(time.time() - self.start_time)
            
        return {
            "name": self.name,
            "is_running": self.is_running,
            "type": self.__class__.__name__,
            "uptime": uptime,
            "processed_count": self.processed_count,
            "config": {}
        }
