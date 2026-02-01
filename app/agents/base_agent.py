from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
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

    def format_market_context(self, df: Any, window: int = 50, columns: list = None) -> str:
        """
        Formats a pandas DataFrame into a clean markdown table for LLM context.
        Done manually to avoid 'tabulate' dependency.
        """
        import pandas as pd
        if not isinstance(df, pd.DataFrame) or df.empty:
            return "No data available."

        subset = df.tail(window).copy()
        if not columns:
            columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            potential_cols = [
                'Exponential Moving Average 9', 'Exponential Moving Average 21', 'Exponential Moving Average 55',
                'Relative Candles Phase', 'Heikin Ashi Close', 'Williams Fractals 9'
            ]
            columns += [c for c in potential_cols if c in subset.columns]

        available_cols = [c for c in columns if c in subset.columns]
        subset = subset[available_cols]
        
        # Round and format
        for col in subset.select_dtypes(include=['number']).columns:
            subset[col] = subset[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "NaN")

        # Build table
        header = "| " + " | ".join(available_cols) + " |"
        separator = "| " + " | ".join(["---"] * len(available_cols)) + " |"
        rows = []
        for _, row in subset.iterrows():
            rows.append("| " + " | ".join(row.values) + " |")
        
        return "\n".join([header, separator] + rows)

    async def call_llm_with_retry(self, chain: Any, inputs: Dict[str, Any], required_keys: List[str] = None, max_retries: int = 5) -> Optional[Dict[str, Any]]:
        """
        Invokes an LLM chain with retry logic for JSON parsing and validation.
        """
        from app.core.validation import validate_llm_response
        
        for attempt in range(max_retries):
            try:
                res = await chain.ainvoke(inputs)
                
                # If required_keys is provided, validate the response
                if required_keys:
                    if validate_llm_response(res, required_keys):
                        return res
                    else:
                        self.log(f"Attempt {attempt + 1}/{max_retries} failed: Invalid JSON structure for {required_keys}. Retrying...", level="WARNING")
                else:
                    # If no keys required, just return as long as it's not None
                    if res is not None:
                        return res
                    else:
                        self.log(f"Attempt {attempt + 1}/{max_retries} failed: NULL response. Retrying...", level="WARNING")
                        
            except Exception as e:
                self.log(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying...", level="WARNING")
            
            # Small delay before retry
            await asyncio.sleep(1)
            
        self.log(f"Failed to get valid LLM response after {max_retries} attempts.", level="ERROR")
        return None
