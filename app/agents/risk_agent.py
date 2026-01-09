import ccxt.async_support as ccxt
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.config import settings
import logging

logger = logging.getLogger("RiskAgent")

class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="RiskAgent")
        self.max_trade_size = settings.ORDER_SIZE_USDT
        self.exchange = ccxt.bingx({
            'apiKey': settings.BINGX_API_KEY,
            'secret': settings.BINGX_SECRET_KEY,
            'options': {
                'defaultType': 'swap',
                'sandbox': settings.BINGX_IS_SANDBOX,
            }
        })

    async def run_loop(self):
        event_bus.subscribe(EventType.SIGNAL, self.on_signal)
        while self.is_running:
            await asyncio.sleep(1)

    async def on_signal(self, data):
        if not self.is_running:
            return

        # Basic risk validation
        # 1. Confidence threshold
        if data.get("confidence", 0) < 0.6:
            logger.info(f"Signal rejected: Confidence too low ({data.get('confidence')})")
            return

        # 2. Position sizing & Balance check
        try:
            logger.info(f"Checking BingX balance for {self.max_trade_size} USDT trade...")
            balance = await self.exchange.fetch_balance()
            free_usdt = balance['USDT']['free']
            
            if free_usdt < self.max_trade_size:
                logger.warning(f"Risk Rejected: Insufficient balance ({free_usdt:.2f} USDT < {self.max_trade_size} USDT)")
                return
                
            order_request = {
                "symbol": data.get("symbol"),
                "side": "buy" if data.get("signal") == "BUY" else "sell",
                "type": "market",
                "amount": self.max_trade_size / data.get("price"), # amount in base asset
                "price": data.get("price"),
                "rationale": data.get("rationale"),
                "agent": self.name
            }
        except Exception as e:
            logger.error(f"Error checking balance: {e}")
            return

        logger.info(f"Risk Approved: {order_request['side']} {order_request['symbol']} size: {order_request['amount']}")
        await event_bus.publish(EventType.ORDER_REQUEST, order_request)

    async def stop(self):
        await super().stop()
        await self.exchange.close()

import asyncio
