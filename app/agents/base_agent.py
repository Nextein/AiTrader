from abc import ABC, abstractmethod
import asyncio
from app.core.event_bus import event_bus, EventType

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.is_running = False

    async def start(self):
        self.is_running = True
        print(f"[{self.name}] Started")
        await self.run_loop()

    async def stop(self):
        self.is_running = False
        print(f"[{self.name}] Stopped")

    @abstractmethod
    async def run_loop(self):
        pass

    def get_status(self):
        return {
            "name": self.name,
            "is_running": self.is_running,
            "type": self.__class__.__name__,
            "config": {}
        }
