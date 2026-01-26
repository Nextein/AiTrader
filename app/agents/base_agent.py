from abc import ABC, abstractmethod
import asyncio
from app.core.event_bus import event_bus, EventType

import time
import logging
from app.core.logger import logger as system_logger

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.is_running = False
        self.is_active = True  # Task 2: Activation state
        self.start_time = None
        self.processed_count = 0
        self.description = ""
        self.tasks = []
        self.responsibilities = []
        self.prompts = []

    async def start(self):
        self.is_running = True
        self.start_time = time.time()
        self.log(f"Agent {self.name} started", level="INFO")
        await self.run_loop()

    async def stop(self):
        self.is_running = False
        self.log(f"Agent {self.name} stopped", level="INFO")

    @abstractmethod
    async def run_loop(self):
        pass

    def get_status(self):
        uptime = time.time() - self.start_time if self.start_time else 0
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_active": self.is_active,
            "type": self.__class__.__name__,
            "uptime": uptime,
            "processed_count": self.processed_count,
            "description": self.description,
            "tasks": self.tasks,
            "responsibilities": self.responsibilities,
            "prompts": self.prompts,
            "config": {}
        }

    def log(self, message: str, level: str = "INFO", data: dict = None):
        """Standardized logging for agents"""
        log_msg = f"[{self.name}] {message}"
        if data:
            log_msg += f" | DATA: {data}"
        
        if level.upper() == "DEBUG":
            system_logger.debug(log_msg)
        elif level.upper() == "INFO":
            system_logger.info(log_msg)
        elif level.upper() == "WARNING":
            system_logger.warning(log_msg)
        elif level.upper() == "ERROR":
            system_logger.error(log_msg)
        elif level.upper() == "CRITICAL":
            system_logger.critical(log_msg)

    async def log_event(self, message: str, data: dict = None, level: str = "INFO"):
        """Publishes an AGENT_LOG event to the event bus for visibility in the UI"""
        self.log(message, level, data)
        await event_bus.publish(EventType.AGENT_LOG, {
            "agent": self.name,
            "message": message,
            "data": data,
            "level": level,
            "timestamp": int(time.time())
        })

    async def log_llm_call(self, prompt_name: str, symbol: str = None, result: dict = None):
        """Specific logging for LLM calls with event publishing"""
        msg = f"LLM_CALL: {prompt_name}" + (f" for {symbol}" if symbol else "")
        self.log(msg, level="INFO", data=result)
        await event_bus.publish(EventType.AGENT_LOG, {
            "agent": self.name,
            "type": "llm_call",
            "prompt_name": prompt_name,
            "symbol": symbol,
            "result": result,
            "timestamp": int(time.time())
        })

    async def log_market_action(self, action: str, symbol: str, details: dict = None):
        """Specific logging for market actions data fetches with event publishing"""
        msg = f"MARKET_ACTION: {action} for {symbol}"
        self.log(msg, level="INFO", data=details)
        await event_bus.publish(EventType.AGENT_LOG, {
            "agent": self.name,
            "type": "market_action",
            "action": action,
            "symbol": symbol,
            "details": details,
            "timestamp": int(time.time())
        })
