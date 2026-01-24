import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger("Analysis")

class AnalysisObject:
    """
    Symbol-scoped Analysis Object acting as the single source of truth.
    Thread-safe and conforms to app/models/analysis.json schema.
    """
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data: Dict[str, Any] = {
            "symbol": symbol,
            "date_created": int(time.time()),
            "analysis_state": "NEW",
            "market_data": {
                "1w": None, "1d": None, "4h": None, "1h": None, "30m": None, "15m": None, "5m": None
            },
            "market_structure": {
                "1w": self._default_market_structure(),
                "1d": self._default_market_structure(),
                "4h": self._default_market_structure(),
                "1h": self._default_market_structure(),
                "30m": self._default_market_structure(),
                "15m": self._default_market_structure(),
                "5m": self._default_market_structure(),
            },
            "market_regime": {
                "1w": "UNDEFINED", "1d": "UNDEFINED", "4h": "UNDEFINED", "1h": "UNDEFINED",
                "30m": "UNDEFINED", "15m": "UNDEFINED", "5m": "UNDEFINED",
                "last_updated": None
            },
            "value_areas": {
                "1w": self._default_value_areas(),
                "1d": self._default_value_areas(),
                "4h": self._default_value_areas(),
                "1h": self._default_value_areas(),
                "30m": self._default_value_areas(),
                "15m": self._default_value_areas(),
                "5m": self._default_value_areas(),
            },
            "vpvr": {
                "1w": self._default_vpvr(),
                "1d": self._default_vpvr(),
                "4h": self._default_vpvr(),
                "1h": self._default_vpvr(),
                "30m": self._default_vpvr(),
                "15m": self._default_vpvr(),
                "5m": self._default_vpvr(),
            },
            "key_levels": {
                "last_updated": None
            }
        }
        self._lock = asyncio.Lock()
        self._last_updated = time.time()

    def _default_market_structure(self):
        return {
            "analysis": [],
            "highs": "NEUTRAL",
            "lows": "NEUTRAL",
            "value_areas": "NEUTRAL",
            "pivot_points": "NEUTRAL",
            "emas": "NEUTRAL",
            "adx": "NEUTRAL",
            "last_updated": None
        }

    def _default_value_areas(self):
        return {
            "poc": None,
            "vah": None,
            "val": None,
            "naked_poc": False,
            "state": "UNKNOWN",
            "last_updated": None
        }

    def _default_vpvr(self):
        return {
            "data": [],
            "last_updated": None
        }

    async def update_section(self, section: str, updates: Any, timeframe: Optional[str] = None):
        """
        Incrementally update a section of the analysis object.
        Agents only mutate their owned sections.
        """
        async with self._lock:
            if section not in self.data:
                self.data[section] = {}
            
            target = self.data[section]
            
            if timeframe:
                # Special handling for market_data which stores DataFrames directly
                if section == "market_data":
                    target[timeframe] = updates
                else:
                    if timeframe not in target or target[timeframe] is None:
                        target[timeframe] = {}
                    
                    if isinstance(target[timeframe], dict) and isinstance(updates, dict):
                        target[timeframe].update(updates)
                    else:
                        target[timeframe] = updates
            else:
                if isinstance(target, dict) and isinstance(updates, dict):
                    target.update(updates)
                else:
                    self.data[section] = updates
            
            self._last_updated = time.time()
            self.data["analysis_state"] = "IN_PROGRESS"
            
            # Update specific timestamps if applicable
            # We check the actual data structure to safely update last_updated
            if isinstance(target, dict) and "last_updated" in target:
                target["last_updated"] = datetime.now().isoformat()
            
            if timeframe and isinstance(target, dict):
                tf_data = target.get(timeframe)
                if isinstance(tf_data, dict) and "last_updated" in tf_data:
                    tf_data["last_updated"] = datetime.now().isoformat()

    async def get_data(self) -> Dict[str, Any]:
        """Return a copy of the data"""
        async with self._lock:
            return self.data.copy()

class AnalysisManager:
    """Manages symbol-scoped AnalysisObjects"""
    _instances: Dict[str, AnalysisObject] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def get_analysis(cls, symbol: str) -> AnalysisObject:
        async with cls._lock:
            if symbol not in cls._instances:
                cls._instances[symbol] = AnalysisObject(symbol)
            return cls._instances[symbol]

    @classmethod
    async def get_all_symbols(cls) -> List[str]:
        async with cls._lock:
            return list(cls._instances.keys())
