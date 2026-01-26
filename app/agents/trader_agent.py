import asyncio
import time
import logging
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
from app.core.config import settings

logger = logging.getLogger("TraderAgent")

class TraderAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="TraderAgent")
        self.open_positions = {} # {symbol: {data}}
        self.last_check = 0

    async def run_loop(self):
        event_bus.subscribe(EventType.ORDER_FILLED, self.on_order_filled)
        event_bus.subscribe(EventType.MARKET_DATA, self.on_market_data)
        while self.is_running:
            await asyncio.sleep(1)

    async def on_order_filled(self, data: Dict[str, Any]):
        symbol = data.get("symbol")
        if not symbol: return
        
        # Track position (simplified - assumes one position per symbol)
        # In a real system, we'd fetch actual positions from the exchange periodically
        if data.get("status") == "FILLED" or data.get("status") == "OPEN":
            self.open_positions[symbol] = {
                "side": data.get("side"),
                "amount": data.get("amount"),
                "entry_price": data.get("price"),
                "sl": data.get("sl_price"),
                "tp": data.get("tp_price"),
                "timestamp": time.time()
            }
            self.log(f"Tracking new position for {symbol}", level="INFO")

    async def on_market_data(self, data: Dict[str, Any]):
        if not self.is_active or not self.open_positions:
            return
            
        symbol = data.get("symbol")
        if symbol not in self.open_positions:
            return
            
        pos = self.open_positions[symbol]
        curr_price = data.get("latest_close")
        
        # 1. Periodically verify positions with exchange (Optional/Future)
        
        # 2. Dynamic Exit Logic
        await self._check_dynamic_exits(symbol, pos, data)

    async def _check_dynamic_exits(self, symbol: str, pos: Dict, market_data: Dict):
        """Implements Heikin Ashi and Structural flip exits"""
        try:
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            tf = market_data.get("timeframe", "1h")
            df = analysis_data.get("market_data", {}).get(tf)
            
            if df is None or len(df) < 5: return
            
            curr = df.iloc[-1]
            
            # Rule: Heikin Ashi Flip
            ha_open = curr.get('Heikin Ashi Open')
            ha_close = curr.get('Heikin Ashi Close')
            ha_rev = (pos['side'] == 'buy' and ha_close < ha_open) or (pos['side'] == 'sell' and ha_close > ha_open)
            
            # Rule: Market Structure Flip (Breaking recent fractal)
            ms = analysis_data.get("market_structure", {}).get(tf, {})
            ms_flip = (pos['side'] == 'buy' and ms.get("highs") == "LOWER") or (pos['side'] == 'sell' and ms.get("lows") == "HIGHER")
            
            if ha_rev or ms_flip:
                reason = "HA reversal" if ha_rev else "Structure flip"
                self.log(f"Dynamic Exit Triggered for {symbol}: {reason}", level="WARNING")
                
                # Signal ExecutionAgent to close
                close_request = {
                    "symbol": symbol,
                    "side": "sell" if pos['side'] == 'buy' else "buy",
                    "type": "market",
                    "amount": pos['amount'],
                    "params": {"reduceOnly": True},
                    "rationale": f"Dynamic Exit: {reason}",
                    "agent": self.name
                }
                await event_bus.publish(EventType.ORDER_REQUEST, close_request)
                
                # Remove from tracking
                del self.open_positions[symbol]

        except Exception as e:
            logger.error(f"TraderAgent Exit Check Error for {symbol}: {e}")
